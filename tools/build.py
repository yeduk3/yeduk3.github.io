#!/usr/bin/env python3
"""정적 페이지 빌더.

배포는 여전히 정적이다 — 이 스크립트는 로컬에서 HTML을 생성할 뿐이고,
GitHub Pages는 생성된 파일을 그대로 서빙한다. 런타임 JS로 목록을 그리지 않는 이유는
AI 크롤러 상당수가 JS를 실행하지 않아 SEO/AEO가 깨지기 때문이다.

하는 일:
  1. nav / footer를 한 곳에서 관리해 4개 페이지에 주입한다.
  2. articles-md/*.md, projects-md/*.md의 frontmatter를 읽어 목록을 생성한다.
  3. 항목이 없으면 빈 상태 문구를 대신 넣는다.

HTML의 `<!-- build:NAME ... -->` … `<!-- /build:NAME -->` 사이만 덮어쓴다.
그 바깥은 손으로 자유롭게 편집해도 빌드가 건드리지 않는다.

사용: python3 tools/build.py [--check] [--drafts]
      --check  파일을 쓰지 않고 최신 상태인지만 검사한다 (CI용).
      --drafts draft: true인 글/작업물까지 포함해 빌드한다. 미리보기 전용.

`--drafts`로 만든 HTML을 그대로 커밋하면 초안이 공개된다. 방지 장치 셋:
  · 초안은 목록·상세에 DRAFT 배지가 붙는다
  · 초안 상세 페이지에는 robots noindex가 들어간다
  · 빌드 끝에 경고를 찍고, 푸시 전 되돌리는 명령을 알려준다
푸시 전에는 반드시 인자 없이 다시 빌드한다.
"""

import filecmp
import html
import json
import math
import pathlib
import re
import shutil
import sys

try:
    import markdown as _md
except ImportError:                      # 목록만 갱신하고 상세 페이지는 건너뛴다
    _md = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = ["index.html", "about/index.html", "articles/index.html", "projects/index.html"]

# 한국어 평균 독서 속도. 추정치이므로 분 단위로만 쓰고, 실측값인 척하지 않는다.
CHARS_PER_MIN = 700

SITE = "https://yeduk3.github.io"

PERSON = {
    "@type": "Person", "@id": SITE + "/#person", "name": "yeduk3", "url": SITE + "/",
    "email": "mailto:yeduk33@gmail.com",
    "knowsAbout": ["컴퓨터 그래픽스", "물리 기반 시뮬레이션", "충돌 검출", "BVH", "LBVH",
                   "GPU 프로그래밍", "Metal", "C++17", "Swift"],
    "sameAs": ["https://github.com/yeduk3", "https://solved.ac/profile/yeduk3",
               "https://www.acmicpc.net/user/yeduk3"],
}
WEBSITE = {
    "@type": "WebSite", "@id": SITE + "/#site", "url": SITE + "/", "name": "yeduk3",
    "inLanguage": "ko", "author": {"@id": SITE + "/#person"},
}
MD_EXTENSIONS = ["tables", "fenced_code", "footnotes", "attr_list", "toc", "sane_lists"]

# KaTeX — 수식이 있는 글에서만 로드한다 (CSS+JS 약 300KB)
KATEX = (
    '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">\n'
    '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>\n'
    '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"\n'
    '        onload="renderMathInElement(document.body)"></script>'
)


# ---------------------------------------------------------------- frontmatter
def parse_front(text):
    """맨 앞 `---` 블록을 dict로. 없으면 None (목록에서 제외된다)."""
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end == -1:
        return None, text
    raw, body = text[3:end], text[end + 4:]
    meta = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip().strip('"').strip("'")
        k = k.strip()
        if k in ("tags", "syndication", "scripts", "styles"):
            meta[k] = [p.strip() for p in v.split(",") if p.strip()]
        else:
            meta[k] = v
    return meta, body


