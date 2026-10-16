"""Build separate Friday research and Monday market briefing pages.

No market requests, model changes or credentials are needed. The nightly build
requires a verified report; research-only releases also support the legacy
report until the first paired report/evidence generation has been committed.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter
from datetime import date
from decimal import Decimal
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

import i18n
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
LANGUAGES = {'es': 'Español', 'en': 'English', 'de': 'Deutsch'}
TRANSLATED_FIELDS = ('title', 'publication_date', 'what_changed',
                     'investorace_implication', 'review_question', 'limitations')

LOCALES = {
    'en': {
        'title': 'Weekly Research', 'nav': 'Friday research',
        'eyebrow': 'The research notebook', 'heading': 'Evidence worth reviewing.',
        'description': 'A concise shortlist of new research, with the practical consequences for InvestorAce made explicit.',
        'scoreboard': 'Scoreboard', 'market': 'Monday briefing', 'navigation': 'Main navigation',
        'language': 'Language', 'edition': 'Edition', 'coverage': 'Coverage',
        'published': 'Published / revised', 'original': 'Original source title',
        'fields': ('What changed', 'InvestorAce implication', 'Review question', 'Evidence limits'),
        'schedule': 'Publishing schedule', 'past': 'Past editions',
        'sources': ('selected source', 'selected sources'), 'priority': 'Priority review',
        'empty': 'No qualifying new sources this period.', 'first': 'First edition',
        'scheduled': 'Scheduled for', 'unpublished': 'No edition has been published yet.',
        'intro': 'Each edition explains what changed, why it matters for InvestorAce, and whether a code or framework review is warranted.',
        'policy': 'Primary sources first. Up to five useful items. Quiet weeks stay short.',
        'footer': 'Research ideas are review candidates. Published editions do not change stock scores, regime fit or portfolio rules. Not investment advice.',
        'topics': TOPICS, 'reviews': REVIEWS,
        'confidence': {'Sicher': 'Certain', 'Wahrscheinlich': 'Likely', 'Vermutung': 'Speculative'},
    },
    'es': {
        'title': 'Investigación semanal', 'nav': 'Investigación del viernes',
        'eyebrow': 'El cuaderno de investigación', 'heading': 'Evidencia que merece una revisión.',
        'description': 'Una selección concisa de nuevas investigaciones y sus consecuencias prácticas para InvestorAce.',
        'scoreboard': 'Panel de acciones', 'market': 'Informe del lunes', 'navigation': 'Navegación principal',
        'language': 'Idioma', 'edition': 'Edición', 'coverage': 'Periodo analizado',
        'published': 'Publicado / revisado', 'original': 'Título original de la fuente',
        'fields': ('Qué cambió', 'Implicación para InvestorAce', 'Pregunta de revisión', 'Limitaciones de la evidencia'),
        'schedule': 'Calendario de publicación', 'past': 'Ediciones anteriores',
        'sources': ('fuente seleccionada', 'fuentes seleccionadas'), 'priority': 'Revisión prioritaria',
        'empty': 'No se encontraron nuevas fuentes pertinentes en este periodo.', 'first': 'Primera edición',
        'scheduled': 'Programada para', 'unpublished': 'Todavía no se ha publicado ninguna edición.',
        'intro': 'Cada edición explica qué cambió, por qué importa para InvestorAce y si conviene revisar el código o el marco de inversión.',
        'policy': 'Primero las fuentes originales. Hasta cinco aportaciones útiles. Las semanas tranquilas se resumen brevemente.',
        'footer': 'Las ideas de investigación son propuestas de revisión. Las ediciones publicadas no cambian las puntuaciones, la afinidad con el régimen ni las reglas de cartera. No constituye asesoramiento de inversión.',
        'topics': {'stock_selection': 'Selección de acciones', 'valuation_reverse_dcf': 'Valoración / DCF inverso',
                   'portfolio_construction': 'Construcción de carteras', 'macro_regimes': 'Regímenes macroeconómicos'},
        'reviews': {'code': 'Revisar el código', 'framework': 'Revisar el marco',
                    'both': 'Revisar código y marco', 'neither': 'Sin revisión necesaria'},
        'confidence': {'Sicher': 'Seguro', 'Wahrscheinlich': 'Probable', 'Vermutung': 'Suposición'},
    },
    'de': {
        'title': 'Wöchentliche Forschung', 'nav': 'Freitagsrecherche',
        'eyebrow': 'Das Forschungsnotizbuch', 'heading': 'Evidenz, die eine Prüfung verdient.',
        'description': 'Eine kompakte Auswahl neuer Forschung mit konkreten Folgen für InvestorAce.',
        'scoreboard': 'Aktienübersicht', 'market': 'Montagsbriefing', 'navigation': 'Hauptnavigation',
        'language': 'Sprache', 'edition': 'Ausgabe', 'coverage': 'Berichtszeitraum',
        'published': 'Veröffentlicht / überarbeitet', 'original': 'Originaltitel der Quelle',
        'fields': ('Was hat sich geändert?', 'Bedeutung für InvestorAce', 'Konkrete Prüffrage', 'Grenzen der Evidenz'),
        'schedule': 'Veröffentlichungsplan', 'past': 'Frühere Ausgaben',
        'sources': ('ausgewählte Quelle', 'ausgewählte Quellen'), 'priority': 'Priorisierte Prüfung',
        'empty': 'In diesem Zeitraum gab es keine geeigneten neuen Quellen.', 'first': 'Erste Ausgabe',
        'scheduled': 'Geplant für', 'unpublished': 'Es wurde noch keine Ausgabe veröffentlicht.',
        'intro': 'Jede Ausgabe erklärt, was sich geändert hat, warum das für InvestorAce relevant ist und ob Code oder Investmentrahmen geprüft werden sollten.',
        'policy': 'Primärquellen zuerst. Bis zu fünf nützliche Beiträge. Ruhige Wochen bleiben kurz.',
        'footer': 'Forschungsideen sind Vorschläge zur Prüfung. Veröffentlichte Ausgaben ändern weder Aktienbewertungen noch Regime-Fit oder Portfolioregeln. Keine Anlageberatung.',
        'topics': {'stock_selection': 'Aktienauswahl', 'valuation_reverse_dcf': 'Bewertung / Reverse DCF',
                   'portfolio_construction': 'Portfoliokonstruktion', 'macro_regimes': 'Makroregime'},
        'reviews': {'code': 'Code prüfen', 'framework': 'Investmentrahmen prüfen',
                    'both': 'Code und Investmentrahmen prüfen', 'neither': 'Keine Prüfung erforderlich'},
        'confidence': {'Sicher': 'Sicher', 'Wahrscheinlich': 'Wahrscheinlich', 'Vermutung': 'Vermutung'},
    },
}

SERIES = {
    'research': {
        'folder': 'weekly-research', 'page': 'research.html', 'archive': 'research',
        'title': 'Weekly Research', 'nav': 'Friday research', 'lang': 'en',
        'eyebrow': 'The research notebook', 'heading': 'Evidence worth reviewing.',
        'description': 'A concise shortlist of new research, with the practical consequences for InvestorAce made explicit.',
    },
    'market': {
        'folder': 'market-briefings', 'page': 'market.html', 'archive': 'market',
        'title': 'Montagsbriefing', 'nav': 'Montagsbriefing', 'lang': 'de',
        'eyebrow': 'Montag · Marktbriefing', 'heading': 'Die Marktwoche im Blick.',
        'description': 'Makro-Regime, Bewertung, Sektoren und Gewinne: Was hat sich verändert und was sollte InvestorAce überprüfen?',
    },
}

MARKET_LOCALES = {
    'en': {'title': 'Monday Market Briefing', 'eyebrow': 'Monday · Market briefing',
           'heading': 'The market week in focus.',
           'description': 'Macro regimes, valuations, sectors and earnings: what changed and what should InvestorAce review?'},
    'es': {'title': 'Informe de mercado del lunes', 'eyebrow': 'Lunes · Informe de mercado',
           'heading': 'La semana bursátil en perspectiva.',
           'description': 'Regímenes macroeconómicos, valoraciones, sectores y beneficios: qué ha cambiado y qué debe revisar InvestorAce.'},
    'de': {'title': 'Montagsbriefing', 'eyebrow': 'Montag · Marktbriefing',
           'heading': 'Die Marktwoche im Blick.',
           'description': 'Makro-Regime, Bewertung, Sektoren und Gewinne: Was hat sich verändert und was sollte InvestorAce überprüfen?'},
}

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
dd{margin:5px 0 18px;overflow-wrap:anywhere}dd:last-child{margin-bottom:0}.limitations{font-size:14px;
color:var(--muted)}aside{border-left:1px solid var(--line);padding-left:22px}
aside h2{font-size:15px;margin:4px 0 16px}aside ul{list-style:none;padding:0;
margin:0}aside li{padding:12px 0;border-bottom:1px solid var(--line)}
aside p{font-size:13px;color:var(--muted)}.priority h2{font-size:18px;margin:0 0 12px}
.priority{border-color:#465439}.empty h2{margin:0 0 12px}.empty p{color:var(--muted)}
.languages{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:24px;
font-size:14px}.languages a{padding:5px 12px;border:1px solid var(--line);
border-radius:999px;text-decoration:none}.languages a[aria-current="page"]{
background:#293521;border-color:#73854f;color:#e2f1be}
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


def numeric_claims(text):
    claims = []
    for match in re.finditer(r'[+−-]?\d+(?:[.,]\d+)?', text):
        token = match.group().replace('−', '-').replace(',', '.')
        if token.startswith('-') and match.start() and text[match.start() - 1].isalnum():
            token = token[1:]
        claims.append(Decimal(token))
    return Counter(claims)


def check_translated_claims(original, translated, keys):
    tags = r'\[(Sicher|Wahrscheinlich|Vermutung)\]'
    for key in keys:
        if Counter(re.findall(tags, original[key])) != Counter(re.findall(tags, translated[key])):
            raise ValueError(f'Translated confidence labels differ: {key}')
        if numeric_claims(original[key]) != numeric_claims(translated[key]):
            raise ValueError(f'Translated numeric claims differ: {key}')


def validate_issue(issue, filename, required_languages=('en',), verify_translation_claims=False):
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
    translations = issue.get('translations', {})
    if not isinstance(translations, dict) or set(translations) - {'es', 'de'}:
        raise ValueError('Translations support Spanish (es) and German (de); English is the base edition')
    for language in required_languages:
        if language != 'en' and language not in translations:
            raise ValueError(f'Missing required {language} translation')
    for language, translated in translations.items():
        if not isinstance(translated, dict) or set(translated) != {'summary', 'priority_review', 'items'}:
            raise ValueError(f'Invalid {language} translation fields')
        text_field(translated, 'summary')
        text_field(translated, 'priority_review')
        if verify_translation_claims:
            check_translated_claims(issue, translated, ('summary', 'priority_review'))
        if not isinstance(translated['items'], list) or len(translated['items']) != len(items):
            raise ValueError(f'{language} translation must cover the same items in the same order')
        for original, translated_item in zip(items, translated['items']):
            required = set(TRANSLATED_FIELDS) | {'source_url'}
            optional = {'authors'} if verify_translation_claims else set()
            if (not isinstance(translated_item, dict)
                    or not required <= set(translated_item)
                    or set(translated_item) - required - optional):
                raise ValueError(f'Invalid {language} item translation fields')
            if translated_item['source_url'] != original['source_url']:
                raise ValueError('Translations must preserve source links and item order')
            for key in TRANSLATED_FIELDS:
                text_field(translated_item, key)
            if 'authors' in translated_item:
                text_field(translated_item, 'authors')
            if verify_translation_claims:
                check_translated_claims(original, translated_item,
                                        tuple(k for k in translated_item if k != 'source_url'))
    return issue


def load_research(folder):
    config = json.loads((folder / 'config.json').read_text(encoding='utf-8'))
    date.fromisoformat(text_field(config, 'first_issue_date'))
    text_field(config, 'schedule_label')
    languages = config.get('languages', ['en'])
    if (not isinstance(languages, list) or not languages
            or any(not isinstance(lang, str) or lang not in LANGUAGES for lang in languages)
            or 'en' not in languages or len(set(languages)) != len(languages)):
        raise ValueError('languages must contain English and distinct supported language codes')
    schedules = config.get('schedule_labels', {})
    if not isinstance(schedules, dict):
        raise ValueError('schedule_labels must be an object')
    for language in languages:
        if language != 'en':
            text_field(schedules, language)
    verify = config.get('verify_translation_claims', False)
    if not isinstance(verify, bool):
        raise ValueError('verify_translation_claims must be a boolean')
    if 'default_language' in config and config['default_language'] not in languages:
        raise ValueError('default_language must be one of the configured languages')
    issues = [validate_issue(json.loads(p.read_text(encoding='utf-8')), p.name, languages, verify)
              for p in sorted(folder.glob('????-??-??.json'), reverse=True)]
    return config, issues


def display_text(value, language):
    for label, translated in (LOCALES[language]['confidence'].items() if language else ()):
        value = value.replace(f'[{label}]', f'[{translated}]')
    return escape(value)


def localized_issue(issue, language):
    if issue is None or language == 'en':
        return issue
    translated = issue['translations'][language]
    items = [{**original, **text, 'original_title': original['title']}
             for original, text in zip(issue['items'], translated['items'])]
    return {**issue, 'summary': translated['summary'],
            'priority_review': translated['priority_review'], 'items': items}


def research_path(stamp=None, language='en'):
    suffix = '' if language == 'en' else f'-{language}'
    return f'research/{stamp}{suffix}.html' if stamp else f'research{suffix}.html'


def page_path(series, stamp=None, language='en'):
    if series == 'research':
        return research_path(stamp, language or 'en')
    settings = SERIES[series]
    suffix = f'-{language}' if language else ''
    return (f'{settings["archive"]}/{stamp}{suffix}.html' if stamp
            else f'{Path(settings["page"]).stem}{suffix}.html')


def card(item, index, language='en', translate_confidence=True):
    e = escape
    labels = LOCALES[language]
    topics = ''.join(f'<span class="topic">{e(labels["topics"][t])}</span>' for t in item['topics'])
    fields = zip(labels['fields'], ('what_changed', 'investorace_implication',
                                   'review_question', 'limitations'))
    detail = ''
    for label, key in fields:
        style = ' class="limitations"' if key == 'limitations' else ''
        detail += f'<dt>{e(label)}</dt><dd{style}>{display_text(item[key], language if translate_confidence else None)}</dd>'
    original = (f'<p class="meta">{e(labels["original"])}: {e(item["original_title"])}</p>'
                if item.get('original_title') else '')
    confidence = labels['confidence'][item['confidence']] if translate_confidence else item['confidence']
    return (f'<article><div class="card-top"><span class="number">{index:02d}</span>'
            f'<span class="pill">{e(labels["reviews"][item["review"]])}</span>'
            f'<span class="meta">[{e(confidence)}]</span></div>'
            f'<h2><a class="source" href="{e(item["source_url"], quote=True)}" '
            f'target="_blank" rel="noopener noreferrer">{e(item["title"])}</a></h2>'
            f'{original}<p class="meta">{e(item["authors"])} · {e(labels["published"])} {e(item["publication_date"])}</p>'
            f'<div class="topics">{topics}</div><dl>{detail}</dl></article>')


def render_page(issue, issues, config, archived=False, series='research', language=None,
                multilingual_series=()):
    e = escape
    settings = SERIES[series]
    path_language = language
    language = language or config.get('default_language', settings['lang'])
    labels = {**LOCALES[language], **(MARKET_LOCALES[language] if series == 'market' else {})}
    if series == 'research' or (issue and issue.get('translations')):
        issue = localized_issue(issue, language)
    prefix = '../' if archived else ''
    topics = ''.join(f'<span class="topic">{e(t)}</span>' for t in labels['topics'].values())
    archive = ''.join(f'<li><a href="{prefix}{page_path(series, x["issue_date"], path_language)}">'
                      f'{e(x["issue_date"])}</a><br><span class="meta">'
                      f'{len(x["items"])} {e(labels["sources"][len(x["items"]) != 1])}'
                      '</span></li>' for x in issues)
    if issue is None:
        first = (date.fromisoformat(config['first_issue_date']).strftime('%d %B %Y')
                 if language == 'en' else config['first_issue_date'])
        content = (f'<div class="empty"><div class="eyebrow">{e(labels["first"])}</div>'
                   f'<h2>{e(labels["scheduled"])} {e(first)}</h2><p>{e(labels["intro"])}</p>'
                   f'<p>{e(labels["unpublished"])}</p></div>')
    else:
        content = (f'<h2 class="issue-heading">{e(labels["edition"])} · {e(issue["issue_date"])}</h2>'
                   f'<p class="meta">{e(labels["coverage"])}: {e(issue["period_start"])} → {e(issue["period_end"])}</p>'
                   f'<p class="summary">{display_text(issue["summary"], language)}</p>'
                   + ''.join(card(item, i, language) for i, item in enumerate(issue['items'], 1))
                   + ('' if issue['items'] else f'<div class="empty">{e(labels["empty"])}</div>')
                   + f'<div class="priority"><h2>{e(labels["priority"])}</h2><div>{display_text(issue["priority_review"], language)}</div></div>')
    title = labels['title'] + (f' · {issue["issue_date"]}' if issue else '')
    navigation = ''
    for key in SERIES:
        label = labels['nav'] if key == 'research' else labels['market']
        current = ' aria-current="page"' if key == series else ''
        nav_language = path_language if key == series else language if key in multilingual_series else None
        navigation += f'<a href="{prefix}{page_path(key, language=nav_language)}"{current}>{e(label)}</a>'
    language_links = ''
    if len(config.get('languages', ['en'])) > 1:
        links = ''.join(f'<a href="{prefix}{page_path(series, issue["issue_date"] if archived and issue else None, lang)}" '
                        f'lang="{lang}" hreflang="{lang}"'
                        + (' aria-current="page"' if lang == language else '')
                        + f'>{e(LANGUAGES[lang])}</a>' for lang in config['languages'])
        language_links = f'<div class="languages" aria-label="{e(labels["language"])}">{e(labels["language"])}: {links}</div>'
    return (f'<!DOCTYPE html><html lang="{language}"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>InvestorAce · {e(title)}</title><meta name="description" '
            f'content="{e(labels["description"], quote=True)}">'
            f'<style>{CSS}</style></head><body><main><nav aria-label="{e(labels["navigation"])}">'
            f'<strong>InvestorAce</strong><a href="{prefix}{i18n.homepage(language)}">{e(labels["scoreboard"])}</a>'
            f'{navigation}</nav><header><div class="eyebrow">{e(labels["eyebrow"])}</div>'
            f'<h1>{e(labels["heading"])}</h1><p>{e(labels["description"])}</p>'
            f'<div class="topics">{topics}</div>{language_links}</header><div class="layout"><section '
            f'aria-label="{e(labels["edition"])}">{content}</section><aside><h2>{e(labels["schedule"])}</h2>'
            f'<p>{e(config.get("schedule_labels", {}).get(language, config["schedule_label"]))}</p>'
            f'<h2>{e(labels["past"])}</h2><ul>{archive}</ul>'
            f'<p>{e(labels["policy"])}</p></aside></div><footer>{e(labels["footer"])}</footer></main></body></html>')


def add_research_link(html):
    match = re.search(r'<body\b[^>]*>', html, re.IGNORECASE)
    if not match or not re.search(r'</html\s*>', html, re.IGNORECASE):
        raise ValueError('Scoreboard must be a complete HTML document')
    nav = ('<nav id="investorace-research-nav" aria-label="Research" '
           'style="margin:0 0 22px;padding:12px 16px;border:1px solid #2a3040;'
           'border-radius:10px;background:#141821;display:flex;gap:16px;flex-wrap:wrap">'
           '<a href="market.html" style="color:#c1d98b;font-weight:700">Montagsbriefing ↗</a>'
           '<a href="research.html" style="color:#c1d98b;font-weight:700">Friday research ↗</a></nav>')
    # Upgrade the old one-link navigation too; repeated builds stay idempotent.
    pattern = r'<nav\b[^>]*\bid=["\']investorace-research-nav["\'][^>]*>.*?</nav>'
    updated, count = re.subn(pattern, lambda _: nav, html, count=1, flags=re.IGNORECASE | re.DOTALL)
    if count:
        return updated
    return html[:match.end()] + nav + html[match.end():]


def market_redirects(config, market_issues, research_issues):
    """Preserve links to migrated editions without listing them in Friday's feed."""
    stamps = config.get('legacy_research_dates', [])
    if not isinstance(stamps, list) or any(not isinstance(s, str) for s in stamps):
        raise ValueError('legacy_research_dates must be a list of ISO dates')
    if len(set(stamps)) != len(stamps):
        raise ValueError('Duplicate legacy research date')
    market_dates = {x['issue_date'] for x in market_issues}
    research_dates = {x['issue_date'] for x in research_issues}
    pages = []
    for stamp in stamps:
        date.fromisoformat(stamp)
        if stamp not in market_dates or stamp in research_dates:
            raise ValueError('Legacy redirect must refer only to a market edition')
        target = f'../market/{stamp}.html'
        page = ('<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">'
                f'<meta http-equiv="refresh" content="0;url={target}">'
                f'<link rel="canonical" href="{target}">'
                '<title>InvestorAce · Montagsbriefing</title></head><body>'
                f'<p>Diese Ausgabe gehört zum <a href="{target}">Montagsbriefing</a>.</p>'
                '</body></html>')
        pages.append((Path('research') / f'{stamp}.html', page))
    return pages


