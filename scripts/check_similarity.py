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

# 의도적으로 반복하는 브랜드 문구 — 유사도 계산에서 제외한다.
#
# 제외 기준: 브랜드 정체성 선언과 CTA 정형구만 넣는다.
# 본문의 논리 전개 문장은 절대 넣지 않는다. (넣으면 검사가 무의미해진다)
DOGMA = [
    # 브랜드 도그마
    "소리를 잘 낼 수 있는 상태",
    "소리를 잘 낼 수 있는 몸 상태",
    "소리를 낼 수 있는 몸 상태",
    "소리를 안정적으로 낼 수 있는 상태",
    "발성 전문 트레이닝 센터 보이스 닥터입니다",
    "발성 전문 센터 보이스 닥터입니다",
    "발성 전문 트레이닝 센터",
    "안녕하세요. 17년 차",
    "안녕하세요 17년",
    "17년 차",
    "17년 경력",
    "그래서 보이스 닥터는 오직 1:1로만 진행합니다",
    "저희는 오직 1:1 트레이닝만 진행합니다",
    "오직 1:1로만",
    "오직 1:1",
    # 비포&애프터 면책 정형구
    "전문 직종의 목소리는 지문과 같기에",
    "전문 직업군은 목소리가 지문과 같기에",
    "비포&애프터 영상입니다",
    "비포 & 애프터 영상입니다",
    "등 전문 직종의 목소리는 지문과 같기에 별도 공개하지 않습니다",
    "별도 공개하지 않습니다",
    "공개하지 않습니다",
    "일반인 사례이며",
    "일반인 사례입니다",
    # CTA 정형구
    "회원제로 운영되며 당일 방문은",
    "회원제로 운영되어 당일 방문 상담은 어렵습니다",
    "회원제로 운영되고 있어 당일 방문 상담은 어렵습니다",
    "당일 방문은 불가하니",
    "당일 방문 상담은 어렵습니다",
    "당일 방문은 어렵습니다",
    "아래 연락처로 먼저 문의",
    "아래 번호로 미리 연락",
    "일정 조율 부탁드립니다",
    "일정을 확인해 주시기 바랍니다",
]

DEFAULT_N = 15


# 원고 파일에서 본문이 끝나는 지점 — 이 뒤는 지시문·태그이므로 비교 대상이 아니다
BODY_END_MARKERS = ("## 이미지 삽입 지시", "## 태그")


def load_body(path):
    """frontmatter와 부가 섹션을 걷어내고 실제 원고 본문만 반환."""
    text = open(path, encoding="utf-8").read()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            text = parts[2]
    for marker in BODY_END_MARKERS:
        text = text.split(marker)[0]
    return text.replace("## 본문", "")


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


def short(path):
    """corpus/x.md 또는 2026-09-05/1.md 처럼 구분 가능한 짧은 이름."""
    parts = os.path.normpath(path).split(os.sep)
    return os.sep.join(parts[-2:]) if len(parts) >= 2 else path


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
                print(f"   ✗ {short(ref)}  {length}자 일치")
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