def reading_minutes(body):
    text = re.sub(r"```.*?```", "", body, flags=re.S)      # 코드 블록 제외
    text = re.sub(r"[#>*_`\-\[\]()!]", "", text)
    text = re.sub(r"\s+", "", text)
    return max(1, math.ceil(len(text) / CHARS_PER_MIN))


def load(dirname, kind, drafts=False):
    """dirname/*.md 중 frontmatter가 있는 것만. 없는 파일은 경고만 하고 건너뛴다.
    drafts=True면 draft 항목도 포함하고 _draft 표시를 남긴다."""
    items, skipped = [], []
    d = ROOT / dirname
    if not d.exists():
        return items, skipped
    # 글 하나 = 폴더 하나: <dir>/<slug>/<slug>.md + 같은 폴더의 어셋. 파일 하나짜리 flat .md도 읽는다.
    sources = list(d.glob("*.md")) + [x / (x.name + ".md") for x in d.iterdir() if x.is_dir()]
    for p in sorted(x for x in sources if x.exists()):
        if p.name.startswith("_"):      # _README.md 같은 안내 파일은 콘텐츠가 아니다
            continue
        meta, body = parse_front(p.read_text(encoding="utf-8"))
        if not meta or not meta.get("title"):
            skipped.append(p.name)
            continue
        is_draft = str(meta.get("draft", "")).lower() in ("true", "yes", "1")
        if is_draft and not drafts:
            skipped.append(p.name + " (draft)")
            continue
        meta["_draft"] = is_draft
        meta["slug"] = meta.get("slug") or p.stem
        meta["minutes"] = reading_minutes(body)
        meta["_kind"] = kind
        meta["_body"] = body
        meta["_assets"] = p.parent if p.parent != d else None
        items.append(meta)
    if kind == "note":
        items.sort(key=lambda m: m.get("date", ""), reverse=True)
    else:
        items.sort(key=lambda m: (m.get("order", "99"), m["slug"]))
    return items, skipped


# ---------------------------------------------------------------- 공통 크롬
def nav(active):
    def link(href, label, key):
        cls = "sx-nav__link sx-nav__link--active" if key == active else "sx-nav__link"
        aria = ' aria-current="page"' if key == active else ""
        return f'<a class="{cls}" href="{href}"{aria}>{label}</a>'
    return f"""<nav class="sx-nav">
  <a class="sx-nav__brand" href="/">yeduk3</a>
  <div class="sx-nav__links">
    {link("/projects/", "작업", "projects")}
    {link("/articles/", "글", "articles")}
    {link("/about/", "소개", "about")}
  </div>
  <div class="sx-nav__spacer"></div>
  <!-- 시스템 규칙: 뷰포트당 primary는 하나. 각 페이지의 primary는 본문에 있으므로 nav는 secondary. -->
  <a class="sx-btn sx-btn--secondary sx-btn--sm" href="mailto:yeduk33@gmail.com">메일 보내기</a>
</nav>"""


def footer():
    return """<footer class="band colophon">
  <div class="sx-container">
    <p>Hosted by Github Pages.
      <a href="https://github.com/yeduk3" target="_blank" rel="noreferrer">source</a><br>
      If there are any problems, please contact to me.</p>
  </div>
</footer>"""


# ---------------------------------------------------------------- 목록 렌더
def empty_state(msg, sub):
    return f"""      <div class="sx-card sx-card--sunken empty">
        <p class="sx-eyebrow">Working on it</p>
        <p class="empty__msg">{html.escape(msg)}</p>
        <p class="sx-caption">{html.escape(sub)}</p>
      </div>"""


DRAFT_BADGE = '<span class="sx-badge sx-badge--danger">draft</span>'


