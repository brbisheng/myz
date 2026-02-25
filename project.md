下面给一个可落地的 plan：目标是让 **Claude Code / OpenClaw 这类 agent** 通过 **Zotero API** 拉取你指定论文（最新/按你口头指定）的 **notes**，再把 notes 结构化输出给你（用于写作、综述、RAG、知识库等）。

---

## 0. 总体架构（先定不变的骨架）

**输入**（你口头/文本指令） → **论文定位**（Zotero 库内找到 item） → **拉取 notes**（item 下的 note items） → **清洗/结构化**（HTML/富文本→markdown/字段） → **输出**（摘要/要点/可检索条目/写作素材） →（可选）**写回 Zotero**（生成新 note 或 tag）

建议把系统拆成两个可替换模块：

1. **Retriever**：只负责和 Zotero API 通信、定位 item、取 note。
2. **Processor**：只负责解析 note、去噪、抽取结构、生成你需要的产物。

这样你换 agent（Claude Code / OpenClaw）时，不会牵一发动全身。

---

## 1. 需求定义（最关键的“可执行规格”）

把“口头指定”和“最新”变成明确规则，否则 agent 会不稳定。

### 1.1 口头指定论文：支持的指令类型

至少支持这三类：

* **精确定位**：`by citekey / DOI / arXiv / title`
* **模糊定位**：`title contains ...` + 交互式 disambiguation（列候选让你选 1 个）
* **集合定位**：`collection=xxx` 或 `tag=yyy` 或 `saved search`（Zotero 内的 collection/tag 是最稳的）

### 1.2 “最新论文”的定义（建议优先用 Zotero 内的时间字段）

你需要明确 “latest” 按哪个排序：

* `dateAdded`（加入 Zotero 的时间）——最稳定、最符合“我刚加进来的文献”
* `dateModified`（条目最近被改过）——如果你经常补元数据会被干扰
* `publicationDate`（发表时间）——Zotero 条目未必都有，且格式多样

**推荐默认：dateAdded 倒序取 Top N。**

### 1.3 notes 的范围

Zotero 的“笔记”可能有两种来源：

* **独立 note item**（Zotero note）
* **附件（PDF）上的 annotation 转 note**（如果你用 Zotero PDF reader 做标注，通常也会以 note/annotation 形式出现，具体取决于你的工作流）

先明确：你要的是 “note item 内容”，还是 “annotation（高亮/批注）”，还是两者都要。
**建议 v1：只做 note item；v2 再加 annotation。**

---

## 2. Zotero API 接入（v1 必须做对）

### 2.1 权限与认证

* 用 Zotero **API key**（用户级）
* 只读权限足够（拉取 items/notes）；如果要写回 Zotero 才需要写权限

### 2.2 最小 API 调用集合（v1）

你需要的核心能力就四个：

1. 列表：取最新 items（按 dateAdded 排序）
2. 搜索：按 title/DOI 等检索 item
3. notes：取某个 item 下的 child notes
4. note 内容：读 note 的正文（通常是 HTML/富文本）

实现上建议你把 API 封装成这几个函数（不绑定任何 agent）：

* `list_items(sort="dateAdded", direction="desc", limit=N, collectionKey?, tag?)`
* `search_items(q, fields=["title","DOI","creators"], limit=...)`
* `list_child_notes(itemKey)`
* `get_note(noteKey)`（返回 note content）

---

## 3. 数据清洗与结构化（让输出可用、可检索）

Zotero note 往往是 HTML 或混合格式，你需要统一成一种内部表示。

### 3.1 标准化输出 schema（强烈建议）

给每条 note 输出一个统一 JSON（或 YAML）结构，后续才好做 RAG/写作：

* `paper`: { `itemKey`, `title`, `authors`, `year`, `doi`, `collections`, `tags` }
* `note`: { `noteKey`, `parentItemKey`, `created`, `modified`, `content_md`, `content_raw` }
* `extracted`:

  * `summary`（一段）
  * `claims`（要点列表）
  * `methods`（方法/模型/数据）
  * `variables`（若你做经济学变量节点抽取）
  * `quotes`（可选，带定位）
  * `open_questions`（你后续要追的点）