def build_site(root, output, require_committed=False):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output == root or output in (root / 'history', root / 'weekly-research',
                                   root / 'market-briefings'):
        raise ValueError('Use a separate site output directory')
    config, issues = load_research(root / 'weekly-research')
    collections = [('research', config, issues)]
    market_folder = root / 'market-briefings'
    if market_folder.exists():
        market_config, market_issues = load_research(market_folder)
        collections.append(('market', market_config, market_issues))
    pointer = root / 'history' / '_current.json'
    if pointer.exists() or require_committed:
        from evidence import current_build
        report = current_build(root / 'history')['report_path']
    else:
        report = root / 'index.html'
        print('Using the legacy scoreboard; no paired generation exists yet.')
    scoreboard = add_research_link(report.read_text(encoding='utf-8'))
    # Translate the verified canonical report; never re-fetch or recalculate it.
    # Prepare every variant before replacing any previously published page.
    scoreboards = [(Path(i18n.homepage(language)), i18n.localize(scoreboard, language))
                   for language in ('en', 'de', 'es')]
    # Validate all content before creating an uploadable site.
    pages = []
    multilingual_series = {series for series, cfg, _ in collections
                           if len(cfg.get('languages', ['en'])) > 1}
    for series, series_config, series_issues in collections:
        languages = (series_config.get('languages', ['en']) if series == 'research'
                     else [None] + series_config.get('languages', []))
        for language in languages:
            latest = render_page(series_issues[0] if series_issues else None,
                                 series_issues, series_config, series=series, language=language,
                                 multilingual_series=multilingual_series)
            path = page_path(series, language=language)
            pages.append((Path(path), latest))
            pages.extend((Path(page_path(series, x['issue_date'], language)),
                          render_page(x, series_issues, series_config, archived=True,
                                      series=series, language=language,
                                      multilingual_series=multilingual_series)) for x in series_issues)
    if market_folder.exists():
        pages.extend(market_redirects(market_config, market_issues, issues))
    output.mkdir(parents=True, exist_ok=True)
    for path, page in scoreboards + pages:
        atomic_text(output / path, page)
    if (root / 'tickers.js').exists():
        shutil.copyfile(root / 'tickers.js', output / 'tickers.js')
    count = sum(len(x[2]) for x in collections)
    print(f'Built briefing pages: {count} edition(s) in {len(collections)} series, output {output}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--output', type=Path, default=Path('public'))
    parser.add_argument('--require-committed-report', action='store_true')
    args = parser.parse_args()
    build_site(args.root, args.output, args.require_committed_report)


if __name__ == '__main__':
    main()
