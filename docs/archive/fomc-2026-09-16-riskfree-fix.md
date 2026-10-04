# FOMC 16.09.2026 — Scoreboard Impact & RISK_FREE Fix

**Status:** patch written and unit-tested, not yet applied to the repo.
**Decision required from Enrique:** spot 10y (5.04) vs. normalized rf (~4.40).

---

## 1. Correction to the first read

I told you the risk was a regime flip REFLATION → INFLATION, with `DUR_W` going
0.00 → 0.45. **That is wrong, and the reason matters.** `macro.read_macro()` has
only four branches:

```python
regime = ('REFLATION'   if growth >= 0 and infl >= 0 else
          'GOLDILOCKS'  if growth >= 0 and infl <  0 else
          'STAGFLATION' if growth <  0 and infl >= 0 else 'RECESSION')
```

**INFLATION is unreachable.** `regime_contract.json` defines its weights
(DUR_W 0.45, BS_W 1.5, PAY_W 1.5) and the classifier can never emit it. Dead
code carrying a live-looking weight set.

The reachable flip from REFLATION is worse, not milder:

| | DUR_W | BS_W | PAY_W |
|---|---|---|---|
| REFLATION (now) | **0.00** | 0.5 | 0.5 |
| → STAGFLATION | **+0.55** | 2.5 (5×) | 1.5 (3×) |
| → GOLDILOCKS | **−0.35** | 0.5 | 0.5 |

REFLATION sits exactly on the hinge where duration is switched **off**. Either
neighbour switches it on, with opposite sign. For a clamped row (±40) the
duration contribution swings from −14 (Goldilocks) to +22 (Stagflation): a
**36-point range in Regime Fit with no price moving**. The entire current
ranking is computed at the one point in the grid where the board's single
largest differentiator contributes zero.

---

## 2. The decision

Unanimous 12-0, target range **3.75%–4.00%**, first hike since July 2023. Warsh:
resilient labour, inflation in "too many categories", price stability is "Job
One". SEP: one more hike 2026, one more 2027, PCE back to 2% pushed 2028 → 2029.
10y **5.041%** intraday, 2y ~4.65%. Oil −3.1% to $102.55.

Hike odds were >90% going in. The front end was priced; the repricing is in the
long end and the terminal rate.

---

## 3. The actual finding: two modules disagree about rates

`macro.py` line 39 fetches `^TNX` live and feeds its 126-day rate of change into
the inflation impulse. `wacc.py` froze the **level** of the same series:

```python
RISK_FREE = 3.67          # % -- US 10y in the source workbooks
```

One module knew rates moved. The other didn't. Gap to the live 10y: **137bp**,
and it has been open for months — today's 25bp just makes it undeniable.

This produced no symptom. The board looked healthy the entire time. That is the
property worth internalising: the `validate()` discipline caught sanity bands,
inverted proximity flags, unmapped sectors — every failure that *showed*. A
stale scalar that reprices all 79 rows coherently shows nothing.

### NGV sensitivity

NGV = (FCF/shares)/r, so NGV(r+d)/NGV(r) = r/(r+d) and sensitivity runs as 1/r².

| WACC | rf → 5.04 (+137bp) | rf → 4.40 (+73bp) | hike only (+25bp) |
|---|---|---|---|
| 4.50% (producers) | **−23.3%** | −14.0% | −5.3% |
| 5.69% | −19.4% | −11.4% | −4.2% |
| 8.00% | −14.6% | −8.4% | −3.0% |
| 11.03% | −11.0% | −6.2% | −2.2% |
| 14.00% | −8.9% | −5.0% | −1.8% |

**The inversion:** low-WACC rows move most. AR, CNX, ENB, OXY, DVN take the
biggest NGV haircut — not NVDA and APP. This is perpetuity arithmetic, not a
statement about the businesses, and it runs opposite to the duration story the
regime model tells. `entry_price(d, target=.60)` is NGV/0.6, so **every entry
price in the book is currently 9–23% too high.**

### Where it lands: the middle, not the tails

`dur = clamp((cover − 0.60) × 100, ±40)` saturates at cover ≥100% and ≤20%.

| Ticker | cover now → at 5.04 | dur now → after |
|---|---|---|
| AR | 257% → 202% | +40.0 → +40.0 (clamped) |
| WKL | 174% → 149% | +40.0 → +40.0 (clamped) |
| GILD | 141% → 121% | +40.0 → +40.0 (clamped) |
| **LVMH** | 94% → 80% | **+34.0 → +20.3** |
| **ABT** | 75% → 63% | **+15.0 → +3.4** |
| **CRM** | 62% → 54% | **+2.0 → −5.8** |
| **ADSK** | 60% → 52% | **0.0 → −7.6** |
| **SPGI** | 53% → 45% | **−7.0 → −14.7** |
| APP | 26% → 23% | −34.0 → −36.9 |
| NVDA | 18% → 16% | −40.0 → −40.0 (clamped) |

Score ranking barely reorders. The **NGV proximity alerts** (AT NGV / CLEARS /
NEAR ENTRY) are absolute-threshold based and flip wholesale. That is the
operationally dangerous part — treat every current CLEARS/NEAR ENTRY flag as
void until the rebuild.

---

## 4. Second bug, found in the same file

```python
FLOOR, CEILING = 0.045, 0.140   # sanity band on the output
```

- **The 4.50% floor is now below the risk-free rate.** It prices equity
  perpetuities as safer than Treasuries. Not conservative — impossible. Low-beta
  levered rows are currently pinned there and will unclamp hard on the fix.
