"""Build the offline reviewer-facing HTML library from authoritative Markdown."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
import re


ROOT = Path(__file__).parents[1]
OUTPUT = ROOT / "docs" / "submission"


@dataclass(frozen=True)
class Page:
    key: str
    title: str
    short_title: str
    category: str
    summary: str
    source: str
    output: str
    accent: str
    accent_soft: str
    status: str


PAGES = (
    Page(
        "case-study",
        "VALI: Kalshi Quant Researcher Case Study",
        "Case study",
        "Portfolio narrative",
        "The research question, methodology, engineering work, honest result, and relevance to event-market research.",
        "docs/submission/KALSHI_QUANT_RESEARCHER_CASE_STUDY.md",
        "KALSHI_QUANT_RESEARCHER_CASE_STUDY.html",
        "#00a891",
        "#d6f4ed",
        "Research engine MVP",
    ),
    Page(
        "validation-plan",
        "Step 5A Empirical Validation Plan",
        "Validation plan",
        "Pre-analysis protocol",
        "Frozen hypotheses, required baselines, metrics, data gates, falsification conditions, and claim boundaries.",
        "docs/operational/5A_EMPIRICAL_VALIDATION_PLAN.md",
        "EMPIRICAL_VALIDATION_PLAN.html",
        "#8066a8",
        "#eee7f8",
        "Predeclared before evaluation",
    ),
    Page(
        "data-audit",
        "Data Availability Audit",
        "Data audit",
        "Evidence inventory",
        "A local-only audit separating empirical-looking public data, deterministic fixtures, missing inputs, and blockers.",
        "experiments/fed_easing_kxfed_v1/DATA_AVAILABILITY_AUDIT.md",
        "DATA_AVAILABILITY_AUDIT.html",
        "#d68a20",
        "#fff0d5",
        "Insufficient attention history",
    ),
    Page(
        "attention-protocol",
        "Attention Data Acquisition Protocol",
        "Attention protocol",
        "Point-in-time provenance",
        "The acceptable sources, required fields, revision semantics, prohibited inputs, and coverage gate for empirical attention history.",
        "experiments/fed_easing_kxfed_v1/ATTENTION_DATA_ACQUISITION_PROTOCOL.md",
        "ATTENTION_DATA_ACQUISITION_PROTOCOL.html",
        "#287ab8",
        "#dfeffc",
        "Not acquired",
    ),
    Page(
        "kalshi-ledger",
        "Kalshi Reconstruction Ledger",
        "Kalshi ledger",
        "Market-data lineage",
        "A conservative classification of public quotes, trades, fixtures, depth evidence, mixed captures, and reconstruction decisions.",
        "experiments/fed_easing_kxfed_v1/KALSHI_RECONSTRUCTION_LEDGER.md",
        "KALSHI_RECONSTRUCTION_LEDGER.html",
        "#c85047",
        "#fbe5e2",
        "Manual tiering required",
    ),
    Page(
        "final-validation",
        "VALI Final 4-Series Validation Report",
        "Validation report",
        "Release verification",
        "Repository identity, automated tests, CLI smoke checks, contract validation, caveats, and bounded readiness conclusion.",
        "FINAL_VALIDATION_REPORT.md",
        "FINAL_VALIDATION_REPORT.html",
        "#17815f",
        "#daf1e8",
        "4-series pass",
    ),
    Page(
        "reviewer-guide",
        "VALI Reviewer Guide",
        "Reviewer guide",
        "Fast review path",
        "A concise route through the repository, evaluation checklist, caveats, non-inferences, and next research step.",
        "docs/submission/REVIEWER_GUIDE.md",
        "REVIEWER_GUIDE.html",
        "#a25079",
        "#f7e3ed",
        "Read this first",
    ),
)


def slugify(value: str) -> str:
    plain = re.sub(r"[`*_]", "", value).casefold()
    return re.sub(r"[^a-z0-9]+", "-", plain).strip("-") or "section"


def inline(value: str) -> str:
    code_values: list[str] = []

    def stash_code(match: re.Match[str]) -> str:
        code_values.append(match.group(1))
        return f"@@CODE{len(code_values) - 1}@@"

    value = re.sub(r"`([^`]+)`", stash_code, value)
    value = escape(value, quote=False)
    value = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", value)
    for index, code in enumerate(code_values):
        value = value.replace(f"@@CODE{index}@@", f"<code>{escape(code)}</code>")
    return value


def is_structural(line: str) -> bool:
    stripped = line.strip()
    return (
        not stripped
        or stripped.startswith("#")
        or stripped.startswith("```")
        or stripped.startswith(">")
        or stripped.startswith("|")
        or bool(re.match(r"^[-*]\s+", stripped))
        or bool(re.match(r"^\d+\.\s+", stripped))
    )


def render_table(lines: list[str]) -> str:
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    if len(rows) > 1 and all(re.fullmatch(r":?-{3,}:?", cell) for cell in rows[1]):
        header, body = rows[0], rows[2:]
    else:
        header, body = rows[0], rows[1:]
    head = "".join(f"<th>{inline(cell)}</th>" for cell in header)
    rendered = [f"<thead><tr>{head}</tr></thead>"]
    if body:
        rendered.append("<tbody>")
        rendered.extend("<tr>" + "".join(f"<td>{inline(cell)}</td>" for cell in row) + "</tr>" for row in body)
        rendered.append("</tbody>")
    return '<div class="table-scroll"><table>' + "".join(rendered) + "</table></div>"


def markdown_body(markdown: str) -> tuple[str, list[tuple[str, str]]]:
    lines = markdown.splitlines()
    output: list[str] = []
    toc: list[tuple[str, str]] = []
    index = 0
    section_open = False
    intro_open = False
    section_number = 0
    used_slugs: dict[str, int] = {}

    def unique_slug(title: str) -> str:
        base = slugify(title)
        count = used_slugs.get(base, 0)
        used_slugs[base] = count + 1
        return base if count == 0 else f"{base}-{count + 1}"

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue

        if stripped.startswith("# "):
            index += 1
            continue

        if stripped.startswith("## "):
            if intro_open:
                output.append("</div>")
                intro_open = False
            if section_open:
                output.append("</div></section>")
            title = stripped[3:].strip()
            section_id = unique_slug(title)
            toc.append((section_id, re.sub(r"[`*_]", "", title)))
            section_number += 1
            output.append(
                f'<section class="doc-section" id="{section_id}" data-doc-section>'
                f'<div class="section-heading"><span class="section-index">Section {section_number:02d}</span>'
                f'<h2>{inline(title)}</h2><button class="section-toggle" type="button" '
                f'aria-controls="{section_id}-body" aria-expanded="true" '
                f'aria-label="Collapse {escape(title)}" data-section-title="{escape(title, quote=True)}">⌄</button></div>'
                f'<div class="section-body" id="{section_id}-body">'
            )
            section_open = True
            index += 1
            continue

        if not section_open and not intro_open:
            output.append('<div class="doc-intro">')
            intro_open = True

        heading = re.match(r"^(#{3,6})\s+(.+)$", stripped)
        if heading:
            level = min(4, len(heading.group(1)))
            output.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
            index += 1
            continue

        if stripped.startswith("```"):
            language = stripped[3:].strip()
            code: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code.append(lines[index])
                index += 1
            index += 1
            lang_class = f' class="language-{escape(language, quote=True)}"' if language else ""
            output.append(f"<pre><code{lang_class}>{escape(chr(10).join(code))}</code></pre>")
            continue

        if stripped.startswith("|"):
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            output.append(render_table(table_lines))
            continue

        if stripped.startswith(">"):
            quote_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                quote_lines.append(lines[index].strip().lstrip(">").strip())
                index += 1
            output.append(f'<div class="callout"><p>{inline(" ".join(quote_lines))}</p></div>')
            continue

        list_match = re.match(r"^([-*]|\d+\.)\s+(.+)$", stripped)
        if list_match:
            ordered = list_match.group(1)[0].isdigit()
            tag = "ol" if ordered else "ul"
            items: list[str] = []
            while index < len(lines):
                candidate = lines[index]
                match = re.match(r"^\s*([-*]|\d+\.)\s+(.+)$", candidate)
                if match:
                    if bool(match.group(1)[0].isdigit()) != ordered and not items:
                        break
                    items.append(match.group(2).strip())
                    index += 1
                    continue
                if items and candidate.startswith(("  ", "\t")) and candidate.strip() and not is_structural(candidate):
                    items[-1] += " " + candidate.strip()
                    index += 1
                    continue
                break
            output.append(f"<{tag}>" + "".join(f"<li>{inline(item)}</li>" for item in items) + f"</{tag}>")
            continue

        paragraph = [stripped]
        index += 1
        while index < len(lines) and not is_structural(lines[index]):
            paragraph.append(lines[index].strip())
            index += 1
        output.append(f"<p>{inline(' '.join(paragraph))}</p>")

    if intro_open:
        output.append("</div>")
    if section_open:
        output.append("</div></section>")
    return "\n".join(output), toc


def source_href(page: Page) -> str:
    return Path(ROOT / page.source).relative_to(OUTPUT, walk_up=True).as_posix()


def page_options(current: Page) -> str:
    options = []
    for page in PAGES:
        selected = " selected" if page == current else ""
        options.append(f'<option value="{page.output}"{selected}>{escape(page.short_title)}</option>')
    return "".join(options)


def neighbor(page: Page, offset: int) -> Page:
    index = PAGES.index(page)
    return PAGES[(index + offset) % len(PAGES)]


def render_page(page: Page) -> str:
    source = ROOT / page.source
    body, toc = markdown_body(source.read_text(encoding="utf-8"))
    toc_html = "".join(f'<a href="#{section_id}">{escape(title)}</a>' for section_id, title in toc)
    previous = neighbor(page, -1)
    following = neighbor(page, 1)
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{escape(page.summary, quote=True)}">
  <title>{escape(page.title)} · VALI Research Library</title>
  <link rel="stylesheet" href="library.css">
</head>
<body style="--accent:{page.accent};--accent-soft:{page.accent_soft}" data-page="{page.key}">
  <a class="skip-link" href="#document">Skip to document</a>
  <div class="reading-progress" aria-hidden="true"><span id="reading-progress"></span></div>
  <header class="topbar">
    <div class="topbar-inner">
      <a class="library-brand" href="VALI_EXPLORER.html"><span class="library-mark">V</span><span>VALI Explorer</span></a>
      <span class="topbar-divider" aria-hidden="true"></span>
      <span class="document-label">Research Library · {escape(page.short_title)}</span>
      <button class="toc-toggle" id="toc-toggle" type="button" aria-controls="doc-sidebar" aria-expanded="false">Contents</button>
      <label class="page-switcher-wrap"><span class="skip-link">Choose a library page</span><select class="page-switcher" id="page-switcher" aria-label="Choose a research library page">{page_options(page)}</select></label>
    </div>
  </header>
  <div class="page-shell">
    <aside class="doc-sidebar" id="doc-sidebar">
      <span class="doc-type">{escape(page.category)}</span>
      <h2 class="sidebar-title">{escape(page.short_title)}</h2>
      <p class="sidebar-summary">{escape(page.summary)}</p>
      <label class="search-label" for="section-search">Search this document</label>
      <input class="section-search" id="section-search" type="search" placeholder="Try “leakage” or “depth”">
      <p class="search-result" id="search-result">{len(toc)} sections</p>
      <p class="toc-heading">On this page</p>
      <nav class="toc" aria-label="Document sections">{toc_html}</nav>
      <div class="sidebar-actions">
        <button class="small-button" id="collapse-all" type="button">Collapse all</button>
        <a class="small-button" href="{source_href(page)}">View source .md</a>
      </div>
    </aside>
    <main class="document" id="document">
      <header class="doc-hero">
        <span class="hero-kicker">{escape(page.category)} · VALI Research Library</span>
        <h1>{escape(page.title)}</h1>
        <p>{escape(page.summary)}</p>
        <div class="hero-meta"><span class="meta-pill">{escape(page.status)}</span><span class="meta-pill">Public-data-only</span><span class="meta-pill">Research, not a trading claim</span></div>
      </header>
      {body}
      <nav class="page-neighbors" aria-label="Adjacent library pages">
        <a class="neighbor previous" href="{previous.output}"><small>Previous</small><b>← {escape(previous.short_title)}</b></a>
        <a class="neighbor next" href="{following.output}"><small>Next</small><b>{escape(following.short_title)} →</b></a>
      </nav>
      <footer class="claim-footer"><p><strong>Claim boundary:</strong> No empirical alpha claim. No trading-readiness claim. No private data, proprietary order flow, order submission, live trading, or <code>P_flow</code>.</p></footer>
    </main>
  </div>
  <noscript><style>.doc-sidebar{{display:block!important;position:static;max-height:none}}.section-body[hidden]{{display:block!important}}</style></noscript>
  <script src="library.js" defer></script>
</body>
</html>
'''


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for page in PAGES:
        (OUTPUT / page.output).write_text(render_page(page), encoding="utf-8")
        print(page.output)


if __name__ == "__main__":
    main()
