#!/usr/bin/env python3
"""네이버 블로그 통계 '유입분석' xlsx 를 읽어 키워드 축을 집계한다.

이 파일이 무엇인지 먼저 분명히 해둔다.
유입분석은 **이미 순위가 잡혀서 사람이 들어온** 검색어만 보여준다.
아직 못 잡은 키워드는 여기 없다. 그러니 신규 발굴 도구가 아니다.

대신 세 가지를 준다.

1. 실제 검색어의 형태  — 사람들이 실제로 친 글자 그대로다.
   `목소리커지는법` 처럼 붙여 쓰고, `아나운서 되는 법` 처럼 띄어 쓴다.
   제목 규칙에 맞추려고 명사구로 비틀면 그 검색어를 놓친다.
2. 이미 신뢰를 얻은 주제축 — C-Rank 는 주제 일관성을 본다.
   여러 달 연속 뜨는 축이 이 블로그가 이미 먹고 있는 땅이다.
3. **경쟁도의 실증 상한선** — 지수를 추정할 필요가 없다.
   이 키워드들에서 실제로 유입이 났다는 것이 곧
   "이 블로그 지수로 이 정도 경쟁도는 뚫린다"는 증거다.

한계도 같이 적는다. 상위 10개까지만 나오고 나머지는 `기타` 로 뭉뚱그려진다.
그 `기타` 가 매달 43~55% 다. 절반 이상이 안 보인다는 뜻이다.
비율만 있고 절대 방문수가 없어서 몇 명인지도 모른다.
"""

import argparse
import glob
import io
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl 이 없습니다.  pip install openpyxl")

RAW = os.path.join(ROOT, "keywords", "inflow", "raw")

# 씨앗 키워드에서 나온 축. 유입 키워드를 이 축에 붙여본다.
AXES = [
    ("직업군", r"(아나운서|성우|배우|연기|승무원|강사|교사|유튜버|쇼핑호스트|"
               r"상담사|영업|직장인|가수|뮤지컬|국악|변호사|세무사|면접)"),
    ("발음",   r"(발음|딕션|대사)"),
    ("발성",   r"(발성|호흡|복식)"),
    ("증상",   r"(떨림|갈라|쉬|잠기|불안|통증|피로|작은|가는|콧소리|목상태)"),
    ("탐색",   r"(학원|아카데미|레슨|수업|강의|과외|비용|가격|추천|어디|"
               r"소수정예|1:1|일대일)"),
    ("방법",   r"(법$|방법|연습|훈련|교정|하는법|되는법)"),
]


def axis_of(kw):
    """한 키워드가 여러 축에 걸리면 전부 돌려준다. 실제로 대부분 겹친다
    (`아나운서발음연습` 은 직업군이면서 발음이면서 방법이다)."""
    hits = [name for name, pat in AXES if re.search(pat, kw)]
    return hits or ["미분류"]


def load():
    months = {}
    for p in sorted(glob.glob(os.path.join(RAW, "*.xlsx"))):
        wb = openpyxl.load_workbook(p, data_only=True)
        ws = wb.worksheets[0]
        rows = list(ws.iter_rows(values_only=True))
        m = re.search(r"(\d{4})[.\-](\d{2})", str(rows[3][1]))
        month = f"{m.group(1)}-{m.group(2)}" if m else os.path.basename(p)
        items = []
        for r in rows[8:]:
            if r and r[0] and r[1] is not None:
                items.append((str(r[0]).strip(), float(r[1])))
        months[month] = items
        wb.close()
    return months


