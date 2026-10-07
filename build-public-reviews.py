# -*- coding: utf-8 -*-
"""从 SQLPad 导出结果生成大众评价数据 public-reviews-data.js"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import openpyxl

SRC = Path(r"c:\Users\ihuab\Downloads\SQLPad Query Results 2026-10-07.xlsx")
OUT = Path(__file__).resolve().parent / "public-reviews-data.js"

Q2 = [
    "剧情精彩", "节奏舒服", "人物鲜活", "文笔流畅", "对话自然",
    "很有吸引力", "越看越想看", "整体完成度高", "没有明显问题", "其他",
]
Q3 = [
    "剧情重复", "内容拖沓", "逻辑混乱", "人物单薄", "对话生硬",
    "文笔不佳", "语言啰嗦", "有水文，凑字数现象", "题材老套无聊", "其他",
]
USELESS = {"没有", "无", "无。", "没有。", "暂无", "好", "ok", "OK", "1", "啊", "嗯", "无无", "没有没有"}


def parse_codes(s):
    if s is None or s == "":
        return []
    out = []
    for part in str(s).replace("，", ",").split(","):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return out


def codes_to_labels(codes, table):
    labels = []
    for c in codes:
        if 1 <= c <= len(table):
            labels.append(table[c - 1])
    return labels


def clean_text(v):
    if v is None:
        return ""
    text = str(v).strip()
    return "" if text in USELESS else text


def main():
    wb = openpyxl.load_workbook(SRC, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    headers = [str(h) for h in rows[0]]

    books = defaultdict(lambda: {"want": 0, "notWant": 0, "maybe": 0, "comments": []})
    all_want = all_not = all_maybe = 0
    global_comments = []

    for r in rows[1:]:
        d = {headers[i]: r[i] for i in range(len(headers))}
        name = (d.get("书名") or "").strip() or "未知书名"
        try:
            q4 = int(d.get("Q4评分"))
        except Exception:
            q4 = 3

        # Q4: 5很想/4想继续/3看情况/2不太想/1不想 → 展示口径：>=3 想看，<=2 不想看
        if q4 >= 3:
            intent = "want" if q4 >= 4 else "maybe"
            books[name]["want"] += 1
            all_want += 1
            if q4 == 3:
                all_maybe += 1
                books[name]["maybe"] += 1
        else:
            intent = "not_want"
            books[name]["notWant"] += 1
            all_not += 1

        q2_labels = codes_to_labels(parse_codes(d.get("Q2选项编码")), Q2)
        q3_labels = codes_to_labels(parse_codes(d.get("Q3选项编码")), Q3)
        q2_other = clean_text(d.get("Q2其他评语"))
        q3_other = clean_text(d.get("Q3其他评语"))
        text_parts = [t for t in (q2_other, q3_other) if t]
        text = "；".join(text_parts)
        tags = q2_labels + q3_labels
        if not text and len(tags) < 2:
            continue

        uid = d.get("用户ID")
        user = f"读者{(uid % 10000):04d}" if isinstance(uid, int) else "匿名读者"
        item = {
            "user": user,
            "intent": intent,
            "tags": tags[:6],
            "text": text or ("选了：" + "、".join(tags[:3])),
            "bookName": name,
        }
        books[name]["comments"].append(item)
        global_comments.append(item)

    ranked = sorted(books.items(), key=lambda kv: len(kv[1]["comments"]), reverse=True)
    book_map = {}
    for name, info in ranked[:20]:
        rich = [c for c in info["comments"] if c["text"] and not c["text"].startswith("选了：")]
        lean = [c for c in info["comments"] if c not in rich]
        book_map[name] = {
            "bookName": name,
            "want": info["want"],
            "notWant": info["notWant"],
            "maybe": info["maybe"],
            "comments": (rich + lean)[:10],
        }

    rich_global = [c for c in global_comments if c["text"] and not c["text"].startswith("选了：")]
    want_c = [c for c in rich_global if c["intent"] == "want"][:20]
    not_c = [c for c in rich_global if c["intent"] == "not_want"][:20]
    maybe_c = [c for c in rich_global if c["intent"] == "maybe"][:10]
    sample = []
    for i in range(max(len(want_c), len(not_c), len(maybe_c))):
        if i < len(want_c):
            sample.append(want_c[i])
        if i < len(not_c):
            sample.append(not_c[i])
        if i < len(maybe_c):
            sample.append(maybe_c[i])
    sample = sample[:24]

    payload = {
        "generatedFrom": SRC.name,
        "totalReviews": len(rows) - 1,
        "global": {"want": all_want, "notWant": all_not, "maybe": all_maybe},
        "sampleComments": sample,
        "books": book_map,
    }
    OUT.write_text(
        "window.PUBLIC_REVIEWS_DATA = "
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + ";\n",
        encoding="utf-8",
    )
    print("ok", OUT, "bytes", OUT.stat().st_size)
    print("global want/not", all_want, all_not, "sample", len(sample), "books", len(book_map))


if __name__ == "__main__":
    main()
