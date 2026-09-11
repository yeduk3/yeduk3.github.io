# yeduk3.github.io

개인 사이트 — 선정한 프로젝트 / CV / 아티클 퍼블리싱. 정적, GitHub Pages.
로컬 빌더(`tools/build.py`)로 공통 크롬과 목록을 생성하고, 산출물인 HTML을 커밋한다.

## 시각 변경 전 필독

**`DESIGN.md`를 먼저 읽는다.** Symplex 디자인 시스템(Claude Design `Vellum design system`)을 따르며,
새 색·이징·반경·폰트를 만들지 않는다. `static/css/symplex.css`는 직접 수정하지 않는다.

## 구조

정적 4페이지. 디렉터리 + `index.html`로 깔끔한 URL을 만든다 (`/about/` → `about/index.html`).

| 경로 | 파일 | 내용 |
|---|---|---|
| `/` | `index.html` | 히어로(자기소개) · 요약 스트립 · BVH 인스펙터 · 최근 글 3 · 최근 작업 3 |
| `/about/` | `about/index.html` | 이력 타임라인 · CV 다운로드 · SNS/GitHub 링크(반전 밴드) |
| `/notes/` | `notes/index.html` | 글 목록 |
| `/work/` | `work/index.html` | 작업물 목록 — 프리뷰 이미지 + 타이틀 블록 반복 |

- `static/css/symplex.css` — 디자인 시스템(토큰 + base + `.sx-*`). **직접 수정 금지**
- `style.css` — 페이지 레이아웃
- `static/js/bvh.js` — BVH 인스펙터. `#bvh` 하나만 잡으므로 페이지당 1개
- `tools/build.py` — 정적 페이지 빌더
- `posts/*.md` — 글. frontmatter가 있는 것만 목록에 뜬다. 작성법은 `posts/_README.md`
- `projects/*.md` — 작업물. 동일. 작성법은 `projects/_README.md`
- `archived-post/` — 개인 보관용. **`.gitignore` 처리되어 커밋되지 않고, 빌더도 읽지 않는다**
- `main/post.html` — 옛 아티클 렌더링. 글 상세 페이지 구조 결정 대기
- `tests/` — 과거 실험. 정리 대상
- `design/` — 시안 후보군 A~H. `.gitignore` 처리, 커밋하지 않음

## 빌드

```bash
python3 tools/build.py          # 마커 영역 재생성
python3 tools/build.py --check  # 파일을 쓰지 않고 최신인지만 검사
```

**배포는 여전히 정적이다.** 빌더는 로컬에서 HTML을 생성할 뿐이고 GitHub Pages는 생성된 파일을 그대로 서빙한다.
런타임 JS로 목록을 그리지 않는 이유는 AI 크롤러 상당수가 JS를 실행하지 않아 SEO/AEO가 깨지기 때문이다.

빌더는 `<!-- build:NAME -->` … `<!-- /build:NAME -->` **사이만** 덮어쓴다. 그 바깥은 손으로 자유롭게 편집해도 된다.

| 마커 | 위치 | 내용 |
|---|---|---|
| `build:nav active=<키>` | 4개 페이지 | 공통 nav. 활성 항목만 다름 |
| `build:footer` | 4개 페이지 | 공통 footer. 4곳이 완전히 동일 |
| `build:notes limit=3` | `/` | `posts/*.md` 최신 3 |
| `build:notes` | `/notes/` | 전체 |
| `build:work limit=3` | `/` | `projects/*.md` 상위 3 |
| `build:work` | `/work/` | 전체 |

nav·footer·목록을 고칠 때는 **HTML이 아니라 `tools/build.py`와 `posts/`·`projects/`를 고치고 빌드**한다.

### frontmatter

```yaml
---
title: 제목            # 필수. 없으면 목록에서 제외된다
date: 2026.09          # 글 정렬 기준
tag: Simulation        # 글 배지
syndication: dev.to    # 선택. 쉼표로 여러 개
slug: custom-slug      # 선택. 기본값은 파일명
draft: true            # 선택. 목록에서 제외
---
```

`_`로 시작하는 파일(`_README.md`)은 빌더가 콘텐츠로 읽지 않는다.

작업물은 `status`, `tags`, `summary`, `order`, `preview`(이미지 경로)를 쓴다.
읽기 시간은 본문 글자 수 ÷ 700(한국어 평균 독서 속도 **추정치**)으로 계산한다 — 실측이 아니다.

항목이 하나도 없으면 목록 자리에 "Working on it" 빈 상태 카드가 들어간다. 가짜 항목으로 채우지 않는다.

## 사실 취급

수치·연도를 지어내지 않는다. 실측하지 않은 값은 `20XX` `0 min`처럼 플레이스홀더로 두거나 슬롯 자체를 만들지 않는다.
BVH readout(`overlap`, `Σarea`)만 실제 계산값이다.
