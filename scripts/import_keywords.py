#!/usr/bin/env python3
"""네이버 검색광고 키워드도구 파일을 읽어 keywords/queue.tsv 를 재구성한다.

내려받는 법
  searchad.naver.com → 로그인 → 도구 → 키워드 도구
  → 씨앗 키워드 입력 → 조회 → 우측 상단 [다운로드]
  **xlsx 그대로 넣으셔도 됩니다.** CSV 로 다시 저장하실 필요 없습니다.

사용
    python3 scripts/import_keywords.py keywords/raw/키워드도구.xlsx
    python3 scripts/import_keywords.py <파일> --min-volume 300 --dry-run
    python3 scripts/import_keywords.py <파일> --max-volume 8000

`--max-volume` 은 경쟁도 상한선이다. keywords/POLICY.md 7번을 보라.
블로그 지수로 환산하는 공식은 없으므로, 이미 유입이 난 키워드의
실측 검색량에서 상한을 잡는다. 기본값은 두지 않는다 — 근거 없이
숫자를 정하는 것이 이 정책이 막으려는 바로 그 일이다.
"""
import argparse
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 키워드도구 헤더는 버전에 따라 조금씩 달라서 부분 일치로 찾는다
COL_KEYWORD = ("연관키워드", "키워드")
COL_PC = ("월간검색수(PC)", "월간검색수PC", "PC검색량")
COL_MO = ("월간검색수(모바일)", "월간검색수모바일", "모바일검색량")
COL_COMP = ("경쟁정도", "경쟁강도")

# 의도 분류 — 실제 검색어 형태는 그대로 두고 분류만 한다.
# 이름은 POLICY.md 6번의 5개 슬롯과 맞춰 둔다. 위에서부터 먼저 걸리는 것을 쓴다.
INTENT = [
    ("탐색",   r"(학원|아카데미|레슨|수업|과외|추천|어디|소수정예|1:1|일대일"
               r"|비용|가격|얼마|요금|수강료|기간|학원비)"),
    ("직업군", r"(성우|아나운서|가수|배우|연기|강사|교사|유튜버|쇼호스트|쇼핑호스트"
               r"|상담사|영업|직장인|승무원|스피치|뮤지컬|국악|변호사|세무사|면접)"),
    ("발음",   r"(발음|딕션|대사|사투리|억양)"),
    ("증상",   r"(떨림|떨려|쉬어|쉰|갈라|아파|아픈|통증|작아|가늘|콧소리|새|꼬여"
               r"|잠기|답답|피로|울렁|불안|목상태)"),
    ("방법",   r"(법|방법|연습|훈련|교정|하는|어떻게|순서|팁|발성|호흡|복식)"),
]

# 절대 쓰지 않을 키워드 — 가드레일과 브랜드 성격상 부적합
EXCLUDE = re.compile(
    r"(치료|병원|이비인후과|수술|약|영양제|성형|보험|무료|공짜|자격증|알바|채용|중고)"
)


def read_rows(path):
    """csv 와 xlsx 를 같은 모양(문자열 2차원 배열)으로 돌려준다."""
    if path.lower().endswith((".xlsx", ".xlsm")):
        try:
            import openpyxl
        except ImportError:
            sys.exit("xlsx 를 읽으려면 openpyxl 이 필요합니다.  pip install openpyxl")
        wb = openpyxl.load_workbook(path, data_only=True)
        rows = [["" if c is None else str(c) for c in r]
                for r in wb.worksheets[0].iter_rows(values_only=True)]
        wb.close()
        return rows
    return list(csv.reader(open(path, encoding="utf-8-sig")))


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
    ap.add_argument("src_path", help="키워드도구에서 받은 csv 또는 xlsx")
    ap.add_argument("--min-volume", type=int, default=200,
                    help="월간 총검색량 하한 (기본 200)")
    ap.add_argument("--max-volume", type=int, default=0,
                    help="경쟁도 상한선. 0이면 적용하지 않는다 (POLICY 7번)")
    ap.add_argument("--max-keywords", type=int, default=200)
    ap.add_argument("--dry-run", action="store_true", help="파일을 쓰지 않고 결과만 본다")
    args = ap.parse_args()

    rows = read_rows(args.src_path)
    # 헤더 줄 찾기.
    # 키워드도구 파일은 맨 위에 "키워드 도구 조회결과" 같은 안내 줄이 붙어 나온다.
    # 그 줄에도 '키워드' 가 들어 있어서 키워드 열만 보고 고르면 안내 줄을 헤더로
    # 잡아버린다. **검색량 열까지 같이 있는 줄**이라야 진짜 헤더다.
    hi = next((i for i, r in enumerate(rows)
               if pick(r, COL_KEYWORD) is not None
               and (pick(r, COL_PC) is not None or pick(r, COL_MO) is not None)), None)
    if hi is None:
        sys.exit("연관키워드·월간검색수 열을 찾지 못했습니다.\n"
                 "키워드도구에서 [다운로드] 로 받은 파일이 맞는지 확인해 주세요.")
    header = rows[hi]
    ik, ipc, imo, ic = (pick(header, c) for c in (COL_KEYWORD, COL_PC, COL_MO, COL_COMP))

    seen, out, dropped = set(), [], {"중복": 0, "제외어": 0, "검색량미달": 0, "상한초과": 0}
    over = []   # 상한을 넘어 hold 로 남기는 것들
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
        if args.max_volume and vol > args.max_volume:
            # 버리지 않는다. 지수가 오르면 풀 것이므로 hold 로 남긴다
            dropped["상한초과"] += 1
            over.append((kw, vol, comp, classify(kw)))
            continue
        out.append((kw, vol, comp, classify(kw)))

    # 검색량 높은 순, 같으면 경쟁 낮은 순
    order = {"낮음": 0, "중간": 1, "높음": 2}
    out.sort(key=lambda x: (-x[1], order.get(x[2], 1)))
    out = out[:args.max_keywords]

    over.sort(key=lambda x: -x[1])

    used = set()
    used_path = os.path.join(ROOT, "keywords", "used.tsv")
    if os.path.exists(used_path):
        for line in open(used_path, encoding="utf-8").read().splitlines()[1:]:
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

    for kw, vol, comp, intent in over:
        lines.append(f"\t{kw}\t{intent}\t{vol}\t{comp}\thold")
    if over:
        print(f"\n상한({args.max_volume:,}) 초과 {len(over)}개는 hold 로 남겼습니다 "
              f"— 지수가 오르면 풉니다")
        for kw, vol, comp, intent in over[:10]:
            print(f"  {kw:<24}{vol:>9,}  {comp}")

    if args.dry_run:
        print("\n(--dry-run: 파일을 쓰지 않았습니다)")
        return 0

    # 쓰다 말고 죽으면 큐가 통째로 날아간다. tmp 에 쓰고 바꿔 끼운다
    dst = os.path.join(ROOT, "keywords", "queue.tsv")
    tmp = dst + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, dst)
    ready = sum(1 for l in lines[1:] if l.endswith("ready"))
    print(f"\nkeywords/queue.tsv 재구성 완료 — ready {ready}개")
    if ready < 10:
        print(f"주의: 하루 5편 = 주 10편입니다. ready {ready}개면 1주도 못 버팁니다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
