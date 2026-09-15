#!/usr/bin/env python3
"""
닥터브레스 페이지의 이미지 자리(images/*.jpg)에 실제 사진을 끼워 넣는 스크립트.

이 페이지는 모든 이미지를 base64로 품고 있는 단일 HTML 파일이라,
새로 넣는 사진도 같은 방식으로 본문에 박아 넣어야 파일 하나로 배포됩니다.

사용법
-----
1) HTML 파일 옆에 images 폴더를 만들고 아래 이름으로 사진을 넣습니다.

   images/selfie-1.jpg   <- 셀카 (전신 사진)
   images/selfie-2.jpg   <- 셀카2 (검사지 작성)
   images/program-1.jpg  <- 영상1 (경추 움직임 호흡)
   images/program-2.jpg  <- 영상2 (천천히 호흡을 빼겠습니다)
   images/program-3.jpg  <- 영상3 (앉은 자세, 다섯)
   images/program-4.jpg  <- 영상4 (누운 자세, 옆구리)

   png 파일이면 확장자를 .png 로 두면 됩니다. 이름만 맞으면 됩니다.

2) 실행

   python3 inline_images.py drbreath-9.15-program-added.html

3) drbreath-9.15-program-added.inlined.html 이 만들어집니다.
   이 파일 하나만 있으면 이미지까지 전부 들어 있습니다.
"""
import base64
import re
import sys
from pathlib import Path

MIME = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif",
}


def main() -> int:
    if len(sys.argv) != 2:
        print("사용법: python3 inline_images.py <html파일>", file=sys.stderr)
        return 2

    html_path = Path(sys.argv[1]).resolve()
    if not html_path.is_file():
        print(f"파일을 찾을 수 없습니다: {html_path}", file=sys.stderr)
        return 1

    base_dir = html_path.parent
    html = html_path.read_text(encoding="utf-8")

    replaced, missing = [], []

    def resolve(ref: str) -> Path | None:
        """images/program-1.jpg 처럼 적힌 경로를 실제 파일로 찾는다.
        확장자가 달라도(.png 등) 같은 이름이면 찾아준다."""
        direct = base_dir / ref
        if direct.is_file():
            return direct
        stem_dir = direct.parent
        if stem_dir.is_dir():
            for cand in sorted(stem_dir.iterdir()):
                if cand.is_file() and cand.stem == direct.stem and cand.suffix.lower() in MIME:
                    return cand
        return None

    def sub(match: re.Match) -> str:
        ref = match.group(1)
        found = resolve(ref)
        if found is None:
            missing.append(ref)
            return match.group(0)
        mime = MIME.get(found.suffix.lower())
        if mime is None:
            missing.append(ref)
            return match.group(0)
        data = base64.b64encode(found.read_bytes()).decode("ascii")
        replaced.append((ref, found.name, found.stat().st_size))
        return f'src="data:{mime};base64,{data}"'

    # src="images/..." 형태만 바꾼다. 이미 base64인 기존 이미지는 건드리지 않는다.
    out = re.sub(r'src="(images/[^"]+)"', sub, html)

    if not replaced and not missing:
        print("바꿀 이미지 자리가 없습니다. 이미 적용된 파일일 수 있습니다.")
        return 0

    out_path = html_path.with_suffix(".inlined.html")
    out_path.write_text(out, encoding="utf-8")

    for ref, name, size in replaced:
        print(f"  넣음   {ref:24} <- {name} ({size/1024:.0f} KB)")
    for ref in missing:
        print(f"  못찾음 {ref:24} (자리표시자로 남습니다)")

    print(f"\n완료: {out_path}")
    print(f"크기: {out_path.stat().st_size/1024/1024:.2f} MB")
    if missing:
        print(f"\n{len(missing)}개는 파일을 못 찾아 그대로 뒀습니다. "
              f"images 폴더의 파일 이름을 확인해 주세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
