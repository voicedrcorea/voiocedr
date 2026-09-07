#!/usr/bin/env python3
"""내가 쓴 초안과 사장님이 고쳐 발행한 원고를 비교한다.

무엇을 고치셨는지를 수치와 문장 단위로 뽑아내, 다음 글에 반영할 규칙을 찾는다.

사용:
    python3 scripts/compare_revision.py drafts/2026-09-05/1.md revisions/2026-09-05__1.md
"""
import argparse
import difflib
import re
import sys

ENDINGS = [
    ("~습니다/~입니다", r"(습니다|입니다)[.\s]"),
    ("~죠/~거죠", r"(죠)[.\s]"),
    ("~겁니다", r"(겁니다)[.\s]"),
    ("~요", r"(어요|아요|에요|예요)[.\s]"),
]

DOGMA = [
    "소리를 잘 낼 수 있는", "17년", "오직 1:1", "1:1",
    "여러분", "보이스 닥터", "회원제", "당일 방문",
]


def load(path):
    text = open(path, encoding="utf-8").read()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            text = parts[2]
    for marker in ("## 이미지 삽입 지시", "## 태그"):
        text = text.split(marker)[0]
    return text.replace("## 본문", "").strip()


def stats(text):
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    clean = re.sub(r"\[[^\]]*\]", "", text)
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n\n", clean) if len(s.strip()) > 3]
    chars = len(re.sub(r"\s", "", clean))
    return {
        "chars": chars,
        "blocks": len(blocks),
        "sents": len(sents),
        "avg_sent": chars / len(sents) if sents else 0,
        "block_list": blocks,
    }


def bar(label, a, b, unit=""):
    d = b - a
    arrow = "→" if d == 0 else ("↑" if d > 0 else "↓")
    pct = f"{d/a*100:+.0f}%" if a else "—"
    return f"  {label:<16}{a:>8.0f}{unit}  {arrow}{b:>8.0f}{unit}   ({d:+.0f}{unit}, {pct})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("draft", help="내가 쓴 초안")
    ap.add_argument("revision", help="사장님이 고쳐 발행한 원고")
    args = ap.parse_args()

    a_txt, b_txt = load(args.draft), load(args.revision)
    a, b = stats(a_txt), stats(b_txt)

    print("=" * 74)
    print(f"초안   {args.draft}")
    print(f"발행본 {args.revision}")
    print("=" * 74)

    print("\n[ 분량 ]")
    print(bar("글자수(공백제외)", a["chars"], b["chars"], "자"))
    print(bar("줄바꿈 블록", a["blocks"], b["blocks"], "개"))
    print(bar("문장 수", a["sents"], b["sents"], "개"))
    print(bar("평균 문장 길이", a["avg_sent"], b["avg_sent"], "자"))

    print("\n[ 어미 분포 ]")
    for name, pat in ENDINGS:
        ca, cb = len(re.findall(pat, a_txt)), len(re.findall(pat, b_txt))
        print(bar(name, ca, cb, "회"))

    print("\n[ 브랜드 문구 ]")
    for w in DOGMA:
        ca, cb = a_txt.count(w), b_txt.count(w)
        if ca or cb:
            mark = "  " if ca == cb else ("  ← 줄임" if cb < ca else "  ← 늘림")
            print(f"  {w:<22}{ca:>3} → {cb:>3}{mark}")

    sm = difflib.SequenceMatcher(None, a["block_list"], b["block_list"])
    print(f"\n[ 블록 일치율 ] {sm.ratio()*100:.0f}%")

    removed, added = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace"):
            removed += a["block_list"][i1:i2]
        if tag in ("insert", "replace"):
            added += b["block_list"][j1:j2]

    def show(title, items, limit=25):
        print(f"\n[ {title} · {len(items)}개 ]")
        for x in items[:limit]:
            print(f"  - {x[:70]}{'…' if len(x) > 70 else ''}")
        if len(items) > limit:
            print(f"  … 외 {len(items)-limit}개")

    show("빼신 문장", removed)
    show("넣으신 문장", added)

    print("\n" + "=" * 74)
    print("이 결과를 brand/tone-and-manner.md 의 H섹션에 규칙으로 옮기세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