def note_row(m):
    e = html.escape
    tag = f'<span class="sx-badge">{e(m["tag"])}</span>' if m.get("tag") else ""
    # 배지는 제목 옆에 둔다. .note__meta는 좁은 폭에서 숨겨져서 안전장치 구실을 못 한다.
    mark = DRAFT_BADGE if m.get("_draft") else ""
    syn = ""
    if m.get("syndication"):
        syn = " · also on " + ", ".join(e(s) for s in m["syndication"])
    return f"""      <a class="note" href="/articles/{e(m['slug'])}/">
        <span class="note__date">{e(m.get('date', ''))}</span>
        <span class="note__title">{mark}{e(m['title'])}</span>
        <span class="note__meta">{tag}<span class="sx-micro">{m['minutes']} min{syn}</span></span>
      </a>"""


def work_item(m):
    e = html.escape
    chips = "".join(f'<span class="sx-badge">{e(t)}</span>' for t in m.get("tags", []))
    badge = f'<span class="sx-badge sx-badge--outline">{e(m["status"])}</span>' if m.get("status") else ""
    if m.get("_draft"):
        badge = DRAFT_BADGE + badge
    if m.get("preview"):
        media = (f'<img src="{e(m["preview"])}" alt="{e(m["title"])} 프리뷰" loading="lazy" '
                 f'decoding="async" width="840" height="525">')
    else:
        # 프리뷰 이미지가 아직 없다. 가짜 스크린샷 대신 빈 슬롯임을 드러낸다.
        media = '<span class="sx-eyebrow">preview —</span>'
    return f"""      <a class="sx-card sx-card--flush sx-card--interactive work-item" href="/projects/{e(m['slug'])}/">
        <div class="sx-media work-item__preview">{media}</div>
        <div class="work-item__body">
          <div class="work-card__top">
            <h3 class="sx-h3">{e(m['title'])}</h3>
            {badge}
          </div>
          <p>{e(m.get('summary', ''))}</p>
          <div class="tags">{chips}</div>
        </div>
      </a>"""


def render_notes(items, limit):
    items = items[:limit] if limit else items
    if not items:
        return empty_state("아직 공개한 글이 없습니다.",
                           "쓰는 중입니다. articles-md/ 에 frontmatter를 갖춘 .md를 넣으면 여기에 나타납니다.")
    return "\n".join(note_row(m) for m in items)


def render_latest(items):
    """요약 스트립의 "Latest note" 한 줄. 최신 글 하나에 링크를 건다. 없으면 빈 상태 문구."""
    if not items:
        return "            <dd>working...</dd>"
    m, e = items[0], html.escape
    mark = DRAFT_BADGE if m.get("_draft") else ""
    return f'            <dd>{mark}<a href="/articles/{e(m["slug"])}/">{e(m["title"])}</a></dd>'


def render_work(items, limit):
    items = items[:limit] if limit else items
    if not items:
        return empty_state("정리 중인 작업이 있습니다.",
                           "projects-md/ 에 frontmatter를 갖춘 .md를 넣으면 여기에 나타납니다.")
    return "\n".join(work_item(m) for m in items)



# ---------------------------------------------------------------- 상세 페이지
# 마크다운이 $a_1$의 밑줄을 이탤릭으로 먹는다. 변환 전에 수식을 빼두었다가 되돌린다.
# (pymdown-extensions의 arithmatex와 같은 일을 하지만 의존성을 늘리지 않는다.)
_MATH_BLOCK = re.compile(r"\$\$(.+?)\$\$", re.S)
_MATH_INLINE = re.compile(r"(?<![\\$])\$(?!\s)([^$\n]+?)(?<!\s)\$(?!\$)")


# 코드 안의 $는 수식이 아니다. 셸의 $HOME, 문자열 보간 등이 수식으로 잡히면 글이 깨진다.
_CODE = re.compile(r"```.*?```|~~~.*?~~~|`[^`\n]+`", re.S)


