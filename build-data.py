import json
from pathlib import Path

root = Path(__file__).resolve().parent
DEFAULT_CHARS = 7000
MAX_RAW_CHARS = 10000

SOURCE_FILES = [
    "source.json",
    "source-continue.json",
]


def truncate_latest(text: str, max_chars: int) -> str:
    """取最新 max_chars 字（从尾部截断，尽量从段落边界开始）。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if len(text) <= max_chars:
        return text

    chunk = text[-max_chars:]
    first_break = chunk.find("\n")
    if 0 <= first_break < 200:
        chunk = chunk[first_break + 1 :]
    return chunk.lstrip("\n")


def parse_source_file(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    row = next(x for x in raw if x.get("result_json"))
    meta = json.loads(row["result_json"])
    raw_content = truncate_latest(meta["latest_10k_content"] or "", MAX_RAW_CHARS)
    content = truncate_latest(raw_content, DEFAULT_CHARS)
    paras = [p.strip() for p in content.split("\n") if p.strip()]
    display_chars = sum(len(p) for p in paras)
    return {
        "title": f"{meta['book_name']} 第{meta['published_chapter_cnt']}章",
        "bookName": meta["book_name"],
        "bookId": meta.get("book_id"),
        "chapterIndex": meta.get("published_chapter_cnt"),
        "wordCount": meta["word_count"],
        "displayChars": display_chars,
        "lengthBucket": DEFAULT_CHARS,
        "rawContent": raw_content,
        "reward": {"text": "阅读奖励", "visible": True},
        "paragraphs": [{"id": i + 1, "content": c} for i, c in enumerate(paras)],
    }


chapters = []
for name in SOURCE_FILES:
    path = root / name
    if not path.exists():
        print(f"skip missing: {name}")
        continue
    chapter = parse_source_file(path)
    chapters.append(chapter)
    print(
        f"{name}: {chapter['title']} "
        f"(raw {len(chapter['rawContent'])} chars, "
        f"default {chapter['displayChars']} chars, "
        f"{len(chapter['paragraphs'])} paragraphs)"
    )

payload = "window.CHAPTERS_DATA = " + json.dumps(chapters, ensure_ascii=False, indent=2) + ";\n"
payload += "window.CHAPTER_DATA = window.CHAPTERS_DATA[0];\n"
root.joinpath("chapters-data.js").write_text(payload, encoding="utf-8")
print(f"Generated chapters-data.js ({len(payload.encode('utf-8'))} bytes, {len(chapters)} chapters)")
