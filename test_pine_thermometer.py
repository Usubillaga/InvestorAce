"""The Pine thermometer must use the same formula and bands as the Python one (no network)."""
import re
import unittest
from pathlib import Path

import market_pulse
import panic_backtest as pb
import index_leaders as il

PINE = (Path(__file__).parent / 'pine' / 'panic_thermometer.pine').read_text()


class PineThermometer(unittest.TestCase):
    def test_same_scores_bands_and_levels(self):
        for formula in ('(40.0 - vix) / 30.0 * 100.0', '50.0 + 5.0 * 100.0 * (spx / ma200 - 1.0)',
                        '50.0 + 10.0 * 100.0 * (spx / ma50 - 1.0)', 'ta.sma(close, 200)', 'ta.sma(close, 50)',
                        'n >= 3 ? total / n : na'):
            self.assertIn(formula, PINE)
        limits = [int(x) for x in re.findall(r'heat < (\d+) \? "', PINE)]
        self.assertEqual(limits, [limit for limit, _ in market_pulse.BANDS[:-1]])
        self.assertIn(f'input.float({pb.PANIC:.1f}, "Buy level, accounts 20 and MOVE")', PINE)
        self.assertIn(f'input.float({il.EUPHORIA:.1f}, "Euphoria', PINE)
        self.assertIn(f'input.float({il.SETUP["20-move"]["move_max"]:.1f}, "MOVE account', PINE)
        self.assertIn(f'input.int({il.MOVE_WINDOW}, "MOVE mean length', PINE)


if __name__ == '__main__':
    unittest.main()
