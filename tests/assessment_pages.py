"""Generate offline synthetic pages for the approval-expiry browser regression."""
import copy
import io
import sys
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import i18n  # noqa: E402
import market_scanner  # noqa: E402
import stock_compare  # noqa: E402
from framework_view import framework_panel  # noqa: E402
from test_assessment_integrity import AssessmentIntegrity, NOW, complete_row  # noqa: E402
from test_framework_contract import engine  # noqa: E402


def generate(destination):
    destination.mkdir(parents=True, exist_ok=True)
    helper = AssessmentIntegrity()
    rows, assessments = {}, {}
    for ticker in ('WKL', 'DIS'):
        row = engine._regime_fixture('Pharma', .3, 7, 8)
        row.update(complete_row())
        row['yf'] = ticker
        row['weight'] = 30. if ticker == 'WKL' else 20.
        row['held'] = True
        rows[ticker] = row
        assessments[ticker] = helper.assess(row, reviews=helper.reviewed(row))
    record = {ticker: dict(score=engine.score(row), assessment=assessments[ticker],
        diagnostics=dict(valuation_contract=dict(status='DECLARED', issues=[])),
        score_explanation=engine.score_components(row)) for ticker, row in rows.items()}
    record['_evidence'] = dict(captured_at=NOW.isoformat(), inputs=copy.deepcopy(rows), model_source_sha256='a'*64)
    with patch.object(engine, 'DATA', rows), patch.object(engine, 'sector_performance', return_value={'ok': False}), \
            patch.object(engine, 'forward_run', return_value={}), \
            patch.object(engine, 'regime_history', return_value=([], {})), redirect_stderr(io.StringIO()):
        html = engine.build_html(macro={'ok': False}, write=False, assessments=assessments)
        book = engine.portfolio_proposal('REFLATION', assessments=assessments)
        panel = framework_panel(rows, engine.W, {}, book)
    html = html.replace('<script id="assessment-data"', panel + '<script id="assessment-data"')
    for language in ('en', 'de', 'es'):
        (destination / f'index.{language}.html').write_text(i18n.localize(html, language), encoding='utf-8')
    notes = dict(schema_version=1, entries={'DIS': dict(objections=[
        dict(id='NEW', severity='major', status='open', message='Synthetic source conflict')])})
    scan = market_scanner.build_scan(record, as_of=NOW, notes=notes)
    (destination / 'scanner.html').write_text(market_scanner.render_scan(scan), encoding='utf-8')
    for path, content in stock_compare.site_pages(destination, {'record': record}, now=NOW):
        (destination / path).write_text(content, encoding='utf-8')


if __name__ == '__main__':
    generate(Path(sys.argv[1]))
