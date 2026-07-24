# ==============================
# 第1部分
# 导入、分类配置、辅助函数
# ==============================

from html.parser import HTMLParser
from html import escape
from pathlib import Path
import json
import time
import re as _re
import urllib.parse  # 用于 URL 解码

# ==============================
# 繁简转换 & 文本规范化辅助函数
# ==============================

try:
    import zhconv
    def to_simplified(text):
        return zhconv.convert(text, 'zh-hans')
except ImportError:
    try:
        import opencc
        _opencc_converter = opencc.OpenCC('t2s')
        def to_simplified(text):
            return _opencc_converter.convert(text)
    except ImportError:
        # 常用繁简字典映射（降级备用）
        _TC_TO_SC = str.maketrans(
            "網絡數據庫圖書館軟件硬件編程語言開發者學習教學教程文章新聞圖片視頻音頻音樂電影繁體簡體",
            "网络数据库图书馆软件硬件编程语言开发者学习教学教程文章新闻图片视频音频音乐电影繁体简体"
        )
        def to_simplified(text):
            return text.translate(_TC_TO_SC)

def normalize_text(text):
    """
    统一文本规范化：
    1. 解码 URL 转义字符 (如 %E7%99%BE%E5%BA%A6 -> 百度)
    2. 转为小写 (不区分大小写)
    3. 转为简体中文 (不区分繁简)
    """
    if not text:
        return ""
    try:
        text = urllib.parse.unquote(str(text))
    except Exception:
        text = str(text)
    
    text = text.lower()
    text = to_simplified(text)
    return text

def is_ignored_url(url):
    """判断是否为需要过滤忽略的网址（如 https://example.com/）"""
    if not url:
        return False
    clean_url = str(url).strip().lower().rstrip('/')
    return clean_url == "https://example.com"

# ==============================
# 自动分类规则（规则文本版，支持二级/三级目录关键词）
# ==============================

CATEGORIES_RULES_FILE = "categories_rules.txt"

# 行首缩进（空格 或 "│"）+ "├──"/"└──" + 内容；缩进是否为空用来区分二级/三级
_TREE_LINE_RE = _re.compile(r'^(?P<indent>[\s│]*)[├└]──\s*(?P<rest>.+?)\s*$')
# 目录节点解析："名称 (关键词1, 关键词2, ...)" 或仅 "名称"
_NODE_WITH_KW_RE = _re.compile(r'^(?P<name>.+?)(?:\s*\((?P<keywords>.*)\))?\s*$')
_KEYWORD_SPLIT_RE = _re.compile(r'\s*[,\uFF0C\u3001]\s*')
_BRACKET_RE = _re.compile(r'\[[^\[\]]*\]')  # "[...]" 中的内容会被忽略


def _parse_keywords(kw_raw):
    """解析以逗号或顿号分隔的关键词列表，并统一进行规范化（小写+简体）"""
    if not kw_raw:
        return []
    keywords = []
    for kw in _KEYWORD_SPLIT_RE.split(kw_raw):
        kw_clean = kw.strip()
        if kw_clean:
            # 规范化关键字，使其支持不区分大小写与繁简
            keywords.append(normalize_text(kw_clean))
    return keywords


def load_categories_from_text(path):
    """
    从规则文本文件解析出三级嵌套的 CATEGORIES 结构
    """
    categories = {}
    current_main = None
    current_sub = None

    if not Path(path).exists():
        return categories

    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            check = line.strip()

            if not check or check.startswith("#"):
                continue

            line = _BRACKET_RE.sub("", line)
            if not line.strip():
                continue

            m = _TREE_LINE_RE.match(line)
            if m:
                indent = m.group("indent")
                rest = m.group("rest").strip()

                if indent == "":
                    # 行首没有缩进 -> 二级目录
                    if current_main is not None:
                        node_m = _NODE_WITH_KW_RE.match(rest)
                        if node_m:
                            sub_name = node_m.group("name").strip()
                            kw_raw = node_m.group("keywords")
                            current_sub = sub_name
                            categories[current_main][current_sub] = {
                                "_keywords": _parse_keywords(kw_raw)
                            }
                    continue
                else:
                    # 行首有缩进 -> 三级目录
                    if current_main is not None and current_sub is not None:
                        node_m = _NODE_WITH_KW_RE.match(rest)
                        if node_m:
                            leaf_name = node_m.group("name").strip()
                            kw_raw = node_m.group("keywords")
                            categories[current_main][current_sub][leaf_name] = _parse_keywords(kw_raw)
                    continue

            # 一级目录标题
            current_main = line.strip()
            categories[current_main] = {}
            current_sub = None

    return categories


