---
title: 작업물 제목
order: 99
status: Research
tags: C++17, Metal
summary: 목록 카드에 들어갈 한두 문장. 3줄을 넘으면 카드에서 말줄임 처리된다.
draft: true
# preview: /static/assets/template/cover.png
# math: true
# scripts: /static/js/demo.js
---

`draft: true`라서 목록에도 안 뜨고 페이지도 생성되지 않는다.
새 작업물을 추가할 때 이 파일을 복사해 슬러그 이름으로 저장하고 `draft` 줄을 지운다.

```bash
cp projects-md/template.md projects/ysim.md
python3 tools/build.py
```

`preview`를 지정하면 목록 카드의 왼쪽이 그 이미지로 채워지고, 없으면 `preview —` 빈 슬롯이 나온다.
**가짜 스크린샷을 넣지 않는다.**

## 무엇을 만들었나

한 문단으로 요약한다.

## 어떻게 만들었나

| 결정 | 이유 |
|---|---|
| | |

## 무엇을 배웠나

실패한 시도도 적는다. 그게 이 사이트에서 제일 값어치 있는 부분이다.

본문 문법은 `articles-md/template.md`와 같다 — 표·수식·코드·이미지·비디오·인터랙티브 전부 된다.
