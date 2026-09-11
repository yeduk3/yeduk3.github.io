#!/usr/bin/env python3
"""정적 페이지 빌더.

배포는 여전히 정적이다 — 이 스크립트는 로컬에서 HTML을 생성할 뿐이고,
GitHub Pages는 생성된 파일을 그대로 서빙한다. 런타임 JS로 목록을 그리지 않는 이유는
AI 크롤러 상당수가 JS를 실행하지 않아 SEO/AEO가 깨지기 때문이다.

하는 일:
  1. nav / footer를 한 곳에서 관리해 4개 페이지에 주입한다.
  2. posts/*.md, projects/*.md의 frontmatter를 읽어 목록을 생성한다.
  3. 항목이 없으면 빈 상태 문구를 대신 넣는다.

HTML의 `<!-- build:NAME ... -->` … `<!-- /build:NAME -->` 사이만 덮어쓴다.
그 바깥은 손으로 자유롭게 편집해도 빌드가 건드리지 않는다.

사용: python3 tools/build.py [--check]
      --check 는 파일을 쓰지 않고 최신 상태인지만 검사한다 (CI용).
"""

import html
import math
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = ["index.html", "about/index.html", "notes/index.html", "work/index.html"]

# 한국어 평균 독서 속도. 추정치이므로 분 단위로만 쓰고, 실측값인 척하지 않는다.
CHARS_PER_MIN = 700


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
        if k in ("tags", "syndication"):
            meta[k] = [p.strip() for p in v.split(",") if p.strip()]
        else:
            meta[k] = v
    return meta, body


def reading_minutes(body):
    text = re.sub(r"```.*?```", "", body, flags=re.S)      # 코드 블록 제외
    text = re.sub(r"[#>*_`\-\[\]()!]", "", text)
    text = re.sub(r"\s+", "", text)
    return max(1, math.ceil(len(text) / CHARS_PER_MIN))


def load(dirname, kind):
    """dirname/*.md 중 frontmatter가 있는 것만. 없는 파일은 경고만 하고 건너뛴다."""
    items, skipped = [], []
    d = ROOT / dirname
    if not d.exists():
        return items, skipped
    for p in sorted(d.glob("*.md")):
        if p.name.startswith("_"):      # _README.md 같은 안내 파일은 콘텐츠가 아니다
            continue
        meta, body = parse_front(p.read_text(encoding="utf-8"))
        if not meta or not meta.get("title"):
            skipped.append(p.name)
            continue
        if str(meta.get("draft", "")).lower() in ("true", "yes", "1"):
            skipped.append(p.name + " (draft)")
            continue
        meta["slug"] = meta.get("slug") or p.stem
        meta["minutes"] = reading_minutes(body)
        meta["_kind"] = kind
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
    {link("/work/", "작업", "work")}
    {link("/notes/", "글", "notes")}
    {link("/about/", "소개", "about")}
  </div>
  <div class="sx-nav__spacer"></div>
  <!-- 시스템 규칙: 뷰포트당 primary는 하나. 각 페이지의 primary는 본문에 있으므로 nav는 secondary. -->
  <a class="sx-btn sx-btn--secondary sx-btn--sm" href="mailto:yeduk33@gmail.com">메일 보내기</a>
</nav>"""


def footer():
    return """<footer class="band colophon">
  <div class="sx-container">
    <p>글은 마크다운으로 쓰고 git으로 버전 관리합니다. 원본은 저장소에 frontmatter 그대로 남습니다.
      <a href="https://github.com/yeduk3" target="_blank" rel="noreferrer">source</a><br>
      Symplex design system · Inter + JetBrains Mono · 정적 사이트.</p>
  </div>
</footer>"""


# ---------------------------------------------------------------- 목록 렌더
def empty_state(msg, sub):
    return f"""      <div class="sx-card sx-card--sunken empty">
        <p class="sx-eyebrow">Working on it</p>
        <p class="empty__msg">{html.escape(msg)}</p>
        <p class="sx-caption">{html.escape(sub)}</p>
      </div>"""


def note_row(m):
    e = html.escape
    tag = f'<span class="sx-badge">{e(m["tag"])}</span>' if m.get("tag") else ""
    syn = ""
    if m.get("syndication"):
        syn = " · also on " + ", ".join(e(s) for s in m["syndication"])
    return f"""      <a class="note" href="/notes/{e(m['slug'])}/">
        <span class="note__date">{e(m.get('date', ''))}</span>
        <span class="note__title">{e(m['title'])}</span>
        <span class="note__meta">{tag}<span class="sx-micro">{m['minutes']} min{syn}</span></span>
      </a>"""


def work_item(m):
    e = html.escape
    chips = "".join(f'<span class="sx-badge">{e(t)}</span>' for t in m.get("tags", []))
    badge = f'<span class="sx-badge sx-badge--outline">{e(m["status"])}</span>' if m.get("status") else ""
    if m.get("preview"):
        media = (f'<img src="{e(m["preview"])}" alt="{e(m["title"])} 프리뷰" loading="lazy" '
                 f'decoding="async" width="840" height="525">')
    else:
        # 프리뷰 이미지가 아직 없다. 가짜 스크린샷 대신 빈 슬롯임을 드러낸다.
        media = '<span class="sx-eyebrow">preview —</span>'
    return f"""      <a class="sx-card sx-card--flush sx-card--interactive work-item" href="/work/{e(m['slug'])}/">
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
                           "쓰는 중입니다. posts/ 에 frontmatter를 갖춘 .md를 넣으면 여기에 나타납니다.")
    return "\n".join(note_row(m) for m in items)


def render_work(items, limit):
    items = items[:limit] if limit else items
    if not items:
        return empty_state("정리 중인 작업이 있습니다.",
                           "projects/ 에 frontmatter를 갖춘 .md를 넣으면 여기에 나타납니다.")
    return "\n".join(work_item(m) for m in items)


# ---------------------------------------------------------------- 마커 치환
MARKER = re.compile(
    r"(?P<open><!--\s*build:(?P<name>[a-z]+)(?P<args>[^>]*?)-->)"
    r".*?"
    r"(?P<close><!--\s*/build:(?P=name)\s*-->)",
    re.S,
)


def parse_args(s):
    return dict(re.findall(r"(\w+)=([^\s]+)", s or ""))


def build(check=False):
    notes, skip_n = load("posts", "note")
    works, skip_w = load("projects", "work")
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
            elif name == "notes":
                body = render_notes(notes, limit)
            elif name == "work":
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

    print(f"notes {len(notes)}개, work {len(works)}개")
    if skip_n or skip_w:
        print("건너뜀(frontmatter 없음/draft):", ", ".join(skip_n + skip_w))
    print("\n".join("  " + r for r in report))
    if check:
        if changed:
            print("\n[check] 최신이 아님:", ", ".join(changed))
            return 1
        print("\n[check] 최신 상태")
        return 0
    print("갱신:", ", ".join(changed) if changed else "없음")
    return 0


if __name__ == "__main__":
    sys.exit(build(check="--check" in sys.argv))
