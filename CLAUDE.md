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
| `/` | `index.html` | 히어로(자기소개) · 요약 스트립 · 최근 글 3 · 최근 작업 3 · BVH 인스펙터 |
| `/about/` | `about/index.html` | 이력 타임라인 · CV 다운로드 · SNS/GitHub 링크(반전 밴드) |
| `/articles/` | `articles/index.html` | 글 목록 |
| `/projects/` | `projects/index.html` | 작업물 목록 — 프리뷰 이미지 + 타이틀 블록 반복 |

- `static/css/symplex.css` — 디자인 시스템(토큰 + base + `.sx-*`). **직접 수정 금지**
- `style.css` — 페이지 레이아웃
- `static/js/bvh.js` — BVH 인스펙터. `#bvh` 하나만 잡으므로 페이지당 1개
- `tools/build.py` — 정적 페이지 빌더. 상세 페이지 렌더에 `markdown` 패키지 필요
  (없으면 목록만 갱신하고 경고). 배포에는 영향 없음 — 결과 HTML만 올라간다
- `articles-md/*.md` — **글 원고.** frontmatter가 있는 것만 목록에 뜬다. 작성법은 `articles-md/_README.md`
- `projects-md/*.md` — **작업물 원고.** 동일. 작성법은 `projects-md/_README.md`
- `archived-post/` — 개인 보관용. **`.gitignore` 처리되어 커밋되지 않고, 빌더도 읽지 않는다**
- `main/post.html` — 옛 아티클 렌더링. 글 상세 페이지 구조 결정 대기
- `tests/` — 과거 실험. 정리 대상
- `design/` — 시안 후보군 A~H. `.gitignore` 처리, 커밋하지 않음

## 빌드

```bash
python3 tools/build.py          # 마커 영역 + 상세 페이지 생성
python3 tools/build.py --check  # 파일을 쓰지 않고 최신인지만 검사
```

### git 훅 — 초안이 새어나가지 않게

```bash
git config core.hooksPath tools/hooks   # 클론마다 한 번
```

- **pre-commit** — 초안을 뺀 상태로 다시 빌드하고 결과물을 스테이지에 올린다.
  커밋은 항상 "공개되는 모습"이 된다. `--drafts`로 미리보던 중에 커밋해도 알아서 정리된다.
- **pre-push** — 커밋에 초안 페이지가 남아 있거나 생성물이 원고와 어긋나면 푸시를 막는다.

푸시 시점에는 커밋이 이미 굳어 있어서 거기서 빌드해봐야 소용이 없다. 그래서 정리는 pre-commit이 하고
pre-push는 확인만 한다. 일부러 우회하려면 `--no-verify`.

### 푸시 후 초안 미리보기 되살리기

git에는 post-push 훅이 없다 — 클라이언트 훅은 `pre-push`가 끝이고 `post-receive`는 GitHub 쪽이다.
그래서 push를 감싼 스크립트를 쓴다.

```bash
./tools/push.sh            # = git push + 초안 포함 재빌드
git pushp                  # 같은 것 (alias, 클론마다 한 번 설정)
git config alias.pushp '!sh tools/push.sh'
```

푸시가 실패하면 재빌드하지 않는다. 재빌드 후에는 생성된 HTML이 초안 상태라 작업 트리가 dirty해지는데,
다음 커밋 때 pre-commit이 알아서 되돌리므로 그대로 둬도 된다.

**배포는 여전히 정적이다.** 빌더는 로컬에서 HTML을 생성할 뿐이고 GitHub Pages는 생성된 파일을 그대로 서빙한다.
런타임 JS로 목록을 그리지 않는 이유는 AI 크롤러 상당수가 JS를 실행하지 않아 SEO/AEO가 깨지기 때문이다.

빌더는 `<!-- build:NAME -->` … `<!-- /build:NAME -->` **사이만** 덮어쓴다. 그 바깥은 손으로 자유롭게 편집해도 된다.

| 마커 | 위치 | 내용 |
|---|---|---|
| `build:nav active=<키>` | 4개 페이지 | 공통 nav. 활성 항목만 다름 |
| `build:footer` | 4개 페이지 | 공통 footer. 4곳이 완전히 동일 |
| `build:articles limit=3` | `/` | `articles-md/*.md` 최신 3 |
| `build:articles` | `/articles/` | 전체 |
| `build:projects limit=3` | `/` | `projects-md/*.md` 상위 3 |
| `build:projects` | `/projects/` | 전체 |

상세 페이지는 마커가 아니라 **빌더가 통째로 생성**한다 — `articles-md/x.md` → `notes/x/index.html`,
`projects/x.md` → `work/x/index.html`. 생성 파일은 직접 고치지 말고 원본 `.md`를 고친다.
원본이 사라지면 해당 디렉터리도 자동 삭제된다(생성 표시가 있는 것만).

nav·footer·목록을 고칠 때는 **HTML이 아니라 `tools/build.py`와 `articles-md/`·`projects/`를 고치고 빌드**한다.

### frontmatter

```yaml
---
title: 제목            # 필수. 없으면 목록에서 제외된다
date: 2026.09          # 글 정렬 기준
tag: Simulation        # 글 배지
syndication: dev.to    # 선택. 쉼표로 여러 개
slug: custom-slug      # 선택. 기본값은 파일명
draft: true            # 선택. 목록·상세 페이지 모두 생성 안 함
math: true             # 선택. KaTeX를 이 글에서만 로드
scripts: /static/js/x.js   # 선택. 쉼표로 여러 개
styles: /static/css/x.css  # 선택
---
```

본문은 표·코드블록·각주·목차를 지원하고(`markdown` 내장 확장), **HTML을 그대로 통과시킨다** —
`<video>`, `<canvas>`, `<figure>` 등을 md 중간에 직접 쓰면 된다.
수식은 `$...$` / `$$...$$`로 쓰고 빌더가 코드 구간을 피해 추출한 뒤 KaTeX 구분자로 바꾼다.
템플릿은 `articles-md/template.md`, `projects-md/template.md` (둘 다 `draft: true`).

`_`로 시작하는 파일(`_README.md`)은 빌더가 콘텐츠로 읽지 않는다.

작업물은 `status`, `tags`, `summary`, `order`, `preview`(이미지 경로)를 쓴다.
읽기 시간은 본문 글자 수 ÷ 700(한국어 평균 독서 속도 **추정치**)으로 계산한다 — 실측이 아니다.

항목이 하나도 없으면 목록 자리에 "Working on it" 빈 상태 카드가 들어간다. 가짜 항목으로 채우지 않는다.

## 사실 취급

수치·연도를 지어내지 않는다. 실측하지 않은 값은 `20XX` `0 min`처럼 플레이스홀더로 두거나 슬롯 자체를 만들지 않는다.
BVH readout(`overlap`, `Σarea`)만 실제 계산값이다.
