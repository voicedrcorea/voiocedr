#!/usr/bin/env python3
"""네이버 검색광고 키워드도구 CSV를 읽어 keywords/queue.tsv 를 재구성한다.

내려받는 법
  searchad.naver.com → 로그인 → 도구 → 키워드 도구
  → 씨앗 키워드 입력 → 조회 → 우측 상단 [다운로드]
  → 받은 파일이 xlsx면 엑셀에서 "CSV UTF-8"로 다시 저장

사용
    python3 scripts/import_keywords.py keywords/raw/키워드도구.csv
    python3 scripts/import_keywords.py <파일> --min-volume 300 --dry-run
"""
import argparse
import csv
import os
import re
import sys

# 키워드도구 헤더는 버전에 따라 조금씩 달라서 부분 일치로 찾는다
COL_KEYWORD = ("연관키워드", "키워드")
COL_PC = ("월간검색수(PC)", "월간검색수PC", "PC검색량")
COL_MO = ("월간검색수(모바일)", "월간검색수모바일", "모바일검색량")
COL_COMP = ("경쟁정도", "경쟁강도")

# 의도 분류 — 실제 검색어 형태를 그대로 두고 분류만 한다
INTENT = [
    ("비용",   r"(비용|가격|얼마|요금|수강료|기간|학원비)"),
    ("직업군", r"(성우|아나운서|가수|배우|강사|교사|유튜버|쇼호스트|상담사|영업|스피치|연기|뮤지컬)"),
    ("증상",   r"(떨림|떨려|쉬어|쉰|갈라|아파|아픈|통증|작아|가늘|콧소리|새|꼬여|잠기|답답|피로|울렁)"),
    ("방법",   r"(법|방법|연습|훈련|하는|어떻게|순서|팁)"),
]

# 절대 쓰지 않을 키워드 — 가드레일과 브랜드 성격상 부적합
EXCLUDE = re.compile(
    r"(치료|병원|이비인후과|수술|약|영양제|성형|보험|무료|공짜|자격증|알바|채용|중고)"
)


def pick(header, candidates):
    for i, h in enumerate(header):
        clean = h.replace(" ", "")
        for c in candidates:
            if c.replace(" ", "") in clean:
                return i
    return None


def to_int(v):
    """'< 10' 이나 '1,234' 같은 표기를 숫자로."""
    s = str(v).strip().replace(",", "")
    if s.startswith("<"):
        return 5
    m = re.search(r"\d+", s)
    return int(m.group()) if m else 0


def classify(kw):
    for name, pat in INTENT:
        if re.search(pat, kw):
            return name
    return "일반"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--min-volume", type=int, default=200,
                    help="월간 총검색량 하한 (기본 200)")
    ap.add_argument("--max-keywords", type=int, default=200)
    ap.add_argument("--dry-run", action="store_true", help="파일을 쓰지 않고 결과만 본다")
    args = ap.parse_args()

    rows = list(csv.reader(open(args.csv_path, encoding="utf-8-sig")))
    # 헤더 줄 찾기 (키워드도구는 위에 안내 줄이 붙어 나올 때가 있다)
    hi = next((i for i, r in enumerate(rows) if pick(r, COL_KEYWORD) is not None), None)
    if hi is None:
        sys.exit("연관키워드 열을 찾지 못했습니다. CSV UTF-8 로 저장했는지 확인해 주세요.")
    header = rows[hi]
    ik, ipc, imo, ic = (pick(header, c) for c in (COL_KEYWORD, COL_PC, COL_MO, COL_COMP))
    if ipc is None and imo is None:
        sys.exit("월간검색수 열을 찾지 못했습니다.")

    seen, out, dropped = set(), [], {"중복": 0, "제외어": 0, "검색량미달": 0}
    for r in rows[hi + 1:]:
        if not r or ik >= len(r):
            continue
        kw = r[ik].strip()
        if not kw:
            continue
        if kw in seen:
            dropped["중복"] += 1
            continue
        seen.add(kw)
        if EXCLUDE.search(kw):
            dropped["제외어"] += 1
            continue
        vol = (to_int(r[ipc]) if ipc is not None and ipc < len(r) else 0) \
            + (to_int(r[imo]) if imo is not None and imo < len(r) else 0)
        if vol < args.min_volume:
            dropped["검색량미달"] += 1
            continue
        comp = r[ic].strip() if ic is not None and ic < len(r) else ""
        out.append((kw, vol, comp, classify(kw)))

    # 검색량 높은 순, 같으면 경쟁 낮은 순
    order = {"낮음": 0, "중간": 1, "높음": 2}
    out.sort(key=lambda x: (-x[1], order.get(x[2], 1)))
    out = out[:args.max_keywords]

    used = set()
    if os.path.exists("keywords/used.tsv"):
        for line in open("keywords/used.tsv", encoding="utf-8").read().splitlines()[1:]:
            p = line.split("\t")
            if len(p) > 1:
                used.add(p[1])

    print(f"읽은 행 {len(rows)-hi-1}  →  채택 {len(out)}")
    print("  제외: " + " / ".join(f"{k} {v}" for k, v in dropped.items()))
    print(f"\n{'키워드':<24}{'월검색량':>9}  {'경쟁':<5}{'의도':<6}상태")
    print("-" * 62)
    lines = ["date\tkeyword\tintent\tvolume\tcompetition\tstatus"]
    for kw, vol, comp, intent in out:
        st = "in_use" if kw in used else "ready"
        date = "2026-사용됨" if kw in used else ""
        lines.append(f"{date}\t{kw}\t{intent}\t{vol}\t{comp}\t{st}")
        if len(lines) <= 41:
            print(f"{kw:<24}{vol:>9,}  {comp:<5}{intent:<6}{st}")
    if len(out) > 40:
        print(f"… 외 {len(out)-40}개")

    if args.dry_run:
        print("\n(--dry-run: 파일을 쓰지 않았습니다)")
        return 0
    os.replace(args.csv_path, args.csv_path)  # no-op, 원본 보존 확인용
    open("keywords/queue.tsv", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"\nkeywords/queue.tsv 재구성 완료 — ready {sum(1 for l in lines[1:] if l.endswith('ready'))}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
