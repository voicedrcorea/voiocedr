#!/usr/bin/env python3
"""보이스닥터 유사문서 검사기.

새 원고가 기존 글(corpus + 과거 drafts + 같은 날 다른 원고)과
연속 N자 이상 겹치는지 검사한다. 기본 N=15.

브랜드 도그마 문구는 의도적 반복이므로 검사에서 제외한다.

사용:
    python3 scripts/check_similarity.py drafts/2026-09-06/1.md
    python3 scripts/check_similarity.py drafts/2026-09-06/*.md --n 15
"""
import argparse
import glob
import os
import re
import sys

# 의도적으로 반복하는 브랜드 문구 — 유사도 계산에서 제외
DOGMA = [
    "소리를 잘 낼 수 있는 상태",
    "소리를 잘 낼 수 있는 몸 상태",
    "소리를 낼 수 있는 몸 상태",
    "17년 발성 전문 트레이닝 센터 보이스 닥터입니다",
    "17년 차 발성 전문 트레이닝 센터 보이스 닥터입니다",
    "17년 경력 발성 전문 센터 보이스 닥터입니다",
    "발성 전문 트레이닝 센터",
    "오직 1:1",
    "회원제로 운영되며 당일 방문은",
    "당일 방문은 불가하니",
    "전문 직종의 목소리는 지문과 같기에",
    "전문 직업군은 목소리가 지문과 같기에",
]

DEFAULT_N = 15


def load_body(path):
    """YAML frontmatter를 걷어내고 본문만 반환."""
    text = open(path, encoding="utf-8").read()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            text = parts[2]
    return text


def normalize(text):
    """공백·문장부호를 제거해 표기 흔들림에 강한 형태로 만든다."""
    for phrase in DOGMA:
        text = text.replace(phrase, "\x00")
    text = re.sub(r"\[[^\]]*\]", " ", text)          # [영상 삽입] 등 지시문 제외
    text = re.sub(r"[^\w가-힣]", "", text)            # 공백·문장부호 제거
    return text


def shingles(text, n):
    return {text[i:i + n] for i in range(len(text) - n + 1)}


def longest_match(a, b_shingles, n):
    """a 안에서 b와 겹치는 가장 긴 연속 구간의 길이와 그 문자열."""
    best_len, best_str = 0, ""
    i = 0
    while i <= len(a) - n:
        if a[i:i + n] in b_shingles:
            j = i + n
            while j < len(a) and a[i:j + 1][-n:] in b_shingles:
                j += 1
            if j - i > best_len:
                best_len, best_str = j - i, a[i:j]
            i = j - n + 1
        else:
            i += 1
    return best_len, best_str


def references(target, extra):
    refs = sorted(glob.glob("corpus/*.md"))
    refs += sorted(glob.glob("drafts/*/*.md"))
    refs += extra
    tgt = os.path.abspath(target)
    return [r for r in dict.fromkeys(refs) if os.path.abspath(r) != tgt]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--n", type=int, default=DEFAULT_N,
                    help=f"허용 최대 연속 일치 글자수 (기본 {DEFAULT_N})")
    args = ap.parse_args()

    failed = False
    for target in args.targets:
        body = normalize(load_body(target))
        print(f"\n■ {target}  ({len(body)}자, 정규화 기준)")
        worst = 0
        for ref in references(target, args.targets):
            ref_sh = shingles(normalize(load_body(ref)), args.n)
            if not ref_sh:
                continue
            length, matched = longest_match(body, ref_sh, args.n)
            if length >= args.n:
                failed = True
                worst = max(worst, length)
                print(f"   ✗ {os.path.basename(ref)}  {length}자 일치")
                print(f'      "{matched[:60]}{"..." if len(matched) > 60 else ""}"')
        if worst == 0:
            print(f"   ✓ 통과 — {args.n}자 이상 연속 일치 없음")

    if failed:
        print("\n=> 재작성이 필요합니다. 위에 표시된 문장을 바꾸세요.")
        return 1
    print("\n=> 전체 통과.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
