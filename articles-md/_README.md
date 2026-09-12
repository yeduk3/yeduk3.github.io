# 글은 여기에 쓴다

글 하나 = 폴더 하나. `articles-md/<슬러그>/<슬러그>.md`가 원고이고, 이미지·mp4 같은 어셋은 같은 폴더에 둔다.
폴더 이름이 URL 슬러그가 된다 (`articles-md/gpu-bvh/gpu-bvh.md` → `/articles/gpu-bvh/`).

```bash
mkdir articles-md/<슬러그> && cp articles-md/template.md articles-md/<슬러그>/<슬러그>.md
python3 tools/build.py
```

빌드하면 `/articles/<슬러그>/index.html`과 어셋 복사본, `/articles/` 목록, 메인의 "최근 글" 3개가 같이 갱신된다.
어셋은 md에서 **상대 경로**로 쓴다 (`![](fig.png)`, `<video src="demo.mp4">`).
복사되는 확장자는 `tools/build.py`의 `ASSET_EXT`. `.mov` 원본 녹화는 복사·커밋되지 않는다.

파일 하나뿐인 글은 `articles-md/<슬러그>.md`로 flat하게 둬도 읽는다.

## frontmatter

| 키 | 필수 | 설명 |
|---|---|---|
| `title` | ✅ | 없으면 목록에 안 뜬다 |
| `date` | | 정렬 기준. `2026.09` 형식 |
| `tag` | | 목록 배지 한 개 |
| `syndication` | | `dev.to, Hashnode` 처럼 쉼표 구분 |
| `slug` | | 기본값은 폴더(파일) 이름 |
| `draft` | | `true`면 목록·상세 페이지 모두 생성 안 함 |
| `math` | | `true`면 이 글에서만 KaTeX 로드 |

읽기 시간은 본문 글자 수 ÷ 700으로 **추정**해 자동 계산한다 (실측 아님).

`_`로 시작하는 파일은 빌더가 무시한다. 이 파일이 그렇다. 나머지 작성법은 `template.md`.