CATEGORIES = load_categories_from_text(CATEGORIES_RULES_FILE)

# ==============================
# HTML辅助函数
# ==============================

def esc_text(value):
    """HTML正文转义"""
    if value is None:
        return ""
    return escape(str(value), quote=False)

def esc_attr(value):
    """HTML属性转义"""
    if value is None:
        return ""
    return escape(str(value), quote=True)

def normalize_attrs(attrs):
    """HTMLParser属性标准化"""
    result = {}
    for k, v in attrs:
        k = k.lower()
        if k in result:
            if isinstance(result[k], list):
                result[k].append(v)
            else:
                result[k] = [result[k], v]
        else:
            result[k] = v
    return result

def split_standard_attrs(attrs):
    """分离标准 Netscape Bookmark 属性"""
    attrs = dict(attrs)
    href = attrs.pop("href", None)
    add_date = attrs.pop("add_date", None)
    last_modified = attrs.pop("last_modified", None)
    icon = attrs.pop("icon", None)
    icon_uri = attrs.pop("icon_uri", None)
    return (attrs, href, add_date, last_modified, icon, icon_uri)

# ==============================
# 分类系统
# ==============================

def build_structure():
    """根据配置构建基础结构，不做预设容器"""
    result = {}
    for main, subs in CATEGORIES.items():
        result[main] = {}
        for sub, sub_data in subs.items():
            result[main][sub] = {}
            for subsub in sub_data:
                if subsub == "_keywords":
                    continue
                result[main][sub][subsub] = []
            if sub not in result[main][sub]:
                result[main][sub][sub] = []

    return result

def categorize_bookmark(title, url):
    """
    分类归类顺序：
    第 1 顺位：判断“无名称网址” -> 归入 Inbox / 无名称
    第 2 顺位：匹配三级/二级规则关键词（匹配对象包括标题与解码后的网址，不区分大小写及繁简） -> 归入对应分类
    第 3 顺位：判断“名称是网址” -> 归入 Inbox / 无标签
    第 4 顺位：未匹配到任何关键词（无标签网址） -> 归入 Inbox / 无标签
    """
    title_str = str(title).strip() if title else ""
    url_str = str(url).strip() if url else ""

    inbox_main = "Inbox"
    sub_no_name = "无名称"
    sub_no_tag = "无标签"

    # 第 1 顺位：判断“无名称网址”
    if not title_str:
        return (inbox_main, sub_no_name, sub_no_name)

    # 规范化标题与解码后的 URL（小写 + 简体）
    norm_title = normalize_text(title_str)
    norm_url = normalize_text(url_str)
    
    # 将标题与 URL 合并为统一匹配文本（实现 URL 链接 / 域名关键字匹配）
    text = norm_title + " " + norm_url

    # 第 2 顺位：匹配三级/二级规则关键词
    # 2.1 匹配三级目录关键词
    for main, subs in CATEGORIES.items():
        for sub, sub_data in subs.items():
            for subsub, keywords in sub_data.items():
                if subsub == "_keywords":
                    continue
                for kw in keywords:
                    if kw and kw in text:
                        return (main, sub, subsub)

    # 2.2 匹配二级目录关键词
    for main, subs in CATEGORIES.items():
        for sub, sub_data in subs.items():
            l2_keywords = sub_data.get("_keywords", [])
            for kw in l2_keywords:
                if kw and kw in text:
                    return (main, sub, sub)

    # 第 3 顺位：判断“名称是网址”
    is_title_url = (
        title_str.lower() == url_str.lower()
        or title_str.lower().startswith(('http://', 'https://', 'www.'))
    )
    if is_title_url:
        return (inbox_main, sub_no_tag, sub_no_tag)

    # 第 4 顺位：未匹配到任何关键词（无标签网址）
    return (inbox_main, sub_no_tag, sub_no_tag)

class BookmarkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = []
        self.stack = [self.root]
        self.current = None
        self.pending_folder = None
        self.last_added = None
        self.capture = None
        self.buf = []
        self.in_dt = False
        self.in_header = True
        self.header = {
            "doctype": None,
            "comment": None,
            "meta": None,
            "title": None,
            "h1": None
        }

    def start_capture(self, name):
        self.capture = name
        self.buf = []

    def finish_capture(self):
        text = "".join(self.buf)
        self.capture = None
        self.buf = []
        return text.strip()

    def append(self, node):
        self.stack[-1].append(node)

    def handle_decl(self, decl):
        if self.in_header and decl.upper().startswith("DOCTYPE"):
            self.header["doctype"] = decl

    def handle_comment(self, data):
        if self.in_header and self.header["comment"] is None:
            self.header["comment"] = data

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs = normalize_attrs(attrs)

        if self.in_header:
            if tag == "meta":
                self.header["meta"] = attrs
                return
            if tag == "title":
                self.start_capture("header_title")
                return
            if tag == "h1":
                self.start_capture("header_h1")
                return

        self.in_header = False

        if tag == "dt":
            self.in_dt = True
            return

        if tag == "p":
            return

        if tag == "dl":
            if self.pending_folder:
                folder = self.pending_folder
                folder["children"] = []
                self.append(folder)
                self.last_added = folder
                self.stack.append(folder["children"])
                self.pending_folder = None
            return

        if tag == "h3":
            other, _, add_date, last_modified, icon, icon_uri = split_standard_attrs(attrs)
            self.current = {
                "type": "folder",
                "title": "",
                "attrs": other,
                "add_date": add_date,
                "last_modified": last_modified,
                "icon": icon,
                "icon_uri": icon_uri,
                "description": None,
                "children": None
            }
            self.start_capture("folder_title")
            return

        if tag == "a":
            other, href, add_date, last_modified, icon, icon_uri = split_standard_attrs(attrs)
            self.current = {
                "type": "bookmark",
                "title": "",
                "attrs": other,
                "href": href,
                "add_date": add_date,
                "last_modified": last_modified,
                "icon": icon,
                "icon_uri": icon_uri,
                "description": None
            }
            self.start_capture("bookmark_title")
            return

        if tag == "hr":
            self.append({"type": "separator"})
            return

        self.append({"type": "raw_tag", "name": tag, "attrs": attrs})

    def handle_endtag(self, tag):
        tag = tag.lower()

        if tag == "title":
            if self.capture == "header_title":
                self.header["title"] = self.finish_capture()
            return

        if tag == "h1":
            if self.capture == "header_h1":
                self.header["h1"] = self.finish_capture()
            return

        if tag == "h3":
            if self.current and self.current["type"] == "folder":
                self.current["title"] = self.finish_capture()
                self.pending_folder = self.current
                self.current = None
            return

        if tag == "a":
            if self.current and self.current["type"] == "bookmark":
                self.current["title"] = self.finish_capture()
                # 校验 URL，如果是 https://example.com/ 则丢弃不添加
                href = self.current.get("href", "")
                if not is_ignored_url(href):
                    self.append(self.current)
                    self.last_added = self.current
                self.current = None
            return

        if tag == "dd":
            if self.last_added and self.capture == "description":
                self.last_added["description"] = self.finish_capture()
            return

        if tag == "dl":
            if len(self.stack) > 1:
                self.stack.pop()
            return

        if tag == "dt":
            self.in_dt = False
            return

    def handle_data(self, data):
        if self.capture:
            self.buf.append(data)

    def handle_entityref(self, name):
        if self.capture:
            self.buf.append("&" + name + ";")

    def handle_charref(self, name):
        if self.capture:
            self.buf.append("&#" + name + ";")

def clean_tree(node):
    if isinstance(node, list):
        return [clean_tree(x) for x in node]
    if isinstance(node, dict):
        return {k: clean_tree(v) for k, v in node.items()}
    return node