### 3.2 去噪规则（必须 deterministic）

* HTML → markdown（保留标题/列表/粗体）
* 删除空段落、重复换行
* 规范引用符号（比如把全角标点统一）
* 可选：把你常用的笔记模板识别出来（例如“贡献/方法/结论/局限”）

---

## 4. Agent 工作流设计（Claude Code / OpenClaw 都适用）

### 4.1 工具化（Tools）

给 agent 暴露一个很小的工具面：

* `zotero.list_items(...)`
* `zotero.search_items(...)`
* `zotero.get_notes_for_item(itemKey)`
* `zotero.get_note(noteKey)`
* `processor.normalize_note(note_html)->note_md`
* `processor.extract_schema(note_md)->extracted_json`

Agent 不应该直接拼 URL；它只调用工具函数。这样可控、可测试、可复用。

### 4.2 典型对话流程（v1）

**A) 你说“拉取最新 5 篇的 notes”**

1. agent：`list_items(limit=5, sort=dateAdded desc)`
2. 对每个 item：`list_child_notes(itemKey)` → `get_note(noteKey)`
3. 汇总：按 paper 分组输出

**B) 你说“把 Acemoglu 2020 那篇 xxx 的 notes 拉出来”**

1. `search_items(q="Acemoglu xxx 2020")`
2. 如果返回多条：列候选（title/year/first author/dateAdded），让你选编号
3. 取选中的 item notes

---

## 5. 可靠性与成本控制（你之前很在意“封顶”和稳定）

### 5.1 缓存与增量

* 缓存 `itemKey -> noteKey list`
* 缓存 `noteKey -> content_md + extracted`（以 `noteVersion` 或 `dateModified` 判定是否需要重跑）
* “最新”模式下，每次只取最近 N 个 item，并且只处理新增或 modified 的 note

### 5.2 错误处理（必须显式）

* Zotero API rate limit / 429：退避重试
* note 不存在：返回 “no notes” 明确标记
* 多候选冲突：必须走 disambiguation

---

## 6. 里程碑拆分（按可交付）

### M1（1 天量级的工程复杂度）：Retriever 打通

* API key 配置
* list latest items
* search items
* 拉取 child notes + note content
* 原样输出（先不抽取）

**验收**：你说“最新 3 篇”，能返回标题 + 每篇 note 原文。

### M2：Processor 标准化

* HTML→Markdown
* 输出统一 schema
* 按 paper 分组输出

**验收**：输出结构稳定，可直接丢进你的知识库。

### M3：智能抽取（面向你的研究/经济学工作流）

* 从 notes 抽取：贡献、方法、数据、识别策略、关键结论、局限
* 生成 “变量-关系-条件” 的结构（你之前的 conditional sign 需求可以接在这里）

**验收**：对 10 篇论文 notes 生成可比较的结构表。

### M4：写回 Zotero（可选）

* 把 extracted 结果写回到 Zotero 新 note（例如 “LLM Summary”）
* 或自动加 tag（如 `processed`, `to_read`, `needs_citation`）

---

## 7. 你需要准备的最少信息（不问你问题，但给出默认）

为了立刻能开始实现，默认做法：

* 默认库：`user library`（不是 group）
* “最新”：按 `dateAdded` 倒序取 N
* notes：只取 Zotero note items（不含 annotation）
* 输出：每篇 paper 一个 JSON block + markdown 摘要

---

如果你下一步要我把它变成“可直接跑”的工程方案，我会按上述 M1→M2 的顺序给你：

1. 文件结构（最小可维护）
2. Zotero API 封装代码接口（Retriever）
3. 一个 CLI/agent tool wrapper（让 Claude Code/OpenClaw 可调用）
4. 示例指令与输出样例（用于测试与回归）
