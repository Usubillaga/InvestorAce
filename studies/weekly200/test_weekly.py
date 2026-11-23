import unittest

import numpy as np
import pandas as pd

import backtest as bt

from .download import annual_rows
from .signals import Reports, Sleeve, collect, eligible, weekly_bars


class TestAsOf(unittest.TestCase):
    def test_sma_uses_prior_200_weeks_and_actual_holiday_session(self):
        dates = pd.bdate_range("2016-01-04", "2021-12-31").difference(
            pd.DatetimeIndex(["2021-04-02"])
        )
        values = np.arange(len(dates)) + 100.0
        data = pd.DataFrame({"close": values, "low": values - 1, "high": values + 1}, index=dates)
        bars = weekly_bars(data, dates)
        day = pd.Timestamp("2021-04-02")
        self.assertEqual(bars.at[day, "session"], pd.Timestamp("2021-04-01"))
        self.assertAlmostEqual(bars.at[day, "line"], bars.close.loc[:day].iloc[-201:-1].mean())
        data.loc["2021-03-29":] *= 0.3
        self.assertEqual(weekly_bars(data, dates).at[day, "line"], bars.at[day, "line"])
        self.assertTrue(bars.line.iloc[:200].isna().all())
        data.loc["2021-04-01", "close"] = np.nan
        gap = weekly_bars(data, dates)
        self.assertTrue(np.isnan(gap.at[day, "close"]))
        self.assertFalse(gap.at[day, "touch"])

    def test_zone_exact_touch_and_confirmation_are_separate(self):
        dates = pd.bdate_range("2014-01-06", periods=5 * 261)
        weekly = np.linspace(50, 150, 261)
        weekly[-2:] = [113, 115]
        data = pd.DataFrame({"close": np.repeat(weekly, 5)}, index=dates)
        data["low"], data["high"] = data.close * 0.998, data.close * 1.002
        # The 200-week line is known before the last week trades.
        level = weekly[-201:-1].mean()
        data.loc[dates[-4], "low"] = level * 1.01
        bars = weekly_bars(data, dates)
        self.assertTrue(bars.iloc[-1].confirm)
        reports = Reports(
            [{"filed": "2018-03-01", "end": "2017-12-31", "accession": "example", "quality": True}]
        )
        events, _ = collect("TEST", bars, reports)
        self.assertTrue(eligible(events[-1], "quality_confirm"))
        self.assertFalse(eligible(events[-1], "quality_exact_touch"))
        data.loc[dates[-4], "low"] = level * 0.99
        events, _ = collect("TEST", weekly_bars(data, dates), reports)
        self.assertTrue(eligible(events[-1], "quality_exact_touch"))
        data.loc[dates[-1], "close"] = 112
        self.assertFalse(weekly_bars(data, dates).iloc[-1].confirm)

    def test_latest_known_filing_even_when_newer_facts_are_missing(self):
        reports = Reports(
            [
                {"filed": "2021-02-01", "end": "2020-12-31", "quality": True},
                {"filed": "2022-02-01", "end": "2021-12-31", "quality": None},
            ]
        )
        self.assertIsNone(reports.at(pd.Timestamp("2021-02-01")))
        self.assertTrue(reports.at(pd.Timestamp("2022-02-01"))["quality"])
        self.assertIsNone(reports.at(pd.Timestamp("2022-02-02"))["quality"])
        self.assertIsNone(reports.at(pd.Timestamp("2024-02-02")))

    def test_annual_facts_require_two_years_in_one_filing_and_real_capex(self):
        facts = {}
        for tag, val in [
            ("Assets", 100),
            ("NetIncomeLoss", 8),
            ("NetCashProvidedByUsedInOperatingActivities", 12),
            ("PaymentsToAcquireProductiveAssets", 4),
            ("PaymentsToAcquirePropertyPlantAndEquipment", 1),
        ]:
            rows = [
                {
                    "start": f"{year}-01-01",
                    "end": f"{year}-12-31",
                    "val": val,
                    "form": "10-K",
                    "fp": "FY",
                    "filed": "2021-02-01",
                    "accn": "x",
                }
                for year in (2019, 2020)
            ]
            facts[tag] = {"units": {"USD": rows}}
        row = annual_rows({"facts": {"us-gaap": facts}})[0]
        self.assertTrue(row["quality"])
        self.assertEqual(row["current"]["capex"], 4)
        facts.pop("PaymentsToAcquireProductiveAssets")
        facts.pop("PaymentsToAcquirePropertyPlantAndEquipment")
        self.assertIsNone(annual_rows({"facts": {"us-gaap": facts}})[0]["quality"])


class TestPortfolio(unittest.TestCase):
    def test_correction_next_close_limit_and_pending_exit(self):
        days = pd.bdate_range("2020-01-01", periods=280)
        market = pd.Series(np.arange(len(days), 0, -1) + 100.0, index=days)
        prices = pd.Series(100.0, index=days)
        names = "ABCD"
        frames = {s: bt.indicators(prices, prices + 1, prices - 1) for s in names}
        # First-day signal, next-close fill at 100. A close at 85 triggers an exit.
        # Missing next price must hold the position and its slot until the first valid fill.
        frames["A"].loc[days[-4] : days[-4], "close"] = 85.0
        frames["A"].loc[days[-3], "close"] = np.nan
        frames["A"].loc[days[-2], "close"] = 80.0
        entries = {days[-6]: [(0, s) for s in names], days[-4]: [(0, "D")]}
        base = bt.simulate(frames, market, {}, days[-6], precise=True, **bt.VARIANTS[bt.BASE])
        empty = bt.simulate(
            frames,
            market,
            {},
            days[-6],
            precise=True,
            weekly_sleeve=Sleeve({}, {}),
            **bt.VARIANTS[bt.BASE],
        )
        res = bt.simulate(
            frames,
            market,
            {},
            days[-6],
            precise=True,
            weekly_sleeve=Sleeve(entries, {}),
            **bt.VARIANTS[bt.BASE],
        )
        self.assertEqual(base["final"], empty["final"])
        self.assertEqual(res["weekly_fills"], 3)
        self.assertEqual(res["weekly_open"], 2)
        self.assertEqual(res["weekly_exits"]["STOP"], 1)
        self.assertAlmostEqual(
            res["final"], 10000 - 36 * 100 * 0.001 - 12 * (100 - 80) - 12 * 80 * 0.001
        )

    def test_no_stop_still_exits_on_weekly_break_or_expiry(self):
        day = pd.Timestamp("2024-04-12")
        pos = {"entry": 100, "entered": day}
        book = Sleeve({}, {day: {"A"}}, stop=False)
        self.assertEqual(book.exit_reason("A", day, 70, pos), "WEEKLY_BREAK")
        self.assertIsNone(book.exit_reason("B", day, 70, pos))
        self.assertEqual(book.exit_reason("B", day + pd.Timedelta(weeks=26), 100, pos), "MAX_HOLD")
