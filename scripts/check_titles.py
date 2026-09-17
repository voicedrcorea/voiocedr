#!/usr/bin/env python3
"""제목 후보 검증기 — 네이버 스마트블록 대응 규칙을 강제한다.

규칙 (brand/tone-and-manner.md E섹션)
  - 후보 6개, 유형이 모두 다를 것
  - 메인 키워드가 제목 맨 앞에 올 것
  - 메인 키워드가 제목 안에서 1회만 나올 것 (반복은 스터핑 감점)
  - 18~30자 (모바일 검색결과에서 잘리지 않게)
  - 특수문자·이모지 금지 (질문형의 '~일까요'는 허용)

2026-09-17 추가 — 사장님이 **4편 연속으로 내 후보를 하나도 안 쓰셨다.**
발행 제목 네 개를 나란히 놓으면 구조가 같다.

    강사 목소리   | 쉬는 건           | 성대가 약해서가 아닙니다
    목소리 떨림   | 반복되는 이유는     | 발성 문제
    유튜버 목소리 | 발음이 잘 안되는건  | 결국 발성 문제
    배우 오디션   | 잘 보는 법         | 결국 발성이 문제인 이유

    [메인 키워드] + [확장 검색어] + [결론]

가운데가 **또 하나의 검색어**다. 제목 하나로 키워드 두 개를 먹는다.
내 제목은 가운데가 서술어였다 — `아무리 관리해도` `아무리 참으려 해도`
`소리가 무너지는 건`. 검색되지 않는 말이다. 그래서 네 번 다 버려졌다.

사용:
    python3 scripts/check_titles.py drafts/2026-09-05/*.md
"""
import re
import sys

TYPES = ["단정형", "부정형", "원인형", "방법형", "증상형", "질문형"]
RESERVE = ["대상형", "비교형"]  # 위 6개로 못 채울 때만 쓰는 예비 유형
MIN_LEN, MAX_LEN = 18, 30
BANNED = re.compile(r"[!~★☆♥♡…※•▶◀▲▼✔✅🔥]|[\U0001F300-\U0001FAFF]")

# 내 제목 버릇. 후보 122개에는 쓰였고 발행본 4편에는 **한 번도** 안 나온다.
# 전부 키워드 뒤에 붙는 서술어라서 검색어가 되지 못한다
TIC = {
    "아무리": 15,      # 아무리 관리해도 / 아무리 참으려 해도
    "먼저": 22,        # ~보다 먼저 할 것
    "경우": 9,         # ~하는 경우
    "진짜 이유": 3,
}

# 브랜드가 제목에 박는 결론. 발행본 4편 중 3편에 있다
CONCLUSION = re.compile(r"(발성 문제|발성이 문제|발성의 문제)")


def parse(path):
    text = open(path, encoding="utf-8").read()
    kw = re.search(r"^keyword:\s*(.+)$", text, re.M)
    titles = re.findall(r"^  - (.+?)\s*\|\s*(.+)$", text, re.M)
    return (kw.group(1).strip() if kw else ""), titles


def main():
    failed = 0
    for path in sys.argv[1:]:
        kw, titles = parse(path)
        print(f"\n■ {path}   메인 키워드: {kw}")
        if not kw:
            print("   ✗ keyword 항목이 없습니다"); failed += 1; continue
        if len(titles) != 6:
            print(f"   ✗ 제목 후보가 {len(titles)}개 — 6개여야 합니다"); failed += 1
        seen = [ty for ty, _ in titles]
        for want in TYPES:
            if want not in seen and not (set(seen) & set(RESERVE)):
                print(f"   ✗ '{want}' 유형이 빠졌습니다"); failed += 1
        for dup in {ty for ty in seen if seen.count(ty) > 1}:
            print(f"   ✗ '{dup}' 유형이 중복입니다"); failed += 1

        # 내 버릇 — 발행본에 한 번도 안 나온 말들
        for ty, title in titles:
            for word, n in TIC.items():
                if word in title:
                    print(f"   ✗ '{word}' 는 내 버릇입니다 "
                          f"(내 후보 {n}회 / 발행본 0회) — {title}")
                    failed += 1

        # 결론을 박는 제목이 최소 2개
        n_conc = sum(1 for _, ti in titles if CONCLUSION.search(ti))
        if n_conc < 2:
            print(f"   ✗ '결국 발성 문제' 형 결론이 {n_conc}개 "
                  f"— 최소 2개는 있어야 합니다 (발행본 3/4)")
            failed += 1

        # 키워드 바로 뒤 어절이 검색어로 이어지는지 (기계 판정은 어려워 안내만)
        for ty, title in titles:
            rest = title[len(kw):].strip() if title.startswith(kw) else ""
            if rest and rest.split()[0] in ("아무리", "정말", "괜히", "자꾸"):
                print(f"   ! 키워드 뒤가 서술어로 시작합니다 — {title}")

        for ty, tx in titles:
            problems = []
            if not tx.startswith(kw):
                problems.append("키워드가 맨 앞에 없음")
            if tx.count(kw) != 1:
                problems.append(f"키워드 {tx.count(kw)}회 (1회여야 함)")
            if not MIN_LEN <= len(tx) <= MAX_LEN:
                problems.append(f"{len(tx)}자 ({MIN_LEN}~{MAX_LEN}자 권장)")
            if BANNED.search(tx):
                problems.append("특수문자·이모지")
            mark = "✓" if not problems else "✗"
            print(f"   {mark} {ty} {len(tx):>2}자  {tx}")
            if problems:
                print(f"        └ {' / '.join(problems)}")
                failed += 1

    print("\n" + ("=> 전체 통과." if not failed else f"=> 수정 필요 {failed}건."))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