def parse_bookmarks_html(text):
    parser = BookmarkParser()
    parser.feed(text)
    parser.close()
    return {"header": parser.header, "items": clean_tree(parser.root)}

# =============================
# HTML生成
# =============================

def render_attrs(attrs):
    if not attrs:
        return ""
    result = []
    for k, v in attrs.items():
        if v is None:
            result.append(f" {k.upper()}")
        elif isinstance(v, list):
            result.append(f' {k.upper()}="{esc_attr(" ".join(map(str, v)))}"')
        else:
            result.append(f' {k.upper()}="{esc_attr(v)}"')
    return "".join(result)

def render_node_attrs(node, is_folder=False):
    result = []
    if not is_folder:
        if node.get("href"):
            result.append(f' HREF="{esc_attr(node["href"])}"')
    for key in ["add_date", "last_modified", "icon", "icon_uri"]:
        if node.get(key):
            result.append(f' {key.upper()}="{esc_attr(node[key])}"')
    result.append(render_attrs(node.get("attrs", {})))
    return "".join(result)

def render_nodes(nodes, level=1):
    lines = []
    indent = "    " * level
    for node in nodes:
        t = node.get("type")
        if t == "separator":
            lines.append(indent + "<HR>")
        elif t == "bookmark":
            lines.append(f'{indent}<DT><A{render_node_attrs(node)}>{esc_text(node.get("title",""))}</A>')
            if node.get("description"):
                lines.append(f'{indent}<DD>{esc_text(node["description"])}')
        elif t == "folder":
            lines.append(f'{indent}<DT><H3{render_node_attrs(node, True)}>{esc_text(node.get("title",""))}</H3>')
            if node.get("description"):
                lines.append(f'{indent}<DD>{esc_text(node["description"])}')
            lines.append(indent + "<DL><p>")
            lines.append(render_nodes(node.get("children", []), level + 1))
            lines.append(indent + "</DL><p>")
    return "\n".join(lines)

def render_header(header):
    lines = []
    if header.get("doctype"):
        lines.append("<!" + header["doctype"] + ">")
    lines.append('<!-- This is an automatically generated file. -->')
    lines.append('<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">')
    lines.append("<TITLE>" + esc_text(header.get("title") or "Bookmarks") + "</TITLE>")
    lines.append("<H1>" + esc_text(header.get("h1") or "Bookmarks") + "</H1>")
    return "\n".join(lines)

def to_html(parsed):
    lines = []
    lines.append(render_header(parsed["header"]))
    lines.append("<DL><p>")
    body = render_nodes(parsed["items"])
    if body:
        lines.append(body)
    lines.append("</DL><p>")
    return "\n".join(lines)

# =============================
# 节点统计
# =============================

def count_nodes(nodes):
    folder = 0
    bookmark = 0
    separator = 0
    raw = 0
    for node in nodes:
        t = node.get("type")
        if t == "folder":
            folder += 1
            a, b, c, d = count_nodes(node.get("children", []))
            folder += a
            bookmark += b
            separator += c
            raw += d
        elif t == "bookmark":
            bookmark += 1
        elif t == "separator":
            separator += 1
        else:
            raw += 1
    return folder, bookmark, separator, raw

def print_stat(title, nodes):
    f, b, s, r = count_nodes(nodes)
    print()
    print("=" * 40)
    print(title)
    print("=" * 40)
    print("文件夹 :", f)
    print("书签   :", b)
    print("分隔线 :", s)
    print("原始项 :", r)
    print("总节点 :", f + b + s + r)

# =============================
# 自动分类生成 HTML
# =============================

def _format_bookmark_line(item, indent_str=""):
    """辅助函数：格式化输出单个书签节点"""
    attrs = [f'HREF="{esc_attr(item["url"])}"']
    if item.get("add_date"):
        attrs.append(f'ADD_DATE="{esc_attr(item["add_date"])}"')
    if item.get("icon"):
        attrs.append(f'ICON="{esc_attr(item["icon"])}"')
    if item.get("icon_uri"):
        attrs.append(f'ICON_URI="{esc_attr(item["icon_uri"])}"')
    if item.get("last_modified"):
        attrs.append(f'LAST_MODIFIED="{esc_attr(item["last_modified"])}"')
    return f'{indent_str}<DT><A {" ".join(attrs)}>{esc_text(item["title"])}</A>'

