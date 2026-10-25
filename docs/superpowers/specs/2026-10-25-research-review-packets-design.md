# Scanner research review packets

The user authorized the best suitable TradingAgents adaptation and asked whether
the existing scanner still works. Use the existing Python/static-page architecture.

## Decision

Add an exportable, frozen research packet to every universe and market candidate.
Three unexecuted role assignments (data, valuation, risk) receive the same snapshot
and content hash. Preserve sources, missing inputs, model assumptions and all
objections, including responded/corrected ones. Two review rounds require claims,
evidence, responses and a separate verification before closure.

The packet is a research handoff, not a completed review or an approval record.
The existing assessment gate remains the only authority for ratings. No API calls,
new runtime dependencies, score/DCF/NGV/regime changes, trades or automatic merges.

## Approaches

A full TradingAgents fork adds provider credentials, dependencies and many model
calls without proving source quality. A display-only note does not provide shared
evidence. Choose an offline, per-stock packet: it works with the current scanner,
can be reviewed here or by another tool, and adds no recurring model costs.
This is the implementer's choice under the user's authorization.

## Interface and acceptance

- Scanner JSON contains separate `review_packets.universe` and `.market` maps;
  identical symbols in the two lists cannot collide.
- Each packet has schema `research-review-packet-v1`, status `NOT_STARTED`, a
  `snapshot`, its SHA-256, three `NOT_RUN` assignments and an explicit no-approval
  policy. A content hash binds a snapshot; it does not authenticate a source.
- The snapshot contains original inputs, output assumptions, dated origin,
  source IDs, issues, objections, thesis, counterargument and next evidence needed.
- Missing values stay null; export does not mutate inputs or claim a review ran.
- Each detail panel offers one JSON download. Downloads survive changed filters
  and repeated opening; source text remains inert at desktop and mobile widths.
- Show scanner coverage and the count of approved ratings separately. An empty
  filtered universe list explains that absent approval is not scanner failure.
- Existing fixed weights and pure regime ordering remain unchanged.

## Validation

Audit the committed scan, last Actions runs and deployed scanner JSON. Run all
Python and existing Node tests, then real Chromium checks of both lists, filters,
details and downloaded packets. Test hash sensitivity, missing values, separate
list identities and unresolved objections. Document the live scanner findings.
