from __future__ import annotations

import json
from html import escape
from pathlib import Path


def write_static_site(root: Path) -> Path:
    site_dir = root / "site"
    data_dir = site_dir / "data"
    site_dir.mkdir(parents=True, exist_ok=True)
    latest_path = data_dir / "latest.json"
    archive_path = data_dir / "archive.json"
    latest = json.loads(latest_path.read_text(encoding="utf-8")) if latest_path.exists() else empty_latest()
    archive = json.loads(archive_path.read_text(encoding="utf-8")) if archive_path.exists() else {"reports": []}
    html = render_homepage(latest, archive)
    index_path = site_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")
    (site_dir / ".nojekyll").write_text("", encoding="utf-8")
    return index_path


def empty_latest() -> dict:
    return {
        "date": "",
        "title": "AI 产品机会日报",
        "summary": "日报尚未生成。运行 scripts/daily-news run-daily 后，这里会显示最新内容。",
        "opportunities": [],
        "big_tech": [],
        "pain_points": [],
        "source_health": [],
    }


def render_homepage(latest: dict, archive: dict) -> str:
    date = escape(latest.get("date") or "Pending")
    summary = escape(latest.get("summary", ""))
    opportunities = latest.get("opportunities", [])
    big_tech = latest.get("big_tech", [])
    pain_points = latest.get("pain_points", [])
    reports = archive.get("reports", [])
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>daily-news · AI 产品机会日报</title>
  <meta name="description" content="本地自动生成的 AI 产品机会与巨头动态日报">
  <style>
    :root {{
      --ink:#0a1f3d;
      --ink-rgb:10,31,61;
      --paper:#f1f3f5;
      --paper-rgb:241,243,245;
      --paper-tint:#e4e8ec;
      --ink-tint:#152a4a;
      --rule:rgba(var(--ink-rgb),.2);
      --muted:rgba(var(--ink-rgb),.68);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.65;
      letter-spacing: 0;
    }}
    a {{ color: inherit; text-decoration-thickness: 1px; text-underline-offset: 3px; }}
    .article-hero {{
      min-height: 88vh;
      display: grid;
      grid-template-rows: auto 1fr auto;
      padding: clamp(24px, 5vw, 72px);
      background:
        radial-gradient(circle at 80% 12%, rgba(var(--ink-rgb),.11), transparent 34%),
        linear-gradient(180deg, var(--paper) 0%, var(--paper-tint) 100%);
      border-bottom: 1px solid var(--rule);
    }}
    .topbar, .meta-row, .section-label, .toc, .source-list, .theme-note {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .08em;
    }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--rule);
    }}
    .hero-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(280px, .65fr);
      gap: clamp(28px, 6vw, 80px);
      align-items: end;
      padding: 72px 0 42px;
    }}
    h1, h2, h3 {{
      font-family: Georgia, "Times New Roman", serif;
      font-weight: 500;
      letter-spacing: 0;
      margin: 0;
    }}
    h1 {{
      font-size: clamp(56px, 11vw, 132px);
      line-height: .88;
      max-width: 980px;
    }}
    .subtitle {{
      max-width: 720px;
      margin: 28px 0 0;
      font-size: clamp(18px, 2vw, 24px);
      color: var(--muted);
    }}
    .stat-band {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      border: 1px solid var(--rule);
    }}
    .stat {{ padding: 18px; border-right: 1px solid var(--rule); }}
    .stat:last-child {{ border-right: 0; }}
    .stat .n {{ font-family: Georgia, "Times New Roman", serif; font-size: 38px; line-height: 1; }}
    .stat .l {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11px; text-transform: uppercase; color: var(--muted); }}
    .article-shell {{
      display: grid;
      grid-template-columns: 220px minmax(0, 880px);
      gap: clamp(24px, 5vw, 72px);
      max-width: 1240px;
      margin: 0 auto;
      padding: clamp(32px, 5vw, 72px) clamp(20px, 4vw, 48px);
    }}
    .toc {{
      position: sticky;
      top: 24px;
      align-self: start;
      display: grid;
      gap: 12px;
      color: var(--muted);
    }}
    .toc-title {{ color: var(--ink); padding-bottom: 10px; border-bottom: 1px solid var(--rule); }}
    .article-section {{ padding: 0 0 64px; border-bottom: 1px solid var(--rule); margin-bottom: 64px; }}
    .article-section:last-child {{ border-bottom: 0; }}
    .section-label {{ color: var(--muted); margin-bottom: 12px; }}
    h2 {{ font-size: clamp(34px, 5vw, 64px); line-height: 1; margin-bottom: 24px; }}
    .lead {{ font-size: 21px; color: var(--muted); max-width: 760px; }}
    .card-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
    .signal-card {{
      min-height: 220px;
      border: 1px solid var(--rule);
      padding: 22px;
      background: rgba(var(--paper-rgb), .54);
    }}
    .signal-card h3 {{ font-size: 28px; line-height: 1.08; margin-bottom: 14px; }}
    .signal-card p {{ margin: 0 0 14px; color: var(--muted); }}
    .score {{
      display: inline-flex;
      align-items: center;
      height: 28px;
      padding: 0 10px;
      border: 1px solid var(--rule);
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
    }}
    .source-list {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; color: var(--muted); }}
    .wide-list {{ display: grid; gap: 14px; }}
    .list-row {{ display: grid; grid-template-columns: 72px 1fr; gap: 18px; padding: 18px 0; border-top: 1px solid var(--rule); }}
    .list-row strong {{ font-family: Georgia, "Times New Roman", serif; font-size: 24px; font-weight: 500; }}
    .pull-quote {{
      margin: 40px 0;
      padding: 30px 0 30px 28px;
      border-left: 2px solid var(--ink);
      font-family: Georgia, "Times New Roman", serif;
      font-size: clamp(28px, 4vw, 48px);
      line-height: 1.05;
    }}
    .references {{ display: grid; gap: 10px; color: var(--muted); }}
    .theme-note {{ margin-top: 24px; color: var(--muted); }}
    @media (max-width: 860px) {{
      .article-hero {{ min-height: auto; }}
      .hero-grid, .article-shell, .card-grid {{ grid-template-columns: 1fr; }}
      .toc {{ position: static; grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .stat-band {{ grid-template-columns: 1fr; }}
      .stat {{ border-right: 0; border-bottom: 1px solid var(--rule); }}
      .stat:last-child {{ border-bottom: 0; }}
      .list-row {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header class="article-hero">
    <div class="topbar">
      <span>daily-news · AI opportunity brief</span>
      <span>{date}</span>
    </div>
    <div class="hero-grid">
      <div>
        <div class="section-label">Today Brief</div>
        <h1>AI 产品机会日报</h1>
        <p class="subtitle">{summary}</p>
      </div>
      <div>
        <div class="stat-band">
          <div class="stat"><div class="n">{len(opportunities)}</div><div class="l">Opportunities</div></div>
          <div class="stat"><div class="n">{len(big_tech)}</div><div class="l">Big Tech</div></div>
          <div class="stat"><div class="n">{len(pain_points)}</div><div class="l">Pain Signals</div></div>
        </div>
        <div class="theme-note">Theme · 靛蓝瓷</div>
      </div>
    </div>
    <div class="meta-row">Local generation · Codex automation · GitHub Pages deployment</div>
  </header>

  <main class="article-shell">
    <nav class="toc" aria-label="文章目录">
      <div class="toc-title">Contents</div>
      <a href="#opportunities">01 · 今日机会</a>
      <a href="#big-tech">02 · 巨头动态</a>
      <a href="#pain">03 · 痛点证据</a>
      <a href="#archive">04 · 归档</a>
    </nav>
    <article class="article-content">
      <section class="article-section" id="opportunities">
        <div class="section-label">01 · Opportunities</div>
        <h2>今天最值得跟进的产品机会</h2>
        <p class="lead">优先选择同时具备用户痛点、产品发布和平台变化证据的信号。</p>
        <div class="card-grid">{render_cards(opportunities)}</div>
      </section>

      <section class="article-section" id="big-tech">
        <div class="section-label">02 · Big Tech</div>
        <h2>巨头动态改变能力边界</h2>
        <div class="wide-list">{render_rows(big_tech)}</div>
      </section>

      <section class="article-section" id="pain">
        <div class="section-label">03 · User Pain</div>
        <blockquote class="pull-quote">好的 AI 产品机会，往往先表现为重复出现的抱怨、绕路和预算摩擦。</blockquote>
        <div class="wide-list">{render_rows(pain_points)}</div>
      </section>

      <section class="article-section takeaway" id="archive">
        <div class="section-label">04 · Archive</div>
        <h2>日报归档</h2>
        <div class="references">{render_archive(reports)}</div>
      </section>
    </article>
  </main>
</body>
</html>
"""


def render_cards(items: list[dict]) -> str:
    if not items:
        return '<article class="signal-card"><h3>等待今日信号</h3><p>运行本地日报自动化后会显示产品机会。</p></article>'
    cards = []
    for item in items[:5]:
        cards.append(
            f"""<article class="signal-card">
  <span class="score">Score {escape(str(item.get('score', 0)))}</span>
  <h3>{escape(item.get('title', ''))}</h3>
  <p>{escape(item.get('summary', ''))}</p>
  <p>{escape(item.get('reason', ''))}</p>
  <div class="source-list">{render_sources(item)}</div>
</article>"""
        )
    return "\n".join(cards)


def render_rows(items: list[dict]) -> str:
    if not items:
        return '<div class="list-row"><span>--</span><div><strong>暂无足够高质量信号</strong><p>下一次生成时会继续覆盖。</p></div></div>'
    rows = []
    for index, item in enumerate(items[:5], start=1):
        rows.append(
            f"""<div class="list-row">
  <span>{index:02d}</span>
  <div><strong>{escape(item.get('title', ''))}</strong><p>{escape(item.get('summary', ''))}</p><div class="source-list">{render_sources(item)}</div></div>
</div>"""
        )
    return "\n".join(rows)


def render_sources(item: dict) -> str:
    links = []
    for source in item.get("sources", [])[:3]:
        published = source.get("published_date") or str(source.get("published_at", ""))[:10]
        label = source.get("name", "Source")
        if published:
            label = f"{label} · {published}"
        links.append(f"<a href=\"{escape(source.get('url', '#'))}\">{escape(label)}</a>")
    return " ".join(links)


def render_archive(reports: list[dict]) -> str:
    if not reports:
        return "<div>暂无归档。首次运行后会自动生成。</div>"
    return "\n".join(
        f"<div><a href=\"../{escape(report.get('path', '#'))}\">{escape(report.get('date', ''))} · {escape(report.get('title', 'AI 产品机会日报'))}</a></div>"
        for report in reports[:20]
    )
