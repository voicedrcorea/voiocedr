#!/usr/bin/env python3
"""후보 표현을 네이버 검색량으로 검증한다.

왜 필요한가.

사장님 말씀대로 구글에서 자주 검색되는 말은 네이버에서도 쓰일 가능성이 높다.
같은 고민을 하는 사람이 쓰는 말은 검색 엔진마다 크게 다르지 않기 때문이다.
그래서 구글 쪽 표현을 후보로 긁어오는 것은 맞는 방향이다.

다만 거기서 멈추면 안 된다. **구글 검색량을 네이버 검색량으로 쓸 수는 없다.**
그건 근거 없는 수치다. 그래서 두 단계로 나눈다.

    1단계 발굴 — 구글 웹검색으로 같은 의도의 표현을 모은다.
                 여기서 나온 것은 후보일 뿐이고 큐에 들어가지 못한다.
    2단계 검증 — 이 스크립트로 `keywords/raw/` 의 네이버 검색량을 찾는다.
                 수치가 나오면 큐로, 안 나오면 `hold` 로 간다.

이렇게 하면 구글은 후보를 넓히는 역할만 하고, 큐에 들어가는 근거는
끝까지 네이버 실측값으로 남는다. POLICY.md 1번이 지켜진다.

사용
    python3 scripts/lookup_volume.py 발음좋아지는방법 목소리커지는법
    echo "후보를 줄마다" | python3 scripts/lookup_volume.py -
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_keywords as ik   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build_index():
    """keywords/raw/ 의 모든 키워드도구 파일을 하나의 검색량 사전으로."""
    vol = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "keywords", "raw", "*.xls*"))) + \
            sorted(glob.glob(os.path.join(ROOT, "keywords", "raw", "*.csv"))):
        rows = ik.read_rows(p)
        header, start = ik.find_header(rows)
        if header is None:
            continue
        ci, pc, mo, cp = (ik.pick(header, c) for c in
                          (ik.COL_KEYWORD, ik.COL_PC, ik.COL_MO, ik.COL_COMP))
        for r in rows[start:]:
            if not r or ci is None or ci >= len(r):
                continue
            k = str(r[ci]).strip()
            if not k:
                continue
            v = (ik.to_int(r[pc]) if pc is not None and pc < len(r) else 0) \
                + (ik.to_int(r[mo]) if mo is not None and mo < len(r) else 0)
            c = str(r[cp]).strip() if cp is not None and cp < len(r) else ""
            vol[k] = (v, c)
    return vol


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    if args == ["-"]:
        args = [l.strip() for l in sys.stdin if l.strip()]

    vol = build_index()
    if not vol:
        sys.exit("keywords/raw/ 에 키워드도구 파일이 없습니다.")
    # 띄어쓰기는 검색어마다 제각각이라 붙여 쓴 형태로도 한 번 더 찾는다
    flat = {k.replace(" ", ""): (k, v) for k, v in vol.items()}

    print(f"검색량 사전 {len(vol):,}개 기준\n")
    print(f"{'후보':<24}{'월검색량':>9}  {'경쟁':<5}판정")
    print("-" * 62)
    ok = miss = 0
    for q in args:
        hit = vol.get(q) or (flat.get(q.replace(" ", "")) or (None, None))[1]
        if hit:
            v, c = hit
            verdict = "큐 후보" if v >= 30 else "검색량 미달"
            print(f"{q:<24}{v:>9,}  {c:<5}{verdict}")
            ok += 1
        else:
            print(f"{q:<24}{'—':>9}  {'':<5}사전에 없음 — hold")
            miss += 1

    print(f"\n확인 {ok}개 / 사전에 없음 {miss}개")
    if miss:
        print("사전에 없는 것은 검색량이 너무 낮거나 씨앗의 연관 목록 밖입니다.")
        print("그 표현을 씨앗에 넣고 키워드도구를 다시 조회하면 확인됩니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