def build_categorized_html(data):
    lines = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        "<TITLE>Bookmarks</TITLE>",
        "<H1>Bookmarks</H1>",
        "<DL><p>"
    ]
    now = str(int(time.time()))
    dummy_bookmark = {"title": "", "url": "https://example.com"}

    for main, subs in data.items():
        lines.append(f'    <DT><H3 ADD_DATE="{now}" LAST_MODIFIED="{now}">{esc_text(main)}</H3>')
        lines.append("    <DL><p>")
        for sub, subsubs in subs.items():
            lines.append(f'        <DT><H3 ADD_DATE="{now}" LAST_MODIFIED="{now}">{esc_text(sub)}</H3>')
            lines.append("        <DL><p>")
            
            real_l3_keys = [k for k in subsubs.keys() if k != sub]

            for subsub, items in subsubs.items():
                if subsub == sub:
                    # 直接在二级目录下的书签
                    if items:
                        for item in items:
                            lines.append(_format_bookmark_line(item, "            "))
                    elif not real_l3_keys:
                        lines.append(_format_bookmark_line(dummy_bookmark, "            "))
                else:
                    # 三级目录：无书签则填充占位书签
                    lines.append(f'            <DT><H3 ADD_DATE="{now}" LAST_MODIFIED="{now}">{esc_text(subsub)}</H3>')
                    lines.append("            <DL><p>")
                    
                    display_items = items if items else [dummy_bookmark]
                    for item in display_items:
                        lines.append(_format_bookmark_line(item, "                "))

                    lines.append("            </DL><p>")

            lines.append("        </DL><p>")
        lines.append("    </DL><p>")
    lines.append("</DL><p>")
    return "\n".join(lines)

# =============================
# MAIN
# =============================

def main():
    input_file = "bookmarks.html"
    json_file = "bookmarks_full.json"
    restore_file = "bookmarks_restored.html"
    category_file = "bookmarks_categorized.html"

    print("正在解析书签...")

    raw = Path(input_file).read_text(encoding="utf-8", errors="ignore")
    parsed = parse_bookmarks_html(raw)

    Path(json_file).write_text(
        json.dumps(parsed, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    restored = to_html(parsed)
    Path(restore_file).write_text(restored, encoding="utf-8")

    parsed2 = parse_bookmarks_html(restored)

    print_stat("原始解析结果", parsed["items"])
    print_stat("恢复HTML再次解析", parsed2["items"])

    a = count_nodes(parsed["items"])
    b = count_nodes(parsed2["items"])

    print()
    print("=" * 40)
    print("最终验证")
    print("=" * 40)
    if a == b:
        print("✔ 节点数量一致")
        print("✔ 转换通过")
    else:
        print("❌ 数据不一致")
        print("原:", a)
        print("新:", b)

    # 分类输出
    structured = build_structure()

    def walk(nodes):
        for node in nodes:
            if node["type"] == "folder":
                walk(node.get("children", []))
            elif node["type"] == "bookmark":
                title = node.get("title", "")
                url = node.get("href", "")
                main, sub, subsub = categorize_bookmark(title, url)

                # 如果当前没有对应目录（包括按需生成的 Inbox/无名称/无标签），就新建这个对应目录
                if main not in structured:
                    structured[main] = {}
                if sub not in structured[main]:
                    structured[main][sub] = {}
                if subsub not in structured[main][sub]:
                    structured[main][sub][subsub] = []

                structured[main][sub][subsub].append({
                    "title": title,
                    "url": url,
                    "add_date": node.get("add_date"),
                    "icon": node.get("icon"),
                    "icon_uri": node.get("icon_uri"),
                    "last_modified": node.get("last_modified"),
                })

    walk(parsed["items"])

    Path(category_file).write_text(
        build_categorized_html(structured),
        encoding="utf-8"
    )

    print()
    print("已生成:", restore_file)
    print("已生成:", category_file)

if __name__ == "__main__":
    main()