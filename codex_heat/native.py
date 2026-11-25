"""Publish the dated paper journals as an in-document InvestorAce tab."""
import json
import re
import subprocess
from dataclasses import dataclass
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen

DIR = Path(__file__).resolve().parent
REPO = 'Usubillaga/InvestorAce-Tradingdesk'
FILES = ('heat-account.json', 'heat-overlap.json')
JS = ('panic-alert.js', 'heat-paper-i18n.js', 'heat-paper-model.js', 'paper-panel.js', 'paper-tabs.js')
LABELS = {'es': ('Panel principal', 'Pánico · Cuentas en papel', 'Cuentas de Claude'),
          'de': ('Übersicht', 'Panik · Paper-Konten', 'Claudes Konten'),
          'en': ('Dashboard', 'Panic · Paper accounts', 'Claude’s accounts')}
HOME = {'es': 'index.es.html', 'de': 'index.de.html', 'en': 'index.html'}


def fetch_json(url):
    with urlopen(Request(url, headers={'User-Agent': 'InvestorAce-paper-publication'}), timeout=8) as response:
        return json.load(response)


def load_data(root, refresh):
    snapshots = [json.loads((DIR / name).read_text()) for name in FILES]
    if refresh:
        try:
            revision = fetch_json(f'https://api.github.com/repos/{REPO}/git/ref/heads/main')['object']['sha']
            if not re.fullmatch('[0-9a-f]{40}', revision):
                raise ValueError('invalid revision')
            pair = [fetch_json(f'https://raw.githubusercontent.com/{REPO}/{revision}/dist/{name}') for name in FILES]
            if (not all(isinstance(x, dict) and x.get('schema') == 1 and x['as_of'] >= prev['as_of']
                        for x, prev in zip(pair, snapshots)) or not isinstance(pair[0]['history'], list)
                    or not isinstance(pair[1]['books'], dict) or set(pair[1]['books']) != {'5', '6'}):
                raise ValueError('unexpected paper ledger schema or date')
            for size, book in pair[1]['books'].items():
                if not isinstance(book, dict) or not isinstance(book.get('holdings'), list):
                    raise ValueError(f'missing or invalid holdings list for the {size}-company account')
            snapshots = pair
        except (OSError, KeyError, TypeError, ValueError) as exc:
            print(f'Using dated bundled paper journals: {exc}')
    refs = []
    for name in ('index-leaders', 'index-leaders-17', 'index-leaders-17-spcx-ant'):
        path = root / 'paper_trades' / (name + '.json')
        if not path.is_file():
            # A partial site fixture must not manufacture comparison accounts.
            refs = []
            break
        try:
            account = json.loads(path.read_text())
            marks = account.get('marks') or []
            refs.append({k: account.get(k) for k in ('capital', 'cash', 'currency', 'level', 'basket_spec')}
                        | {'marks': marks[-1:]})
        except (OSError, ValueError, AttributeError, TypeError):
            refs = []
            break
    return dict(original=snapshots[0], overlap=snapshots[1], claude=refs)


