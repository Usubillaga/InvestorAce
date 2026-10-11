"""Build the weekly research pages alongside the last completed scoreboard.

No market requests, model changes or credentials are needed. The nightly build
requires a verified report; research-only releases also support the legacy
report until the first paired report/evidence generation has been committed.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import date
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from integrity import atomic_text

TOPICS = {
    'stock_selection': 'Stock selection',
    'valuation_reverse_dcf': 'Valuation / reverse DCF',
    'portfolio_construction': 'Portfolio construction',
    'macro_regimes': 'Macro regimes',
}
REVIEWS = {'code': 'Code review', 'framework': 'Framework review',
           'both': 'Code + framework review', 'neither': 'No review warranted'}
CONFIDENCE = {'Sicher', 'Wahrscheinlich', 'Vermutung'}

CSS = """
:root{color-scheme:dark;--bg:#0d0f14;--panel:#141821;--line:#2a3040;
--text:#edf0f7;--muted:#a0aabe;--accent:#c1d98b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:16px/1.6 Inter,system-ui,-apple-system,sans-serif}a{color:var(--accent);
text-underline-offset:4px}a:hover{color:#e2f1be}main{max-width:1060px;margin:auto;
padding:32px 24px 64px}nav{display:flex;gap:22px;flex-wrap:wrap;align-items:center;
padding-bottom:22px;border-bottom:1px solid var(--line)}nav strong{margin-right:auto;
font-size:18px;letter-spacing:-.5px}nav a{font-size:14px}.eyebrow{color:var(--accent);
font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase}
header{padding:48px 0 30px}h1{font-size:clamp(36px,6vw,62px);line-height:1.1;
letter-spacing:-2px;margin:14px 0 20px;max-width:800px}header p{max-width:700px;
color:var(--muted);font-size:18px}.topics{display:flex;gap:8px;flex-wrap:wrap}
.topic,.pill{font-size:12px;border:1px solid var(--line);border-radius:999px;
padding:4px 10px}.topic{color:var(--muted)}.layout{display:grid;
grid-template-columns:minmax(0,1fr) 240px;gap:28px}.issue-heading{margin:0 0 20px;
font-size:24px;letter-spacing:-.6px}.meta{font-size:13px;color:var(--muted)}
.summary{margin:0 0 24px;color:var(--muted)}article,.priority,.empty{background:var(--panel);
border:1px solid var(--line);border-radius:12px;padding:24px;margin-bottom:18px}
.card-top{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.number{color:var(--accent);
font-size:13px;font-weight:700;margin-right:auto}.pill{color:var(--accent)}
h2{font-size:22px;line-height:1.3;letter-spacing:-.5px;margin:16px 0 10px}
.source{overflow-wrap:anywhere}dl{margin:22px 0 0}dt{font-size:12px;
font-weight:700;color:var(--muted);letter-spacing:.5px;text-transform:uppercase}
dd{margin:5px 0 18px}dd:last-child{margin-bottom:0}.limitations{font-size:14px;
color:var(--muted)}aside{border-left:1px solid var(--line);padding-left:22px}
aside h2{font-size:15px;margin:4px 0 16px}aside ul{list-style:none;padding:0;
margin:0}aside li{padding:12px 0;border-bottom:1px solid var(--line)}
aside p{font-size:13px;color:var(--muted)}.priority h2{font-size:18px;margin:0 0 12px}
.priority{border-color:#465439}.empty h2{margin:0 0 12px}.empty p{color:var(--muted)}
footer{margin-top:40px;border-top:1px solid var(--line);padding-top:20px;
font-size:12px;color:var(--muted)}@media(max-width:760px){main{padding:22px 16px 44px}
.layout{grid-template-columns:1fr}aside{border-left:0;border-top:1px solid var(--line);
padding:22px 0 0}header{padding-top:32px}article{padding:20px}h1{letter-spacing:-1px}}
"""


def text_field(obj, key):
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{key} must be nonempty text')
    return value


def validate_issue(issue, filename):
    if not isinstance(issue, dict) or issue.get('schema_version') != 1:
        raise ValueError('Expected weekly research schema_version 1')
    stamp = date.fromisoformat(text_field(issue, 'issue_date'))
    if filename != f'{stamp.isoformat()}.json':
        raise ValueError('Issue date must match its filename')
    start = date.fromisoformat(text_field(issue, 'period_start'))
    end = date.fromisoformat(text_field(issue, 'period_end'))
    if not start <= end <= stamp:
        raise ValueError('Invalid research coverage period')
    for key in ('summary', 'priority_review'):
        text_field(issue, key)
    items = issue.get('items')
    if not isinstance(items, list) or len(items) > 5:
        raise ValueError('Each issue must contain zero to five items')
    urls = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('Research items must be objects')
        for key in ('title', 'authors', 'publication_date', 'what_changed',
                    'investorace_implication', 'review_question', 'limitations'):
            text_field(item, key)
        url = text_field(item, 'source_url')
        parsed = urlsplit(url)
        if (parsed.scheme not in ('https', 'http') or not parsed.hostname
                or parsed.username or parsed.password or re.search(r'\s', url)):
            raise ValueError('Source links must be public HTTP(S) URLs')
        if url in urls:
            raise ValueError('Duplicate source in the same issue')
        urls.add(url)
        if (not isinstance(item.get('review'), str) or item['review'] not in REVIEWS
                or not isinstance(item.get('confidence'), str) or item['confidence'] not in CONFIDENCE):
            raise ValueError('Invalid review verdict or confidence label')
        topics = item.get('topics')
        if (not isinstance(topics, list) or not topics
                or any(not isinstance(t, str) or t not in TOPICS for t in topics)
                or len(set(topics)) != len(topics)):
            raise ValueError('Use distinct supported research topics')
    return issue


def load_research(folder):
    config = json.loads((folder / 'config.json').read_text(encoding='utf-8'))
    date.fromisoformat(text_field(config, 'first_issue_date'))
    text_field(config, 'schedule_label')
    issues = [validate_issue(json.loads(p.read_text(encoding='utf-8')), p.name)
              for p in sorted(folder.glob('????-??-??.json'), reverse=True)]
    return config, issues


def card(item, index):
    e = escape
    topics = ''.join(f'<span class="topic">{e(TOPICS[t])}</span>' for t in item['topics'])
    fields = [('What changed', 'what_changed'), ('InvestorAce implication', 'investorace_implication'),
              ('Review question', 'review_question'), ('Evidence limits', 'limitations')]
    detail = ''
    for label, key in fields:
        style = ' class="limitations"' if key == 'limitations' else ''
        detail += f'<dt>{label}</dt><dd{style}>{e(item[key])}</dd>'
    return (f'<article><div class="card-top"><span class="number">{index:02d}</span>'
            f'<span class="pill">{e(REVIEWS[item["review"]])}</span>'
            f'<span class="meta">[{e(item["confidence"])}]</span></div>'
            f'<h2><a class="source" href="{e(item["source_url"], quote=True)}" '
            f'target="_blank" rel="noopener noreferrer">{e(item["title"])}</a></h2>'
            f'<p class="meta">{e(item["authors"])} · Published / revised {e(item["publication_date"])}</p>'
            f'<div class="topics">{topics}</div><dl>{detail}</dl></article>')


def render_page(issue, issues, config, archived=False):
    e = escape
    prefix = '../' if archived else ''
    topics = ''.join(f'<span class="topic">{e(t)}</span>' for t in TOPICS.values())
    archive = ''.join(f'<li><a href="{prefix}research/{x["issue_date"]}.html">'
                      f'{e(x["issue_date"])}</a><br><span class="meta">'
                      f'{len(x["items"])} selected source{"s" if len(x["items"]) != 1 else ""}'
                      '</span></li>' for x in issues)
    if issue is None:
        first = date.fromisoformat(config['first_issue_date']).strftime('%d %B %Y')
        content = ('<div class="empty"><div class="eyebrow">First edition</div>'
                   f'<h2>Scheduled for {e(first)}</h2><p>Each edition explains what changed, '
                   'why it matters for InvestorAce, and whether a code or framework review is warranted.</p>'
                   '<p>No edition has been published yet.</p></div>')
    else:
        content = (f'<h2 class="issue-heading">Edition · {e(issue["issue_date"])}</h2>'
                   f'<p class="meta">Coverage: {e(issue["period_start"])} → {e(issue["period_end"])}</p>'
                   f'<p class="summary">{e(issue["summary"])}</p>'
                   + ''.join(card(item, i) for i, item in enumerate(issue['items'], 1))
                   + ('' if issue['items'] else '<div class="empty">No qualifying new sources this period.</div>')
                   + f'<div class="priority"><h2>Priority review</h2><div>{e(issue["priority_review"])}</div></div>')
    title = 'Weekly Research' + (f' · {issue["issue_date"]}' if issue else '')
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>InvestorAce · {e(title)}</title><meta name="description" '
            'content="Weekly evidence and practical review ideas for the InvestorAce investment framework.">'
            f'<style>{CSS}</style></head><body><main><nav aria-label="Main navigation">'
            f'<strong>InvestorAce</strong><a href="{prefix}index.html">Scoreboard</a>'
            f'<a href="{prefix}research.html" aria-current="page">Weekly research</a></nav>'
            '<header><div class="eyebrow">The research notebook</div>'
            '<h1>Evidence worth reviewing.</h1><p>A concise shortlist of new research, '
            'with the practical consequences for InvestorAce made explicit.</p>'
            f'<div class="topics">{topics}</div></header><div class="layout"><section '
            f'aria-label="Research edition">{content}</section><aside><h2>Publishing schedule</h2>'
            f'<p>{e(config["schedule_label"])}</p><h2>Past editions</h2><ul>{archive}</ul>'
            '<p>Primary sources first. Up to five useful items. Quiet weeks stay short.</p></aside></div>'
            '<footer>Research ideas are review candidates. Published editions do not change stock scores, '
            'regime fit or portfolio rules. Not investment advice.</footer></main></body></html>')


def add_research_link(html):
    if 'id="investorace-research-nav"' in html:
        return html
    match = re.search(r'<body\b[^>]*>', html, re.IGNORECASE)
    if not match or not re.search(r'</html\s*>', html, re.IGNORECASE):
        raise ValueError('Scoreboard must be a complete HTML document')
    nav = ('<nav id="investorace-research-nav" aria-label="Research" '
           'style="margin:0 0 22px;padding:12px 16px;border:1px solid #2a3040;'
           'border-radius:10px;background:#141821;display:flex;gap:16px;flex-wrap:wrap">'
           '<a href="research.html" style="color:#c1d98b;font-weight:700">Weekly research ↗</a>'
           '<span style="color:#a0aabe;font-size:13px">New evidence · InvestorAce implications · Review priorities</span></nav>')
    return html[:match.end()] + nav + html[match.end():]


def build_site(root, output, require_committed=False):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output == root or output in (root / 'history', root / 'weekly-research'):
        raise ValueError('Use a separate site output directory')
    config, issues = load_research(root / 'weekly-research')
    pointer = root / 'history' / '_current.json'
    if pointer.exists() or require_committed:
        from evidence import current_build
        report = current_build(root / 'history')['report_path']
    else:
        report = root / 'index.html'
        print('Using the legacy scoreboard; no paired generation exists yet.')
    scoreboard = add_research_link(report.read_text(encoding='utf-8'))
    # Validate all content before creating an uploadable site.
    latest = render_page(issues[0] if issues else None, issues, config)
    archived = [(x['issue_date'], render_page(x, issues, config, archived=True)) for x in issues]
    output.mkdir(parents=True, exist_ok=True)
    atomic_text(output / 'index.html', scoreboard)
    atomic_text(output / 'research.html', latest)
    for stamp, page in archived:
        atomic_text(output / 'research' / f'{stamp}.html', page)
    if (root / 'tickers.js').exists():
        shutil.copyfile(root / 'tickers.js', output / 'tickers.js')
    print(f'Built research pages: {len(issues)} edition(s), output {output}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--output', type=Path, default=Path('public'))
    parser.add_argument('--require-committed-report', action='store_true')
    args = parser.parse_args()
    build_site(args.root, args.output, args.require_committed_report)


if __name__ == '__main__':
    main()
