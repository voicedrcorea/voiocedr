#!/usr/bin/env python3
"""H섹션 확정 규칙이 원고에 실제로 들어갔는지 검사한다.

왜 만들었나.

2026-09-16 발행본에서 사장님이 초안에 **없던 것들을 채워 넣으셨다.**
`여러분` 호칭 0회, `운영` 1회, 전문 트레이너 문장 0회.
분량도 1,505자로 짧았고 사장님이 138자를 더하셨다.

전부 H섹션에 적혀 있거나 적혔어야 할 규칙인데, 검사기가 없어서
"지켰다고 생각하고" 넘어갔다. 문서에만 적힌 규칙은 지켜지지 않는다.

사용
    python3 scripts/check_voice.py drafts/2026-09-21/*.md
"""
import io
import re
import sys

BODY_START = "## 본문"
BODY_END = ("## 이미지 삽입 지시", "## 태그")


def body(path):
    t = io.open(path, encoding="utf-8").read()
    if BODY_START in t:
        t = t.split(BODY_START, 1)[1]
    for m in BODY_END:
        if m in t:
            t = t.split(m, 1)[0]
    return t


# (이름, 판정 함수, 근거)
def rules(b, n):
    """b = 공백 정규화한 본문, n = 공백 제외 글자수."""
    return [
        ("H14 분량 1,600~1,900자", 1600 <= n <= 1900,
         f"{n}자 — 1,500 아래면 빠진 단계를, 2,000 위면 군더더기를 찾는다"),
        ("H16 보이스 닥터 3회+", b.count("보이스 닥터") >= 3,
         f"{b.count('보이스 닥터')}회"),
        ("H16 1:1 2회+", b.count("1:1") >= 2, f"{b.count('1:1')}회"),
        ("H18 여러분 4회+", b.count("여러분") >= 4, f"{b.count('여러분')}회"),
        ("H19 운영 3회+", b.count("운영") >= 3, f"{b.count('운영')}회"),
        ("H20 전문 트레이너 문장", "전문 트레이너" in b, "마무리 CTA 앞자리"),
        ("H8 물음표 반문 2회+", len(re.findall(r"까요\?", b)) >= 2,
         f"{len(re.findall(r'까요.', b))}회"),
        ("영상 자리표시", "비포&애프터 영상 삽입" in b, "면책 괄호 뒤"),
        ("접기/펴기 요약", "접기/펴기" in b, "H21 — 그대로 발행되는 블록"),
        ("17년 2회 내외", b.count("17년") >= 1, f"{b.count('17년')}회"),
    ]


def main():
    paths = sys.argv[1:]
    if not paths:
        sys.exit(__doc__)
    bad = 0
    for p in paths:
        raw = body(p)
        b = re.sub(r"\s+", " ", raw)
        n = len(re.sub(r"\s", "", raw))
        short = "/".join(p.rstrip("/").split("/")[-2:])
        fails = [(name, why) for name, ok, why in rules(b, n) if not ok]
        if fails:
            bad += 1
            print(f"\n■ {short}")
            for name, why in fails:
                print(f"   ✗ {name:<26} {why}")
        else:
            print(f"■ {short}\n   ✓ 통과 — H섹션 확정 규칙 전부 충족")
    print()
    if bad:
        print(f"=> {bad}개 원고에 빠진 규칙이 있습니다. 채우고 다시 돌리세요.")
        print("   분량이 모자라면 문장을 늘리지 말고 위에 걸린 항목부터 넣으세요.")
        return 1
    print("=> 전체 통과.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