@dataclass
class Panel:
    data: dict
    languages: dict

    @classmethod
    def build(cls, root, refresh=False):
        data = load_data(root, refresh)
        run = subprocess.run(['node', str(DIR / 'paper-panel.js')], input=json.dumps(data),
                             text=True, capture_output=True, check=True)
        return cls(data, json.loads(run.stdout))

    def embed(self, document, language, leader_page=False, round2_html=None, radar_html=None):
        """Apply after localization, so archived report HTML stays untouched."""
        primary, paper, claude = LABELS[language]
        primary = claude if leader_page else primary
        controls = (f'<div class="ia-paper-tabs" role="tablist" aria-label="InvestorAce">'
                    f'<button type="button" id="ia-primary-tab" role="tab" aria-selected="true" '
                    f'aria-controls="ia-primary">{primary}</button>'
                    f'<button type="button" id="ia-paper-tab" role="tab" aria-selected="false" tabindex="-1" '
                    f'aria-controls="panic-paper">{paper}</button></div>')
        round2_panel = ''
        if round2_html is not None:
            title = {'en': 'Paper round 2', 'de': 'Paper-Runde 2', 'es': 'Ronda de papel 2'}[language]
            switch = (f'<button type="button" id="ia-round2-tab" role="tab" aria-selected="false" tabindex="-1" '
                      f'aria-controls="paper-round2">{title}</button>')
            controls = controls.removesuffix('</div>') + switch + '</div>'
            links = ' · '.join(f'<a href="{home}#paper-round2" hreflang="{code}">{label}</a>'
                               for (code, home), label in zip(HOME.items(), ('Español', 'Deutsch', 'English')))
            round2_panel = (f'<section id="paper-round2" aria-labelledby="ia-round2-tab" role="tabpanel" tabindex="0">'
                            f'<nav class="ia-pp-lang">{links}</nav>{round2_html}</section>')
            document = document.replace('</head>', '<link rel="stylesheet" href="round2.css"></head>', 1)
        radar_panel = ''
        if radar_html is not None:
            title = {'en': '52-week radar', 'de': '52-Wochen-Radar', 'es': 'Radar de 52 semanas'}[language]
            switch = (f'<button type="button" id="ia-radar-tab" role="tab" aria-selected="false" tabindex="-1" '
                      f'aria-controls="low-radar">{title}</button>')
            controls = controls.removesuffix('</div>') + switch + '</div>'
            radar_panel = (f'<section id="low-radar" aria-labelledby="ia-radar-tab" role="tabpanel" tabindex="0">'
                           f'{radar_html}</section>')
            document = document.replace('</head>', '<link rel="stylesheet" href="low-radar.css"></head>', 1)
        langs = ' · '.join(f'<a href="{home}#panic-paper" hreflang="{code}" lang="{code}"'
                           + (' aria-current="true"' if code == language else '') + f'>{label}</a>'
                           for (code, home), label in zip(HOME.items(), ('Español', 'Deutsch', 'English')))
        state = json.dumps(self.data, ensure_ascii=True, separators=(',', ':')).replace('<', '\\u003c')
        panel = (f'<section id="panic-paper" class="ia-pp" data-language="{language}" role="tabpanel" '
                 f'aria-labelledby="ia-paper-tab" tabindex="0"><nav class="ia-pp-lang">{langs}</nav>'
                 f'<ia-panic-alert lang="{language}"></ia-panic-alert><div data-paper-content>{self.languages[language]}</div></section>'
                 f'<script type="application/json" id="ia-paper-data">{state}</script>'
                 '<script defer src="panic-paper.js"></script>')
        document = document.replace('</head>', '<link rel="stylesheet" href="panic-paper.css"></head>', 1)
        body = re.search(r'<body\b[^>]*>', document, re.I)
        closing = document.lower().rindex('</body>')
        return (document[:body.end()] + '<div class="ia-paper-shell">' + controls + f'<noscript><a href="#ia-primary">{primary}</a> · <a href="#panic-paper">{paper}</a></noscript>'
                + '<div role="tabpanel" aria-labelledby="ia-primary-tab" id="ia-primary">'
                + document[body.end():closing] + '</div>' + panel + round2_panel + radar_panel + '</div>' + document[closing:])

    def assets(self):
        yield Path('panic-paper.js'), '\n'.join((DIR / name).read_text() for name in JS)
        yield Path('panic-paper.css'), (DIR / 'paper-tabs.css').read_text()
        for name in ('heat-comparison.html', 'heat-comparison.en.html', 'heat-comparison.de.html',
                     'heat-comparison.css', 'heat-comparison-events.csv', 'heat-study.json'):
            yield Path(name), (DIR / name).read_bytes()
        for lang in ('', '.en'):
            yield Path('heat-archive' + lang + '.html'), (DIR / ('heat-archive' + lang + '.html')).read_bytes()
        for key, name in zip(('original', 'overlap'), FILES):
            yield Path(name), json.dumps(self.data[key], ensure_ascii=False)
        for name, lang in [('heat-leaders.html', 'es'), ('heat-leaders.en.html', 'en'), ('heat-overlap.html', 'de')]:
            target = HOME[lang] + '#panic-paper'
            yield Path(name), ('<!doctype html><html lang="' + lang + '"><meta charset="utf-8">'
                               '<title>InvestorAce · Paper</title><link rel="canonical" href="' + target + '">'
                               '<script src="panic-bookmark.js"></script><meta http-equiv="refresh" content="0;url='
                               + target + '"><p><a href="' + target + '">' + escape(LABELS[lang][1]) + '</a></p></html>')
        yield Path('panic-bookmark.js'), (DIR / 'panic-bookmark.js').read_text()