- **The 14.00% ceiling** compresses high-beta rows onto one number. `wacc.py`'s
  own docstring exists to abolish exactly this: *"a beta-0.39 pharma and a
  beta-1.09 consumer-tech company cannot share a discount rate."* At rf 5.04 a
  beta-2.2 row computes 15.4% and gets clamped to 14.0% — the flat-rate failure
  the module was written to remove, reintroduced by its own sanity band.

Patched: floor = rf, ceiling = rf + 2.00 × MRP. Both move with the inputs they
are bands on. The JNJ (5.34% vs 5.36%) and AAPL (8.66% vs 8.67%) workbook
reproductions still pass.

### Third: `r_wacc` is not archived

`history/2026-09-16.json` records `AR: ngv 99.80` and gives no way to recover the
`r` that produced it. No historical snapshot is reproducible, and a repricing
cannot be distinguished from a fundamentals change after the fact. For a
framework whose stated design is *"one input reprices the book"*, not archiving
that input is the gap that let this run for months.

---

## 5. The patch

`investorace-riskfree-fix.patch` — 4 files, tested, applies to `main`.

**`wacc.py`** — `RISK_FREE` demoted to a documented fallback. `resolve_risk_free()`,
`set_risk_free(value, source, asof)`, `provenance()`, `bands(rf)`. Clamp source
recorded per row in `detail['clamped']`.

**`integrity.py`** — `risk_free_faults(provenance, live_10y)`: **blocking** past
50bp drift. Blocking is deliberate and follows your own rule from `validate_full()`
— a check reporting a fact about one row (the beta-gap warning) must not stop a
build; a check proving the *output* is wrong may. A stale rf is the second kind.
Also `clamp_saturation_faults()`: warns when >15% of rows bind, i.e. when the
sanity band has quietly become a flat rate. Both stay market-data free by taking
the observation as an argument.

**`engine.py`** — `sync_risk_free()` called **first** in `run_build()`. Ordering
is the point: `fetch_prices()` computes WACC per row, so setting rf afterwards
would stamp correct provenance onto a book priced at the old rate. Plus `_rates`
and per-row `r_wacc`/`beta`/`wacc_clamped` in the archived observation.

The spot-vs-normalized decision is an explicit literal, not a default buried in
a function — my first draft hardcoded spot, which would have let the merge make
the decision for you:

```python
RISK_FREE_MODE = 'spot'            # 'spot' | 'normalized'
RISK_FREE_NORMALIZED = 4.40
RISK_FREE_NORMALIZED_DRIFT_BP = 150
```

Under `'normalized'` the staleness check widens to tolerate the deliberate gap
and prints it as a warning on **every** build. A declared divergence that stops
being visible is precisely how 3.67 survived for months.

**`reprice.py`** (new) — standalone what-if. Writes nothing: no `index.html`, no
`history/`, no observation. Prints WACC / NGV / cover / entry / duration, now vs.
new, per row, with the largest haircuts, the clamp count, and the Regime Fit
consequence under each DUR_W.

```
python reprice.py                 # live 10y vs. the rate in force
python reprice.py 4.40 5.04       # both scenarios side by side
python reprice.py --held 4.40     # portfolio rows only
```

---

## 6. The open decision

**I disagree with going straight to 5.04.** Setting rf to the spot 10y imports a
cyclical-peak yield into a perpetuity with no terminal value to absorb it. Your
own framework principle says commodity producers need mid-cycle normalization —
the discount rate deserves the same treatment. SEP long-run funds rate is
3.0–4.0%, implying a normalized 10y around 4.25–4.50%.

**Counter-argument, and it is a real one:** `wacc.py`'s docstring defines
RISK_FREE as *"US 10y in the source workbooks"*. Spot **is** the stated design
intent, so normalizing is a change of method, not a bug fix. Two different
decisions are bundled here and should be taken separately:

1. **Bug fix (not optional):** rf must track a live observation and be checked.
2. **Method change (your call):** *which* observation — spot or normalized.

**My recommendation:** `rf = 4.40` as base case, 5.04 as a stress column.
**Risk of going to spot:** it fires sell / DO-NOT-ADD signals across the energy
sleeve at the exact point a stagflationary tilt would favour it, and the
Abgeltungsteuer drag on that rotation is unrecoverable.

Run `python reprice.py 4.40 5.04` before deciding. The numbers above are
computed at representative WACC levels; that command produces them per row from
live betas.

---

## 7. Open items

- **Unreachable INFLATION regime** — either wire a third axis into
  `read_macro()` or delete the weights from `regime_contract.json`. Leaving
  live-looking weights on dead code is how the next silent failure starts.
- **6-month impulse windows** mean the classifier confirms a regime break weeks
  late. REFLATION currently holds (growth +13.1%, inflation +15.4%, Warsh called
  activity solid). Watch for growth crossing zero while inflation stays positive
  → STAGFLATION, where duration switches on at +0.55 and BS_W quintuples.
- **`^TNX` is inside the inflation impulse.** The Fed hiking mechanically raises
  the impulse that classifies the regime. Worth deciding whether that is a
  feature or double-counting.
- **Published board predates the decision** — last run 2026-09-16 01:12 UTC, the
  FOMC released at 18:00 UTC. Nothing on the live site reflects today.
- `cost_of_debt` defaults to `rf` when not supplied and nothing supplies it, so
  the rf change passes through both legs, damped only by the tax shield on the
  debt weight (`we + wd×0.79`). My earlier guess that kd came from historical
  interest expense was wrong.
