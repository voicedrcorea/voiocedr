#!/usr/bin/env python3
"""제목 후보 검증기 — 네이버 스마트블록 대응 규칙을 강제한다.

규칙 (brand/tone-and-manner.md E섹션)
  - 후보 6개, 유형이 모두 다를 것
  - 메인 키워드가 제목 맨 앞에 올 것
  - 메인 키워드가 제목 안에서 1회만 나올 것 (반복은 스터핑 감점)
  - 20~30자 (모바일 검색결과에서 잘리지 않게)
  - 특수문자·이모지 금지 (질문형의 '~일까요'는 허용)

사용:
    python3 scripts/check_titles.py drafts/2026-09-05/*.md
"""
import re
import sys

TYPES = ["원인형", "부정형", "방법형", "대상형", "증상형", "질문형"]
RESERVE = ["비교형"]  # 6개를 채우고 남을 때 쓰는 예비 유형
MIN_LEN, MAX_LEN = 20, 30
BANNED = re.compile(r"[!~★☆♥♡…※•▶◀▲▼✔✅🔥]|[\U0001F300-\U0001FAFF]")


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