def protect_math(text):
    store = []

    def stash(m, disp):
        store.append((disp, m.group(1)))
        return "\x00MATH%d\x00" % (len(store) - 1)

    def sub_math(chunk):
        chunk = _MATH_BLOCK.sub(lambda m: stash(m, True), chunk)
        return _MATH_INLINE.sub(lambda m: stash(m, False), chunk)

    out, pos = [], 0
    for m in _CODE.finditer(text):       # 코드 구간은 건너뛰고 사이만 치환한다
        out.append(sub_math(text[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(sub_math(text[pos:]))
    return "".join(out), store


def restore_math(html_text, store):
    for i, (disp, expr) in enumerate(store):
        # KaTeX는 textContent를 읽으므로 HTML 특수문자를 이스케이프해 둔다
        e = html.escape(expr, quote=False)
        wrapped = ("\\[" + e + "\\]") if disp else ("\\(" + e + "\\)")
        html_text = html_text.replace("\x00MATH%d\x00" % i, wrapped)
    return html_text


def iso_date(d):
    """schema.org는 ISO 8601을 요구한다. 2026.09 / 2026.09.11 → 2026-09 / 2026-09-11.
    해석할 수 없으면 None을 돌려 구조화 데이터에서 빼버린다 — 틀린 날짜보다 없는 편이 낫다."""
    if not d:
        return None
    m = re.fullmatch(r"(\d{4})[.\-/](\d{1,2})(?:[.\-/](\d{1,2}))?", d.strip())
    if not m:
        return None
    y, mo, day = m.group(1), int(m.group(2)), m.group(3)
    if not 1 <= mo <= 12:
        return None
    return f"{y}-{mo:02d}" + (f"-{int(day):02d}" if day else "")


def summarize(body, limit=150):
    """meta description용 요약. 코드·수식·HTML·마크다운 기호를 걷어낸 첫 문장들."""
    t = re.sub(r"```.*?```|~~~.*?~~~", " ", body, flags=re.S)
    t = re.sub(r"\$\$.+?\$\$", " ", t, flags=re.S)
    t = re.sub(r"\$[^$\n]+\$", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)                          # raw HTML
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)             # 이미지
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)          # 링크는 글자만
    t = re.sub(r"^\s{0,3}#{1,6}\s+", "", t, flags=re.M)     # 제목 기호
    t = re.sub(r"^\s*[-*+]\s+", "", t, flags=re.M)          # 목록 기호
    t = re.sub(r"[`*_>|]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return (t[:limit].rstrip() + "…") if len(t) > limit else t


def render_markdown(body):
    text, store = protect_math(body)
    out = _md.markdown(text, extensions=MD_EXTENSIONS)
    return restore_math(out, store)


def document(title, desc, path, body, *, ld=None, math_on=False, scripts=(), styles=(), draft=False):
    """생성 페이지 한 장. 손으로 쓰는 4개 페이지와 head 구성을 맞춘다."""
    graph = [PERSON, WEBSITE] + (ld or [])
    ld_json = json.dumps({"@context": "https://schema.org", "@graph": graph},
                         ensure_ascii=False, indent=2)
    extra = ""
    if draft:
        # 초안이 실수로 배포돼도 색인되지 않게
        extra += '\n<meta name="robots" content="noindex, nofollow" />'
    if math_on:
        extra += "\n" + KATEX
    for st in styles:
        extra += f'\n<link rel="stylesheet" href="{html.escape(st)}">'
    for sc in scripts:
        extra += f'\n<script src="{html.escape(sc)}" defer></script>'
    return f"""<!doctype html>
<html lang="ko">
<head>
<!-- 이 파일은 tools/build.py가 생성한다. 직접 고치지 말고 원본 .md를 고친 뒤 다시 빌드할 것. -->
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{html.escape(title)} — yeduk3</title>
<meta name="description" content="{html.escape(desc)}" />
<meta name="author" content="yeduk3" />
<link rel="canonical" href="{SITE}{path}" />
<meta property="og:type" content="article" />
<meta property="og:site_name" content="yeduk3" />
<meta property="og:locale" content="ko_KR" />
<meta property="og:title" content="{html.escape(title)}" />
<meta property="og:description" content="{html.escape(desc)}" />
<meta property="og:url" content="{SITE}{path}" />
<meta property="og:image" content="{SITE}/static/og.png" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{html.escape(title)}" />
<meta name="twitter:description" content="{html.escape(desc)}" />
<meta name="twitter:image" content="{SITE}/static/og.png" />

<script type="application/ld+json">
{ld_json}
</script>

<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="/static/css/symplex.css" />
<link rel="stylesheet" href="/style.css" />{extra}
</head>
<body>

{nav(None)}

{body}

{footer()}
</body>
</html>
"""


def detail(m):
    """글/작업물 한 편의 상세 페이지를 (경로, HTML)로 돌려준다."""
    e = html.escape
    kind = m["_kind"]
    base = "/articles/" if kind == "note" else "/projects/"
    path = f"{base}{m['slug']}/"
    back = "글 전체" if kind == "note" else "작업 전체"
    eyebrow = m.get("tag") or m.get("status") or ("Writing" if kind == "note" else "Selected work")

    bits = []
    if m.get("date"):
        bits.append(e(m["date"]))
    if kind == "note":
        bits.append(f"{m['minutes']} min")
    for t in m.get("tags", []):
        bits.append(e(t))
    if m.get("syndication"):
        bits.append("also on " + ", ".join(e(x) for x in m["syndication"]))
    if m.get("_draft"):
        bits.insert(0, "DRAFT")
    meta_line = " · ".join(bits)

    desc = m.get("summary") or summarize(m["_body"])

    ld = [{
        "@type": "BlogPosting" if kind == "note" else "CreativeWork",
        "headline": m["title"],
        "author": {"@id": SITE + "/#person"},
        "mainEntityOfPage": SITE + path,
        # 해석 가능한 날짜일 때만 넣는다. 없는 날짜를 지어내지 않는다.
        **({"datePublished": iso_date(m.get("date"))} if iso_date(m.get("date")) else {}),
    }]

    body = f"""<header class="sec--tight post-head">
  <div class="sx-container-text">
    <a class="sx-micro post-back" href="{base}">← {back}</a>
    <p class="sx-eyebrow">{e(eyebrow)}</p>
    <h1 class="sx-h1">{e(m['title'])}</h1>
    <p class="sx-caption post-meta">{meta_line}</p>
  </div>
</header>

<article class="sec--tight">
  <div class="sx-container-text">
    <div class="prose">
{render_markdown(m['_body'])}
    </div>
  </div>
</article>"""

    return path, document(m["title"], desc, path, body,
                          ld=ld, math_on=str(m.get("math", "")).lower() in ("true", "yes", "1"),
                          scripts=m.get("scripts", ()), styles=m.get("styles", ()),
                          draft=bool(m.get("_draft")))


GEN_MARK = "<!-- 이 파일은 tools/build.py가 생성한다."

# 원고 폴더에서 생성 디렉터리로 복사하는 어셋. 원본 녹화(.mov)나 작업 파일은 서빙하지 않는다.
ASSET_EXT = {".mp4", ".webm", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".pdf", ".json", ".js", ".css"}


def sync_assets(src, out_dir, check):
    """원고 폴더의 어셋을 생성 디렉터리로 복사하고, 원본이 사라진 파일은 지운다. 바뀐 파일명을 돌려준다."""
    changed, keep = [], {"index.html"}
    for f in sorted(src.iterdir()) if src else []:
        if f.suffix.lower() not in ASSET_EXT or f.name.startswith((".", "_")):
            continue
        keep.add(f.name)
        dst = out_dir / f.name
        if not (dst.exists() and filecmp.cmp(f, dst, shallow=False)):
            changed.append(f.name)
            if not check:
                out_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst)
    if out_dir.exists():
        for f in out_dir.iterdir():
            if f.is_file() and f.name not in keep:
                changed.append(f.name)
                if not check:
                    f.unlink()
    return changed


def write_details(items, check):
    """상세 페이지를 쓰고, 원본이 사라진 생성 디렉터리는 지운다."""
    if _md is None:
        return [], ["markdown 패키지가 없어 상세 페이지를 건너뜀 (pip install markdown)"]
    written, notes = [], []
    wanted = {}
    for m in items:
        path, doc = detail(m)
        wanted[path] = doc
        out = ROOT / path.strip("/") / "index.html"
        old = out.read_text(encoding="utf-8") if out.exists() else None
        if old != doc:
            written.append(path)
            if not check:
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(doc, encoding="utf-8")
        written += [path + f for f in sync_assets(m["_assets"], out.parent, check)]
    # 고아 정리: 생성 표시가 있는 디렉터리만 지운다 (손으로 쓴 페이지는 건드리지 않는다)
    for base in ("articles", "projects"):
        d = ROOT / base
        if not d.exists():
            continue
        for sub in sorted(x for x in d.iterdir() if x.is_dir()):
            idx = sub / "index.html"
            p = f"/{base}/{sub.name}/"
            if p in wanted or not idx.exists():
                continue
            if GEN_MARK in idx.read_text(encoding="utf-8"):
                notes.append(f"고아 삭제 {p}")
                if not check:
                    shutil.rmtree(sub)
    return written, notes


# ---------------------------------------------------------------- 마커 치환
MARKER = re.compile(
    r"(?P<open><!--\s*build:(?P<name>[a-z]+)(?P<args>[^>]*?)-->)"
    r".*?"
    r"(?P<close><!--\s*/build:(?P=name)\s*-->)",
    re.S,
)


def parse_args(s):
    return dict(re.findall(r"(\w+)=([^\s]+)", s or ""))


def build(check=False, drafts=False):
    notes, skip_n = load("articles-md", "note", drafts)
    works, skip_w = load("projects-md", "work", drafts)
    changed, report = [], []

    for rel in PAGES:
        path = ROOT / rel
        src = path.read_text(encoding="utf-8")

        def fill(mo):
            name = mo.group("name")
            args = parse_args(mo.group("args"))
            limit = int(args["limit"]) if args.get("limit") else None
            if name == "nav":
                body = nav(args.get("active"))
            elif name == "footer":
                body = footer()
            elif name == "articles":
                body = render_notes(notes, limit)
            elif name == "latest":
                body = render_latest(notes)
            elif name == "projects":
                body = render_work(works, limit)
            else:
                raise SystemExit(f"{rel}: 알 수 없는 build 마커 '{name}'")
            return f"{mo.group('open')}\n{body}\n{mo.group('close')}"

        out, n = MARKER.subn(fill, src)
        report.append(f"{rel:20} 마커 {n}개")
        if out != src:
            changed.append(rel)
            if not check:
                path.write_text(out, encoding="utf-8")

    det, det_notes = write_details(notes + works, check)
    for n in det_notes:
        print("  " + n)

    n_draft = sum(1 for m in notes + works if m.get("_draft"))
    print(f"notes {len(notes)}개, work {len(works)}개 · 상세 페이지 {len(det)}건 갱신"
          + (f" · draft {n_draft}건 포함" if n_draft else ""))
    if skip_n or skip_w:
        print("건너뜀(frontmatter 없음/draft):", ", ".join(skip_n + skip_w))
    print("\n".join("  " + r for r in report))
    changed += det
    if check:
        if changed:
            print("\n[check] 최신이 아님:", ", ".join(changed))
            return 1
        print("\n[check] 최신 상태")
        return 0
    print("갱신:", ", ".join(changed) if changed else "없음")
    if n_draft:
        print(f"\n*** 초안 {n_draft}건이 생성된 HTML에 들어 있다. 이대로 커밋하지 말 것. ***")
        print("    푸시 전:  python3 tools/build.py   (인자 없이 다시 빌드)")
    return 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    unknown = [a for a in argv if a not in ("--check", "--drafts")]
    if unknown:
        raise SystemExit(f"알 수 없는 인자: {' '.join(unknown)}\n사용: build.py [--check] [--drafts]")
    sys.exit(build(check="--check" in argv, drafts="--drafts" in argv))
