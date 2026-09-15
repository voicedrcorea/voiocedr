# 닥터브레스 랜딩 페이지

블로그 자동화와는 별개로, `drbreath.liveklass.com` 상담 유입용
랜딩 페이지(DR.Breath)의 원본과 작업 도구를 보관한다.

## 파일

| 파일 | 설명 |
|---|---|
| `drbreath-landing.html` | 랜딩 페이지 전체 (이미지 base64 포함 단일 파일) |
| `section-program-flow.html` | "닥터브레스 프로그램은?" 섹션만 떼어낸 조각 |
| `inline_images.py` | `images/` 의 사진을 HTML 본문에 base64로 박아 넣는 스크립트 |
| `images/` | 끼워 넣을 사진을 두는 폴더 (사진 자체는 커밋하지 않는다) |

## 프로그램 소개 섹션

후기 섹션(`#review`) 아래, 가격 섹션(`#pricing`) 위에 들어간다.
세로 타임라인 3단계 구성이다.

1. 상담 신청 후 검사지 작성 + 호흡 영상 셀카 촬영 → 담당 트레이너 전달
2. 담당 트레이너가 진단 후 프로그램 배치
3. 2주 간격(스케줄에 따라 12~17일) 재진단 후 프로그램 재배치

기존 페이지 스타일을 그대로 따른다.
브랜드 컬러 번호 배지, `accent-500` + `shadow-cta` CTA, `rounded-2xl` 카드,
`break-keep`, 섹션 상단 영문 라벨(`PROCESS`).

위 후기 섹션이 `bg-slate-50`, 아래 가격 섹션이 `bg-white` 라서
그 사이는 연한 브랜드 그라데이션으로 두 흰 섹션이 붙어 보이지 않게 했다.

## 사진 넣는 법

사진은 저장소에 커밋하지 않는다. 용량이 크고, 인물 사진이다.

`landing/images/` 에 아래 이름으로 넣는다.

```
selfie-1.jpg    셀카 (전신 사진)
selfie-2.jpg    셀카2 (검사지 작성)
program-1.jpg   영상1 (경추 움직임 호흡)
program-2.jpg   영상2 (천천히 호흡을 빼겠습니다)
program-3.jpg   영상3 (앉은 자세, 다섯)
program-4.jpg   영상4 (누운 자세, 옆구리)
```

확장자가 `.png` 여도 이름만 맞으면 찾아간다.

```
python3 landing/inline_images.py landing/drbreath-landing.html
```

`drbreath-landing.inlined.html` 이 만들어진다.
이 파일 하나에 사진까지 전부 들어 있으므로 그대로 배포하면 된다.
빠진 사진은 자리표시자로 남고, 어떤 파일을 못 찾았는지 알려준다.

## 아직 정리되지 않은 것

- 셀카 2장은 세로/가로로 비율이 달라서 정사각 박스에 `object-contain` 으로
  넣어 뒀다. 여백 없이 채우려면 `object-cover` 로 바꾸면 되지만 상하좌우가 잘린다
- 이 환경은 `cdn.tailwindcss.com` 이 조직 네트워크 정책으로 차단되어 있어
  (CONNECT 403) 브라우저 렌더 검증을 하지 못했다. 클래스 계산과 태그 균형만
  확인했다. 화면 확인은 사람이 직접 열어봐야 한다
