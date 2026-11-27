"""Insider purchase clusters (no network)."""
import json
import unittest

import numpy as np
import pandas as pd

import insider_backtest as ib


class Clusters(unittest.TestCase):
    def test_purchases_clusters_returns_and_report(self):
        sub = pd.DataFrame(dict(ACCESSION_NUMBER=['a', 'b', 'c', 'd', 'e'],
                                FILING_DATE=['05-JAN-2010', '10-JAN-2010', '20-JAN-2010', '01-JUN-2010', '02-JUN-2010'],
                                ISSUERTRADINGSYMBOL=['AAA', 'AAA', 'AAA', 'BBB', 'AAA'],
                                RPTOWNERCIK=['1', '2', '3', '9', '1']))
        trans = pd.DataFrame(dict(ACCESSION_NUMBER=['a', 'b', 'c', 'd', 'e', 'e'],
                                  TRANS_CODE=['P', 'P', 'P', 'P', 'S', 'P'],
                                  TRANS_ACQUIRED_DISP_CD=['A', 'A', 'A', 'A', 'D', 'A'],
                                  TRANS_SHARES=['100', '100', '100', '50000', '10', '1'],
                                  TRANS_PRICEPERSHARE=['10', '10', '10', '30', '10', '10']))
        p = ib.purchases(sub, trans)
        self.assertNotIn('S', p.to_string())
        sig = ib.clusters(p)
        self.assertEqual([(s, str(d.date()), b) for s, d, b, _ in sig],
                         [('AAA', '2010-01-20', 3), ('BBB', '2010-06-01', 1)])   # 3 buyers; $1.5M by one buyer
        idx = pd.bdate_range('2009-12-01', periods=300)
        adj = pd.DataFrame({'AAA': np.linspace(10, 20, 300), 'BBB': 30.}, index=idx)
        spx = pd.Series(100., index=idx)
        members = pd.DataFrame(True, index=idx, columns=adj.columns)
        rows = ib.returns(sig, adj, spx, members)
        self.assertEqual(rows[0]['entry'], '2010-01-21')                         # first close after the filing
        self.assertGreater(rows[0]['126']['excess'], 0)
        self.assertIsNone(rows[1]['252'])                                         # past the data
        members['BBB'] = False
        self.assertEqual(len(ib.returns(sig, adj, spx, members)), 1)              # not a member: left out
        r = ib.study(rows)
        json.dumps(r, allow_nan=False)
        self.assertIn('Insider purchase clusters', ib.report(r))
        self.assertFalse(r['passes'])                                             # far too few signals


if __name__ == '__main__':
    unittest.main()
