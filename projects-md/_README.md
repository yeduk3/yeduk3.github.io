# 작업물은 여기에 쓴다

`projects-md/<슬러그>.md` 파일 하나가 작업물 하나다. 파일명이 URL 슬러그가 된다
(`projects/ysim.md` → `/projects/ysim/`).

작성 후 빌드하면 `/projects/` 전체 목록과 메인의 "최근 작업" 3개가 같이 갱신된다.

```bash
python3 tools/build.py
```

## 템플릿

```markdown
---
title: ysim — GPU 시뮬레이션 엔진
order: 01
status: 20XX — now
tags: C++17, Metal, LBVH
summary: 목록 카드에 들어갈 한두 문장. 3줄을 넘기면 말줄임 처리된다.
preview: /static/assets/ysim.png
---

상세 내용을 마크다운으로 쓴다.
```

## frontmatter

| 키 | 필수 | 설명 |
|---|---|---|
| `title` | ✅ | 없으면 목록에 안 뜬다 |
| `summary` | | 카드 설명. 3줄 초과분은 `...` |
| `status` | | 우측 배지. `Shipped`, `Research` 등 |
| `tags` | | 쉼표 구분 |
| `order` | | 정렬 기준. `01`, `02` … |
| `preview` | | 이미지 경로. 없으면 `preview —` 빈 슬롯이 나온다 |
| `slug` | | 기본값은 파일명 |
| `draft` | | `true`면 목록에서 제외 |

`_`로 시작하는 파일은 빌더가 무시한다. 이 파일이 그렇다.

## 아직 안 되는 것

목록은 `/projects/<슬러그>/`로 링크를 걸지만 **상세 페이지는 아직 생성되지 않는다** — 누르면 404다.
