"""CRWV's September 2026 consolidated US-GAAP leverage bridge, in USD.

The raw provider cache is evidence. Apply the issuer figures to a copy only.
Operating rent remains an expense in the default operating EBITDA.
"""
from datetime import datetime
from integrity import positive_number


SEC = 'https://www.sec.gov/Archives/edgar/data/1769628/'
Q3 = SEC + '000176962826000465/crwv-20260930.htm'
FY = SEC + '000176962826000104/crwv-20251231.htm'
Q3_RELEASE = SEC + '000176962826000461/coreweave3q26earningspress.htm'
FY_RELEASE = SEC + '000176962826000094/coreweave4q25earningspress.htm'
# EDGAR accession 0001769628-26-000465, accepted at 07:20:41 Eastern.
ACCEPTED = datetime.fromisoformat('2026-11-12T12:20:41+00:00')
PERIOD = '2026-09-30'
TTM_ENDS = [PERIOD, '2026-06-30', '2026-03-31', '2025-12-31']
FCF_LIMIT = 'CoreWeave needs a sustainable cash-flow bridge for replacement capex and financing.'


def _ttm(fy25, nine_months25, nine_months26):
    """Whole USD from issuer tables reported in USD millions."""
    return (fy25 - nine_months25 + nine_months26) * 1_000_000


def reconcile(facts, as_of):
    inputs = dict(facts.get('inputs') or {})
    # Keep the original three fields available for audit even when the leverage
    # metric is unavailable. Raw EBITDA can be useful outside the leverage test.
    inputs.update(provider_debt=inputs.get('debt'), provider_cash=inputs.get('cash'),
                  provider_ebitda=inputs.get('ebitda'))
    result = dict(facts, inputs=inputs)
    if (as_of < ACCEPTED or facts.get('financial_period') != PERIOD
            or facts.get('financial_currency') != 'USD' or facts.get('basis') != 'TTM'
            or facts.get('period_ends') != TTM_ENDS):
        inputs.update(debt=None, issuer_leverage_ebitda=None)
        result['primary_warnings'] = [*facts.get('primary_warnings', []),
            'No matching dated CoreWeave debt, lease and EBITDA bridge for this reporting window.']
        return result

    # Q3 balance sheet p. 6 and Notes 8 and 10. Restricted cash (1,405 + 877)
    # cannot be netted against these consolidated debts. Nominal is a separate
    # claim measure; 552 + 80 of unamortized costs explain the book difference.
    carrying = (9_183 + 32_417 + 1_389 + 3_884) * 1_000_000
    finance = (296 + 353) * 1_000_000
    operating = (668 + 18_029) * 1_000_000
    cash, securities = 4_122_000_000, 62_000_000
    operating_ebitda = _ttm(-46, 44, 14) + _ttm(2_454, 1_633, 4_429)
    adjusted = _ttm(3_093, 2_197, 4_923)
    fixed_rent = _ttm(825, 540, 1_592)
    inputs.update(debt_carrying_ex_leases=carrying, debt_principal_ex_leases=47_505_000_000,
                  finance_lease_liabilities=finance, operating_lease_liabilities=operating,
                  cash_equivalents=cash, marketable_securities=securities,
                  restricted_cash=(1_405 + 877) * 1_000_000,
                  debt=carrying + finance, cash=cash + securities,
                  issuer_leverage_ebitda=operating_ebitda,
                  adjusted_ebitda_after_rent=adjusted, adjusted_ebitdar=adjusted + fixed_rent,
                  net_debt_including_operating_leases=carrying + finance + operating - cash - securities)
    # Keep the greater precision of a provider's historical OCF/capex. The
    # rounded issuer tie-out is descriptive, never a sustainable FCFE input.
    inputs['issuer_ttm_ocf'] = _ttm(3_058, 1_499, 5_638)
    inputs['issuer_ttm_cash_capex'] = _ttm(10_309, 6_249, 23_558)
    inputs['issuer_ttm_ocf_less_cash_capex'] = inputs['issuer_ttm_ocf'] - inputs['issuer_ttm_cash_capex']
    if not (facts.get('shares_basis') == 'ISSUER_COVER_ALL_CLASSES'
            and facts.get('shares_asof') and '2026-10-30' < facts['shares_asof'] <= as_of.date().isoformat()
            and positive_number(inputs.get('shares')) is not None):
        inputs['shares'] = 465_847_732 + 90_277_992
        result.update(shares_asof='2026-10-30', shares_basis='ISSUER_COVER_ALL_CLASSES')
    result['source_urls'] = list(dict.fromkeys([*facts.get('source_urls', []), Q3, FY, Q3_RELEASE, FY_RELEASE]))
    result['primary_warnings'] = [*facts.get('primary_warnings', []),
        'September issuer leverage includes finance leases and unrestricted securities. '
        'Operating rent remains in EBIT plus D&A. Customer prepayments and financed capex '
        'require separate normalization.']
    return result
