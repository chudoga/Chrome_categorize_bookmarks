这里为你准备了一份结构清晰、规范且易于阅读的 GitHub `README.md` 模板。你可以直接复制并保存为仓库中的 `README.md`。

---

# 🔖 Netscape Bookmark Parser & Categorizer

一个高效、轻量的 Python 浏览器书签处理与自动分类工具。支持解析标准的 Netscape Bookmark HTML 格式，将其转换为结构化 JSON，并可根据自定义文本规则将杂乱的书签自动归类到多级目录中。

---

## ✨ 核心特性

* **⚡ 标准解析与无损还原**：完整支持 Netscape 书签格式（包含 `ADD_DATE`、`ICON`、`LAST_MODIFIED` 等元数据），支持 HTML ↔ JSON 互转，内置节点一致性校验。
* **🌳 树状文本分类引擎**：无需修改代码，只需编辑 `categories_rules.txt` 规则文件即可自由配置一/二/三级目录和关键词规则。
* **🔤 智能文本规范化**：
* **URL 自动解码**：如将 `%E7%99%BE%E5%BA%A6` 自动转译为“百度”再进行关键字匹配。
* **大小写与繁简不敏感**：支持繁简体自动转换（优先调用 `zhconv` / `opencc`，内置降级映射表），匹配更精准。


* **🧹 自动清理与占位符过滤**：在解析源头自动过滤掉无意义的占位网址（如 `[https://example.com/](https://example.com/)`），保持书签库纯净。
* **📥 完善的 Inbox 兜底机制**：
* 无名称网址 ➡️ 归入 `Inbox / 无名称`
* 未匹配关键词或“名称即网址” ➡️ 归入 `Inbox / 无标签`



---

## 📁 项目结构

```text
.
├── bookmark_processor.py      # 主程序脚本
├── categories_rules.txt       # 分类规则配置文件
├── bookmarks.html             # [输入] 待处理的导出的书签文件
├── bookmarks_full.json        # [输出] 解析后的完整书签 JSON 数据
├── bookmarks_restored.html    # [输出] 还原的标准 HTML 书签文件
└── bookmarks_categorized.html # [输出] 自动分类整理后的最终书签文件

```

---

## 🚀 快速开始

### 1. 环境准备与依赖

脚本基于 Python 3 开发，默认使用标准库（无需额外安装依赖即可运行）。

若想获得更好的**繁体中文自动转简体**体验，建议可选安装 `zhconv` 或 `opencc`：

```bash
pip install zhconv
# 或者
pip install opencc-python-reimplemented

```

*(注：若未安装上述依赖，脚本会自动降级使用内置的常用繁简字符对照表)*

---

### 2. 使用步骤

1. **导出书签**：从 Chrome、Edge、Firefox 等浏览器中导出书签文件，命名为 `bookmarks.html` 并放入项目根目录。
2. **配置规则**：编辑 `categories_rules.txt`（参考下方规则配置说明）。
3. **运行脚本**：

```bash
python bookmark_processor.py

```

4. **导入结果**：运行完成后，将生成的 `bookmarks_categorized.html` 导入回浏览器即可享受整洁的书签目录！

---

## ⚙️ 分类规则语法说明 (`categories_rules.txt`)

规则文件采用类似于 `tree` 命令的直观缩进格式，解析时会自动忽略空行、以 `#` 开头的注释行以及 `[...]` 中的描述内容。

```text
# ==============================
# 格式规范：
# 一级目录名[一级目录描述]
# ├── 二级目录名[二级目录描述]
# │   ├── 三级目录名 (关键词1, 关键词2, ...)
# │   └── 三级目录名 (关键词1, 关键词2, ...)
# └── 二级目录名 (二级目录关键词1, 二级目录关键词2)
# ==============================

Inbox[待整理标签]
├── 待整理 (临时收集, 未处理)
└── 无标签 (已归档, 无标签)

Tech[技术开发与运维]
├── 软件开发 (个人项目, 开发环境, GitHub, Gitee)
├── AI大模型 (Claude, GPT, HuggingFace, OpenAI, Kimi)
└── 运维与服务器 (Linux运维, Nginx, Docker, SSH, VPS)

Life[生活与休闲]
├── 医疗健康 (健康, 医院, 药品, 默沙东)
└── 影视娱乐 (电影网, 字幕组, Netflix, Steam)

```

### 规则要点：

* **关键词分隔**：英文逗号 `,`、中文逗号 `，` 或顿号 `、` 均可。
* **多级匹配**：优先匹配三级目录关键词，若无匹配则尝试匹配二级目录关键词。
* **匹配范围**：同时对书签的 **标题 (Title)** 和 **解码后的网址 (URL/域名)** 进行检索。

---

## 🔄 分类优先级逻辑

对于每一个书签，脚本会按以下顺序进行分类判别：

1. **第 1 顺位**：标题为空（无名称网址）➡️ 归入 `Inbox / 无名称`
2. **第 2 顺位**：匹配三级/二级规则关键词 ➡️ 归入对应 `大类 / 中类 / 小类`
3. **第 3 顺位**：标题为网址链接（如 `https://...`）➡️ 归入 `Inbox / 无标签`
4. **第 4 顺位**：未匹配到任何关键词 ➡️ 归入 `Inbox / 无标签`

---

## 📄 开源许可证

[MIT License](https://www.google.com/search?q=LICENSE)
