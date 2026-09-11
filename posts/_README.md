# 글은 여기에 쓴다

`posts/<슬러그>.md` 파일 하나가 글 하나다. 파일명이 URL 슬러그가 된다
(`posts/gpu-bvh-staged-port.md` → `/notes/gpu-bvh-staged-port/`).

작성 후 빌드하면 `/notes/` 전체 목록과 메인의 "최근 글" 3개가 같이 갱신된다.

```bash
python3 tools/build.py
```

## 템플릿

```markdown
---
title: GPU라고 다 빠르지 않다 — BVH 빌드를 단계별로 옮겨본 기록
date: 2026.09
tag: Simulation
---

본문을 마크다운으로 쓴다.
```

## frontmatter

| 키 | 필수 | 설명 |
|---|---|---|
| `title` | ✅ | 없으면 목록에 안 뜬다 |
| `date` | | 정렬 기준. `2026.09` 형식 |
| `tag` | | 목록 배지 한 개 |
| `syndication` | | `dev.to, Hashnode` 처럼 쉼표 구분 |
| `slug` | | 기본값은 파일명 |
| `draft` | | `true`면 목록에서 제외 |

읽기 시간은 본문 글자 수 ÷ 700으로 **추정**해 자동 계산한다 (실측 아님).

`_`로 시작하는 파일은 빌더가 무시한다. 이 파일이 그렇다.

## 아직 안 되는 것

목록은 `/notes/<슬러그>/`로 링크를 걸지만 **글 상세 페이지는 아직 생성되지 않는다** — 누르면 404다.
마크다운을 HTML로 렌더하는 단계가 미구현.
