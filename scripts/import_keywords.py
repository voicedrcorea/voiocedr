#!/usr/bin/env python3
"""네이버 검색광고 키워드도구 파일을 읽어 keywords/queue.tsv 를 재구성한다.

내려받는 법
  searchad.naver.com → 로그인 → 도구 → 키워드 도구
  → 씨앗 키워드 입력 → 조회 → 우측 상단 [다운로드]
  **xlsx 그대로 넣으셔도 됩니다.** CSV 로 다시 저장하실 필요 없습니다.
  여러 번 조회해서 받은 파일을 한 번에 넣으셔도 됩니다.

사용
    python3 scripts/import_keywords.py keywords/raw/*.xlsx
    python3 scripts/import_keywords.py <파일…> --min-volume 300 --dry-run
    python3 scripts/import_keywords.py <파일…> --max-volume 8000

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

# 가드레일상 비의료 사업자가 가져갈 수 없는 검색 의도. 조용히 버린다
EXCLUDE = re.compile(
    r"(치료|병원|이비인후과|수술|약|영양제|성형|보험|무료|공짜|자격증|알바|채용|중고)"
)

# 의료 진단명. 버리지는 않되 사장님 판단이 필요하므로 hold 로 남긴다
MEDICAL = re.compile(r"(성대결절|성대폴립|후두염|역류성|성대마비|발성장애|언어장애)")

# 키워드도구는 씨앗과 무관한 초대형 키워드를 끼워 넣는다 (`유튜브` 2,500만 등).
# 관련성은 두 단계로 본다.
#
# 목소리 단어가 들어 있으면 통과다. 직업명만 있는 것은 통과가 아니다 —
# `아나운서연봉` `강사모집` 은 직업 정보를 찾는 검색이지 목소리 고민이 아니다.
# 직업명은 학원·레슨·오디션 같은 말과 붙었을 때만 우리 독자가 된다.
VOICE = re.compile(
    r"(목소리|발성|발음|호흡|복식|스피치|보이스|성대|음성|딕션|억양|사투리|공명|"
    r"낭독|대사|웅변|말하기|말투|톤|비음|콧소리|떨림|목쉼|성량|딸림)"
)
CAREER = re.compile(
    r"(아나운서|성우|배우|연기|가수|뮤지컬|국악|유튜버|쇼호스트|쇼핑호스트|승무원|"
    r"강사|강연|교사|상담사|변호사|세무사|직장인|영업)"
)
CAREER_OK = re.compile(r"(학원|레슨|아카데미|수업|훈련|연습|되는법|되는 법|준비|오디션|면접|입시|과외)")

# 직업명·목소리 단어에 붙어 나오지만 우리 독자의 검색이 아닌 것들.
# AI 음성 합성 계열이 특히 많이 딸려 온다 — `AI목소리만들기` 는
# 목소리를 바꾸려는 사람이 아니라 프로그램을 찾는 사람의 검색이다.
JUNK = re.compile(
    r"(연봉|월급|수입|모집|공고|전망|커트라인|등급컷|인강|사이트|순위|뜻|유래|나무위키"
    r"|AI|ai|인공지능|TTS|tts|합성|변조|더빙|어플|[Aa]pp|프로그램|다운로드|사이트|무료)"
)


def relevant(kw):
    if JUNK.search(kw):
        return False
    if VOICE.search(kw):
        return True
    return bool(CAREER.search(kw) and CAREER_OK.search(kw))


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
        clean = str(h).replace(" ", "")
        for c in candidates:
            if c.replace(" ", "") in clean:
                return i
    return None


def find_header(rows):
    """헤더 줄과 데이터 시작 줄을 찾는다.

    키워드도구가 실제로 내려주는 파일은 헤더가 **두 줄**이다.

        0: 연관키워드 | 월간검색수       |            | 월평균클릭수 | …
        1:            | 월간검색수(PC)  | 월간검색수(모바일) | …

    엑셀에서 병합된 셀이라 한 줄만 보면 어느 쪽에도 필요한 열이 다 없다.
    그래서 한 줄로 안 되면 **다음 줄을 겹쳐 읽는다.**
    맨 위에 "키워드 도구 조회결과" 같은 안내 줄이 붙어 나오는 판본도 있어서,
    키워드 열만 보고 고르면 안내 줄을 헤더로 잡아버린다.
    검색량 열까지 같이 잡히는 조합이라야 진짜 헤더다.
    """
    for i, r in enumerate(rows):
        if pick(r, COL_KEYWORD) is None:
            continue
        if pick(r, COL_PC) is not None or pick(r, COL_MO) is not None:
            return r, i + 1
        if i + 1 < len(rows):
            nxt = rows[i + 1]
            merged = [f"{a} {b}".strip() for a, b in
                      zip(r + [""] * len(nxt), nxt + [""] * len(r))]
            if pick(merged, COL_PC) is not None or pick(merged, COL_MO) is not None:
                return merged, i + 2
    return None, 0


def to_int(v):
    """'< 10' 이나 '1,234' 같은 표기를 숫자로."""
    s = str(v).strip().replace(",", "")
    if s.startswith("<"):
        return 5
    m = re.search(r"\d+", s)
    return int(m.group()) if m else 0


def classify(kw):
    """걸리는 축을 전부 돌려준다.

    한 키워드가 여러 슬롯 후보가 되는 것이 정상이다
    (`아나운서발음연습` 은 직업군이면서 발음이면서 방법이다).
    슬롯을 하나만 붙여두면 스킬이 다섯 편을 갈라 배치할 수 없다.
    표기는 analyze_inflow.py 와 같은 `·` 구분으로 맞춘다.
    """
    hits = [name for name, pat in INTENT if re.search(pat, kw)]
    return "·".join(hits) if hits else "일반"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src_paths", nargs="+",
                    help="키워드도구에서 받은 csv 또는 xlsx (여러 개 가능)")
    ap.add_argument("--min-volume", type=int, default=200,
                    help="월간 총검색량 하한 (기본 200)")
    ap.add_argument("--max-volume", type=int, default=0,
                    help="경쟁도 상한선. 0이면 적용하지 않는다 (POLICY 7번)")
    ap.add_argument("--max-keywords", type=int, default=300)
    ap.add_argument("--dry-run", action="store_true", help="파일을 쓰지 않고 결과만 본다")
    args = ap.parse_args()

    seen, out, over, medical = {}, [], [], []
    dropped = {"중복": 0, "제외어": 0, "무관": 0, "검색량미달": 0,
               "상한초과": 0, "의료의도": 0}
    total_rows = 0

    for sp in args.src_paths:
        rows = read_rows(sp)
        header, start = find_header(rows)
        if header is None:
            sys.exit(f"{sp}: 연관키워드·월간검색수 열을 찾지 못했습니다.\n"
                     "키워드도구에서 [다운로드] 로 받은 파일이 맞는지 확인해 주세요.")
        ik, ipc, imo, ic = (pick(header, c)
                            for c in (COL_KEYWORD, COL_PC, COL_MO, COL_COMP))
        for r in rows[start:]:
            if not r or ik is None or ik >= len(r):
                continue
            kw = str(r[ik]).strip()
            if not kw:
                continue
            total_rows += 1
            if kw in seen:
                dropped["중복"] += 1
                continue
            seen[kw] = True
            if EXCLUDE.search(kw):
                dropped["제외어"] += 1
                continue
            if not relevant(kw):
                dropped["무관"] += 1
                continue
            vol = (to_int(r[ipc]) if ipc is not None and ipc < len(r) else 0) \
                + (to_int(r[imo]) if imo is not None and imo < len(r) else 0)
            comp = str(r[ic]).strip() if ic is not None and ic < len(r) else ""
            rec = (kw, vol, comp, classify(kw))
            if MEDICAL.search(kw):
                # 의료 진단명은 버리지 않는다. 가져갈지는 사장님이 정하실 일이다
                dropped["의료의도"] += 1
                medical.append(rec)
                continue
            if vol < args.min_volume:
                dropped["검색량미달"] += 1
                continue
            if args.max_volume and vol > args.max_volume:
                # 버리지 않는다. 지수가 오르면 풀 것이므로 hold 로 남긴다
                dropped["상한초과"] += 1
                over.append(rec)
                continue
            out.append(rec)

    # 검색량 높은 순, 같으면 경쟁 낮은 순
    order = {"낮음": 0, "중간": 1, "높음": 2}
    out.sort(key=lambda x: (-x[1], order.get(x[2], 1)))
    out = out[:args.max_keywords]
    over.sort(key=lambda x: -x[1])
    medical.sort(key=lambda x: -x[1])

    # 이미 쓴 키워드는 used.tsv 가 원본이다. 큐를 다시 만들어도 이력은 남겨야
    # 다음 실행이 같은 키워드를 또 고르지 않는다
    used, used_rows = set(), []
    used_path = os.path.join(ROOT, "keywords", "used.tsv")
    if os.path.exists(used_path):
        for line in open(used_path, encoding="utf-8").read().splitlines()[1:]:
            c = line.split("\t")
            if len(c) > 1 and c[1].strip():
                used.add(c[1].strip())
                used_rows.append((c[0].strip(), c[1].strip()))

    print(f"파일 {len(args.src_paths)}개 / 읽은 행 {total_rows}  →  채택 {len(out)}")
    print("  제외: " + " / ".join(f"{k} {v}" for k, v in dropped.items()))
    print(f"\n{'키워드':<24}{'월검색량':>9}  {'경쟁':<5}{'의도':<6}상태")
    print("-" * 62)
    lines = ["date\tkeyword\taxis\tvolume\tstatus\tnote"]
    for date, kw in used_rows:
        lines.append(f"{date}\t{kw}\t{classify(kw)}\t\tin_use\t사용됨")
    for kw, vol, comp, intent in out:
        if kw in used:
            continue
        lines.append(f"\t{kw}\t{intent}\t{vol}\tready\t경쟁 {comp}")
        if len(lines) <= 41:
            print(f"{kw:<24}{vol:>9,}  {comp:<5}{intent}")
    if len(out) > 40:
        print(f"… 외 {len(out)-40}개")

    for kw, vol, comp, intent in over:
        lines.append(f"\t{kw}\t{intent}\t{vol}\thold\t상한 초과 — 지수 오르면 해제")
    for kw, vol, comp, intent in medical:
        lines.append(f"\t{kw}\t{intent}\t{vol}\thold\t의료 진단명 — 사장님 판단 필요")

    if over:
        print(f"\n상한({args.max_volume:,}) 초과 {len(over)}개는 hold 로 남겼습니다 "
              f"— 지수가 오르면 풉니다")
        for kw, vol, comp, intent in over[:10]:
            print(f"  {kw:<24}{vol:>9,}  {comp}")
    if medical:
        print(f"\n의료 진단명 {len(medical)}개도 hold 입니다 — 가져갈지는 사장님이 정하십니다")
        for kw, vol, comp, intent in medical[:10]:
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
    ready = sum(1 for l in lines[1:] if "\tready\t" in l)
    print(f"\nkeywords/queue.tsv 재구성 완료 — ready {ready}개")
    if ready < 10:
        print(f"주의: 하루 5편 = 주 10편입니다. ready {ready}개면 1주도 못 버팁니다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
