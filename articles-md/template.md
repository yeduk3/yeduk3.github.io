---
title: 글 제목이 여기 들어간다
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
cp articles-md/template.md posts/gpu-bvh-staged-port.md
# draft 줄 삭제 후
python3 tools/build.py
```

제목은 frontmatter의 `title`이 담당한다. **본문에 `# 제목`을 다시 쓰지 않는다.**
본문 소제목은 `##`부터 시작한다.

## 표

| 단계 | CPU | GPU | 비고 |
|---|---|---|---|
| build | 0.0 ms | 0.0 ms | 실측 전에는 플레이스홀더로 둔다 |
| query | 0.0 ms | 0.0 ms | |

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

어셋은 글 폴더(`articles-md/<슬러그>/`)에 md와 나란히 둔다. 빌더가 `/articles/<슬러그>/`로 복사하므로
상대 경로로 쓴다.

![캡션으로 쓸 대체 텍스트](example.png)

## 비디오 · 인터랙티브

마크다운은 HTML을 그대로 통과시킨다. 필요한 곳에 직접 쓴다.
GIF 대신 mp4. 짧은 무음 클립은 `autoplay muted loop playsinline`이 GIF처럼 동작한다.

<figure>
  <video src="demo.mp4" controls muted loop playsinline></video>
  <figcaption>GitHub Pages는 LFS를 서빙하지 않는다. 인코딩해서 작게 만든 mp4만 커밋한다.</figcaption>
</figure>

```bash
ffmpeg -i in.mov -an -vf "scale=1920:-2" -c:v libx264 -crf 23 -preset slow -pix_fmt yuv420p -movflags +faststart out.mp4
```

둘을 나란히 비교할 때는 `<figure class="compare">`에 `<video>` 둘.

<figure>
  <canvas id="demo" height="300"></canvas>
  <figcaption>스크립트는 frontmatter의 <code>scripts:</code>로 붙인다.</figcaption>
</figure>

## 인용과 목록

> 줄일 수 있는 문장은 틀린 문장이다.

- 첫째
- 둘째
  - 중첩