def emit_queue(seen, span):
    """유입 기록을 큐 행으로 바꾼다.

    여기서 한 가지를 구분한다.

    **꾸준히 뜨는 키워드는 이미 우리 글이 잡고 있다.** 거기에 새 글을 또 쓰면
    자기 글끼리 경쟁한다. 지키는 대상이지 새로 칠 대상이 아니다.

    **한 달 떴다가 사라진 키워드는 다르다.** 한 번 뚫었다는 것은 이 지수로
    닿는다는 뜻이고, 지금 없다는 것은 놓쳤다는 뜻이다. 사장님이 물으신
    *"기존 키워드 중 노출되지 못한 것"* 에 이 데이터가 닿는 가장 가까운 지점이다.
    """
    rows = []
    for kw, hits in sorted(seen.items(), key=lambda x: -max(p for _, p in x[1])):
        best = max(p for _, p in hits)
        n = len(hits)
        if n >= span:
            status, note = "defend", f"{n}/{span}개월 유지 — 이미 잡고 있다"
        elif n > 1:
            status, note = "defend", f"{n}/{span}개월 — 흔들리지만 잡고 있다"
        else:
            status, note = "ready", f"{hits[0][0]} 1회 노출 후 이탈 — 되찾는다"
        rows.append((kw, "·".join(axis_of(kw)), f"{best:.2f}", status, note))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit-queue", action="store_true",
                    help="keywords/queue.tsv 에 유입 근거 키워드를 병합한다")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    months = load()
    if not months:
        sys.exit(f"{RAW} 에 xlsx 가 없습니다.")

    seen = defaultdict(list)      # 키워드 -> [(월, 비율)]
    axis_share = defaultdict(float)
    axis_months = defaultdict(set)
    etc = {}

    for month, items in sorted(months.items()):
        for kw, pct in items:
            if kw == "기타":
                etc[month] = pct
                continue
            seen[kw].append((month, pct))
            for a in axis_of(kw):
                axis_share[a] += pct
                axis_months[a].add(month)

    span = len(months)
    print(f"# 유입 키워드 분석 — {span}개월 "
          f"({min(months)} ~ {max(months)})\n")

    print("## 이 데이터가 보여주지 않는 것\n")
    for m in sorted(etc):
        print(f"- {m}: 상위 10개 밖 `기타` 가 **{etc[m]}%**")
    avg = sum(etc.values()) / len(etc)
    print(f"\n전체 검색 유입의 평균 **{avg:.1f}%** 가 상위 10개 밖이다.")
    print("절반이 안 보인다. 이 표만으로 전체 유입 구조를 판단하면 안 된다.\n")

    print("## 여러 달 반복된 키워드 — 이 블로그가 이미 먹고 있는 땅\n")
    repeat = sorted(((k, v) for k, v in seen.items() if len(v) > 1),
                    key=lambda x: -len(x[1]))
    for kw, hits in repeat:
        ms = ", ".join(f"{m.split('-')[1]}월 {p}%" for m, p in hits)
        print(f"- **{kw}** — {len(hits)}개월 ({ms})")
    print()

    print("## 축별 비중 (중복 집계 — 한 키워드가 여러 축에 걸린다)\n")
    for a, s in sorted(axis_share.items(), key=lambda x: -x[1]):
        print(f"- {a}: 합계 {s:.1f}%p, {len(axis_months[a])}/{span}개월 등장")
    print()

    print("## 실제 검색어 형태 — 이대로 쓴다\n")
    print("붙여 쓴 것은 붙여 쓴 채로, 띄어 쓴 것은 띄어 쓴 채로 둔다.")
    print("제목 규칙을 맞추려고 명사구로 비틀면 그 검색어를 놓친다.\n")
    spaced = [k for k in seen if " " in k]
    glued = [k for k in seen if " " not in k]
    print(f"- 붙여 쓴 검색어 {len(glued)}개: {', '.join(sorted(glued)[:8])} …")
    print(f"- 띄어 쓴 검색어 {len(spaced)}개: {', '.join(sorted(spaced))}")
    print()

    print("## 경쟁도 실증 상한선 후보\n")
    print("아래 키워드들은 **실제로 유입이 발생했다**. 추정 지수가 아니라 결과다.")
    print("검색광고 키워드도구에서 이것들의 월간검색량을 뽑으면,")
    print("그 최대값이 이 블로그가 실제로 뚫어낸 경쟁도의 상한선이 된다.\n")
    print("```")
    for kw in sorted(seen):
        print(kw)
    print("```")

    if not args.emit_queue:
        return

    rows = emit_queue(seen, span)
    dst = os.path.join(ROOT, "keywords", "queue.tsv")

    # 기존 큐를 덮어쓰지 않는다. 이미 쓴 것은 이력이고,
    # 근거가 약해 보류해둔 것도 지우지 않는다. 지우면 왜 뺐는지가 사라진다
    keep, parked = [], []
    if os.path.exists(dst):
        for line in io.open(dst, encoding="utf-8").read().splitlines()[1:]:
            cols = line.split("\t")
            if not cols or len(cols) < 2 or not cols[1].strip():
                continue
            # 상태는 5번째 열이다. 맨 뒤를 보면 note 를 상태로 읽는다
            st = cols[4] if len(cols) > 4 else cols[-1]
            if st == "in_use":
                keep.append((cols[0], cols[1], cols[2] if len(cols) > 2 else "",
                             "", "in_use", "사용됨"))
            elif st == "ready" and len(cols) > 3 and cols[3].strip():
                # 검색량이 붙어 있으면 근거가 있는 것이다. 그대로 둔다
                keep.append((cols[0], cols[1], cols[2], cols[3], "ready",
                             cols[5] if len(cols) > 5 else ""))
            elif st in ("ready", "hold"):
                parked.append(("", cols[1], cols[2] if len(cols) > 2 else "",
                               "", "hold", cols[5] if len(cols) > 5
                               else "검색량 근거 없음 — 키워드도구 조회 대기"))
    used = {r[1] for r in keep} | {r[1] for r in parked}

    # defend 는 기존 행을 덮어써야 한다.
    # 검색량만 보고 들어온 ready 행이 알고 보니 이미 우리가 잡고 있는
    # 키워드라면, 그대로 두면 스킬이 그걸 골라 자기 글을 밀어낸다
    defend = {kw: note for kw, _, _, status, note in rows if status == "defend"}
    fixed = 0
    merged = []
    for r in keep:
        if r[1] in defend:
            merged.append((r[0], r[1], r[2], r[3], "defend", defend[r[1]]))
            fixed += 1
        else:
            merged.append(r)
    keep = merged

    out = ["date\tkeyword\taxis\tvolume\tstatus\tnote"]
    out += ["\t".join(r) for r in keep]
    added = 0
    for kw, axis, pct, status, note in rows:
        if kw in used:
            continue
        out.append(f"\t{kw}\t{axis}\t\t{status}\t{note} (유입 {pct}%)")
        added += 1

    out += ["\t".join(r) for r in parked]

    ready = sum(1 for l in out[1:] if "\tready\t" in l)
    used_n = sum(1 for r in keep if r[4] == "in_use")
    print(f"\n큐 병합: 기존 {len(keep)}행 유지(사용됨 {used_n}) "
          f"+ 유입 근거 {added}개 추가 + 근거없음 {len(parked)}개 hold 로 이월")
    print(f"검색량만 보고 ready 였던 {fixed}개를 defend 로 되돌렸습니다 "
          f"— 이미 잡고 있는 키워드입니다")
    print(f"ready {ready}개 — 하루 5편 기준 {ready/10:.1f}주분")
    if args.dry_run:
        print("(--dry-run: 파일을 쓰지 않았습니다)")
        return
    tmp = dst + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    os.replace(tmp, dst)
    print(f"{dst} 갱신 완료")


if __name__ == "__main__":
    main()
