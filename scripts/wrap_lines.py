#!/usr/bin/env python3
"""원고 본문을 네이버 스마트에디터 모바일 줄바꿈 양식으로 다시 감는다.

한 줄 최대 24자 (모바일에서 오른쪽에 2~3칸 여백이 남는 지점).
어절 경계에서만 끊고, 문장이 길면 의미 단위로 먼저 아래줄로 내린다.
문단(빈 줄) 구분은 그대로 둔다.

사용:
    python3 scripts/wrap_lines.py drafts/2026-09-07/*.md
    python3 scripts/wrap_lines.py --check drafts/2026-09-07/*.md   # 검사만
"""
import argparse
import os
import re
import sys

MAX = 24          # 한 줄 최대
PREFER = 22       # 이 길이를 넘으면 다음 어절부터 새 줄
# 의미 단위 경계 — 이 어절 뒤에서는 우선적으로 줄을 바꾼다
BREAK_AFTER = re.compile(
    r"(습니다|입니다|겁니다|합니다|됩니다|입니까|까요|나요|죠|"
    r"만|지만|는데|시면|하면|이며|이고|하고|아니라|때문에|그래서|그런데)[.,?!]?$"
)
# 손대지 않는 블록
SKIP = ("[", '"', "'", "#", "|", "-", "1.", "2.", "3.", "4.", "5.", "6.")


SENT_END = re.compile(r"(?<=[.?!])\s+")


def wrap_sentence(sent):
    """한 문장을 24자 이하 줄들로 감는다. 어절 경계에서만 끊는다."""
    words = sent.split()
    lines, cur = [], ""
    for w in words:
        cand = w if not cur else cur + " " + w
        if len(cand) > MAX and cur:
            lines.append(cur)
            cur = w
        else:
            cur = cand
            # 의미 단위 경계이고 이미 충분히 길면 여기서 끊는다
            if len(cur) >= PREFER and BREAK_AFTER.search(w):
                lines.append(cur)
                cur = ""
    if cur:
        lines.append(cur)
    return lines


def wrap_para(text):
    """한 문단을 줄 단위로 다시 감는다.

    이 필자는 문장마다 새 줄에서 시작한다. 문장을 먼저 나눈 뒤
    각 문장을 24자 이하로 감는다. 서로 다른 문장을 한 줄에 섞지 않는다.
    """
    flat = text.replace("\n", " ").strip()
    lines = []
    for sent in SENT_END.split(flat):
        if sent.strip():
            lines += wrap_sentence(sent.strip())
    return "\n".join(lines)


def process(body):
    out = []
    for para in body.split("\n\n"):
        p = para.strip()
        if not p:
            continue
        out.append(p if p.startswith(SKIP) else wrap_para(p))
    return "\n\n".join(out)


def offenders(body):
    bad = []
    for para in body.split("\n\n"):
        p = para.strip()
        if not p or p.startswith(SKIP):
            continue
        for line in p.split("\n"):
            if len(line) > MAX:
                bad.append(line)
    return bad


def split_doc(text):
    head, rest = text.split("## 본문", 1)
    body, tail = rest.split("## 이미지 삽입 지시", 1)
    return head, body, tail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--check", action="store_true", help="고치지 않고 검사만")
    args = ap.parse_args()

    failed = 0
    for path in args.targets:
        text = open(path, encoding="utf-8").read()
        try:
            head, body, tail = split_doc(text)
        except ValueError:
            print(f"✗ {path}: 본문 구획을 찾지 못했습니다")
            failed += 1
            continue

        if args.check:
            bad = offenders(body)
            if bad:
                failed += 1
                print(f"✗ {path}  {MAX}자 초과 {len(bad)}줄")
                for b in bad[:5]:
                    print(f"    {len(b):>3}자  {b}")
            else:
                print(f"✓ {path}  모든 줄 {MAX}자 이하")
            continue

        new_body = "\n\n" + process(body) + "\n\n"
        lines_before = sum(len(p.split("\n")) for p in body.split("\n\n") if p.strip())
        lines_after = sum(len(p.split("\n")) for p in new_body.split("\n\n") if p.strip())
        out = head + "## 본문" + new_body + "## 이미지 삽입 지시" + tail

        clean = re.sub(r"\[[^\]]*\]", "", new_body)
        chars = len(re.sub(r"\s", "", clean))
        blocks = len([x for x in new_body.split("\n\n") if x.strip()])
        out = re.sub(r"chars_excl_space: \d+", f"chars_excl_space: {chars}", out)
        out = re.sub(r"blocks: \d+", f"blocks: {blocks}", out)

        tmp = path + ".tmp"
        open(tmp, "w", encoding="utf-8").write(out)
        os.replace(tmp, path)
        print(f"{path}  줄 {lines_before} → {lines_after}  ({chars}자 / {blocks}문단)")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
