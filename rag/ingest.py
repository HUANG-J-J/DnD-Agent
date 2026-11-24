"""把 SRD 规则书 PDF 按标题切块，输出 rag/chunks.jsonl。

每遇到一个标题（章 / 节 / 小节 / 词条）就开始新的一块，
块里记下标题路径和页码，方便调试和引用。

用法（项目根目录）：python -m rag.ingest
"""

import json
import re
from pathlib import Path

import pymupdf

PDF_PATH = Path("rules/SRD_CC_v5.2.pdf")
OUT_PATH = Path("rag/chunks.jsonl")
FIRST_PAGE = 4      # 从 0 数；前 4 页是版权页和目录，第 5 页开始是正文
MAX_CHARS = 2500    # 超过这个长度的块再按段落切开

# 规则书里标题用 GillSans-SemiBold，字号决定层级
HEADING_LEVELS = {26.0: 1, 18.0: 2, 14.8: 3, 14.0: 3, 12.0: 4}


def heading_level(span):
    if span["font"] != "GillSans-SemiBold":
        return None
    return HEADING_LEVELS.get(round(span["size"], 1))


def is_page_furniture(span):
    # 页眉 "System Reference Document 5.2" 和页码都是 11 号 GillSans
    # 注意小型大写字母标题（GillSans-Bold-SC700）的首字母也是 11 号，不能误删
    return round(span["size"], 1) == 11.0 and span["font"] in ("GillSans", "GillSans-SemiBold")


def clean(text):
    text = re.sub(r"(\w) ?-\n(\w)", r"\1\2", text)   # 断行连字符：experi -\nence → experience
    text = re.sub(r"\n(?=\S)", " ", text)            # 普通换行并成空格；以空格开头的条目行保留换行
    return re.sub(r"[ \t]+", " ", text).strip()


def split_long(text):
    """太长的块按句子切开，每段不超过 MAX_CHARS。"""
    if len(text) <= MAX_CHARS:
        return [text]
    parts, buf = [], ""
    for sentence in re.split(r"(?<=[.!?”])\s+", text):
        if buf and len(buf) + len(sentence) > MAX_CHARS:
            parts.append(buf.strip())
            buf = ""
        buf += sentence + " "
    if buf.strip():
        parts.append(buf.strip())
    return parts


def iter_lines(doc):
    """逐行产出 (页码, 标题层级或 None, 文字)。"""
    for pno in range(FIRST_PAGE, len(doc)):
        for block in doc[pno].get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                spans = [s for s in line["spans"] if s["text"].strip() and not is_page_furniture(s)]
                if not spans:
                    continue
                levels = {heading_level(s) for s in spans}
                level = levels.pop() if len(levels) == 1 else None
                yield pno + 1, level, "".join(s["text"] for s in spans)


def build_chunks(doc):
    chunks = []
    path = [None] * 4           # 当前所处的 章 / 节 / 小节 / 词条
    lines, page, last_was_heading = [], None, False

    def flush():
        body = clean("\n".join(lines))
        if not body:
            return
        title = " > ".join(p for p in path if p)
        for i, part in enumerate(split_long(body)):
            chunks.append({
                "id": f"p{page}-{len(chunks)}",
                "title": title,
                "chapter": path[0],
                "page": page,
                "part": i,
                "text": part,
            })

    for pno, level, text in iter_lines(doc):
        if level is None:
            page = page or pno
            lines.append(text)
            last_was_heading = False
            continue
        text = text.strip()
        if last_was_heading and not lines and path[level - 1]:
            path[level - 1] += " " + text       # 标题折成了两行，拼回去
            continue
        flush()
        path[level - 1] = text
        for deeper in range(level, 4):
            path[deeper] = None
        lines, page, last_was_heading = [], pno, True

    flush()
    return chunks


def main():
    doc = pymupdf.open(PDF_PATH)
    chunks = build_chunks(doc)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    lengths = sorted(len(c["text"]) for c in chunks)
    print(f"共 {len(chunks)} 块，写入 {OUT_PATH}")
    print(f"长度：最短 {lengths[0]}，中位数 {lengths[len(lengths) // 2]}，最长 {lengths[-1]}")


if __name__ == "__main__":
    main()
