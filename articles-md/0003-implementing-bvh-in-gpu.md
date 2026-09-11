---
title: GPU에서 돌아가는 BVH 구현하기
date: 2026.09
tag: Simulation
draft: true
math: true
# syndication: dev.to, Hashnode
# slug: custom-url-slug
# scripts: /static/js/demo-bvh.js
# styles: /static/css/demo-bvh.css
---

`draft: true`라서 목록에도 안 뜨고 페이지도 생성되지 않는다.
새 글을 쓸 때 이 파일을 복사해서 슬러그 이름으로 저장하고 `draft` 줄을 지운다.

```bash
cp posts/template.md posts/gpu-bvh-staged-port.md
# draft 줄 삭제 후
python3 tools/build.py
```

제목은 frontmatter의 `title`이 담당한다. **본문에 `# 제목`을 다시 쓰지 않는다.**
본문 소제목은 `##`부터 시작한다.

## 표

| 단계  | CPU    | GPU    | 비고                            |
| ----- | ------ | ------ | ------------------------------- |
| build | 0.0 ms | 0.0 ms | 실측 전에는 플레이스홀더로 둔다 |
| query | 0.0 ms | 0.0 ms |                                 |

## 수식

`math: true`일 때만 KaTeX를 불러온다. 인라인은 `$A_L / A$`처럼, 블록은 이렇게.

$$ \text{SAH}(N) = C_t + \frac{A_L}{A} N_L C_i + \frac{A_R}{A} N_R C_i $$

빌더가 변환 전에 수식 구간을 빼두므로 `$a_1$`의 밑줄이 이탤릭으로 먹히지 않는다.

## 코드

```cpp
// 긴 축 기준 median split
auto axis = (b.max - b.min).maxAxis();
std::nth_element(first, first + n / 2, last, ByAxis{axis});
```

## 이미지

이미지는 `static/assets/<슬러그>/` 아래 모은다.

![캡션으로 쓸 대체 텍스트](/static/assets/template/example.png)

## 비디오 · 인터랙티브

마크다운은 HTML을 그대로 통과시킨다. 필요한 곳에 직접 쓴다.

<figure>
  <video src="/static/assets/template/demo.mp4" controls muted loop playsinline></video>
  <figcaption>비디오는 저장소에 직접 넣지 말 것 — LFS 없이 금방 비대해진다.</figcaption>
</figure>

<figure>
  <canvas id="demo" height="300"></canvas>
  <figcaption>스크립트는 frontmatter의 <code>scripts:</code>로 붙인다.</figcaption>
</figure>

## 인용과 목록

> 줄일 수 있는 문장은 틀린 문장이다.

- 첫째
- 둘째
  - 중첩
