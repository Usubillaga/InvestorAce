"""Automatic daily report and data-status pages (no network)."""
import unittest
from datetime import datetime, timezone
from pathlib import Path

import daily_report as dr
from evidence import current_build


class Pages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = current_build(Path(__file__).parent / 'history')
        cls.now = datetime(2026, 11, 21, 18, tzinfo=timezone.utc)

    def test_report_has_both_accounts_flags_and_a_stale_banner_only_when_old(self):
        html = dr.report_page(Path(__file__).parent, self.build, now=self.now)
        for part in ('Cuenta modelo', 'Cuenta activa', 'Alertas de tus reglas', 'lang="es"', 'trading-compare.html'):
            self.assertIn(part, html)
        captured = datetime.fromisoformat(self.build['record']['_evidence']['captured_at'])
        fresh = dr.report_page(Path(__file__).parent, self.build, now=captured)
        self.assertNotIn('Datos viejos', fresh)
        old = dr.report_page(Path(__file__).parent, self.build, now=captured.replace(year=captured.year + 1))
        self.assertIn('Datos viejos', old)

    def test_status_page_and_failures_do_not_block_the_site(self):
        html = dr.status_page(Path(__file__).parent, self.build, now=self.now)
        for part in ('Build del modelo', 'Escáner de mercado', 'Tendencia del mercado', 'Backtest', 'Carpeta history'):
            self.assertIn(part, html)
        self.assertEqual(dr.site_pages('/nonexistent', {'record': {}}, now=self.now) and None, None)

    def test_formatting(self):
        self.assertEqual(dr._eur(-1524.3), '−1.524 €')
        self.assertEqual(dr._pct(7.5), '+7,50 %')
        self.assertEqual(dr._num(25901.2), '25.901')


if __name__ == '__main__':
    unittest.main()
