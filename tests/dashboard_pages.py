"""Render before/after UI from identical committed facts, without network calls.

python tests/dashboard_pages.py BASE_COMMIT output-directory
Then set DASHBOARD_BEFORE=output-directory/before and DASHBOARD_AFTER=.../after.
"""
import copy
import io
import subprocess
import sys
import types
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import engine  # noqa: E402
import evidence  # noqa: E402
import i18n  # noqa: E402
import weekly_research  # noqa: E402


def generate(before_ref, destination):
    sha = subprocess.check_output(['git', 'rev-parse', '--verify', '--end-of-options',
                                   before_ref + '^{commit}'], cwd=ROOT, text=True).strip()
    source = subprocess.check_output(['git', 'show', sha + ':engine.py'], cwd=ROOT, text=True)
    baseline = types.ModuleType('dashboard_baseline_engine')
    baseline.__file__ = str(ROOT / 'engine.py')
    exec(compile(source, baseline.__file__, 'exec'), baseline.__dict__)
    record = evidence.current_build(ROOT / 'history')['record']
    rows = record['_evidence']['inputs']
    rates = record.get('_rates') or {}
    for name, module in [('before', baseline), ('after', engine)]:
        if rates.get('risk_free'):
            module.WACC.set_risk_free(rates['risk_free'], rates.get('source'), rates.get('asof'))
            module.LIVE_10Y = rates.get('live_10y')
        with patch.object(module, 'DATA', copy.deepcopy(rows)), \
             patch.object(module, 'sector_performance', return_value={}), \
             patch.object(module, 'regime_history', return_value=([], {})), \
             patch.object(module, 'forward_run', return_value={
                 'ok': False, 'note': 'no frozen cohort yet; build a validated snapshot first'}), \
             redirect_stderr(io.StringIO()):
            html = module.build_html(macro=record['_evidence']['macro'], write=False,
                assessments={t: record[t]['assessment'] for t in rows})
        html = weekly_research.add_research_link(html, include_daily=True, include_claude=True,
            include_scanner=True, include_comparison=True, include_enagas=True)
        folder = destination / name
        folder.mkdir(parents=True, exist_ok=True)
        for language in ('en', 'de', 'es'):
            (folder / f'index.{language}.html').write_text(i18n.localize(html, language), encoding='utf-8')
    print(f'Rendered before/after: {len(rows)} companies, three languages, no network calls')


if __name__ == '__main__':
    generate(sys.argv[1], Path(sys.argv[2]))
