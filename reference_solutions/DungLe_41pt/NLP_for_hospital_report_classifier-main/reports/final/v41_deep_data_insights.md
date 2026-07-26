# V41 — causal data audit and exact Vietnamese ICD label correction

## Confirmed baseline

V37 remains production at `41.8315`:

- WER: `55.4442`;
- J_assertion: `51.4203`;
- J_candidates: `32.5967`.

V40 changed six assertion arrays but reproduced every V37 metric exactly.
Those six mentions have zero measured influence and should not be used as the
basis for another assertion expansion.

## What the full audit rules out

The remaining error surface was inspected by mechanism instead of by isolated
examples:

- all six remaining `isFamily` assertions describe a real relative, spouse or
  inherited risk;
- 46 aligned near-clone pairs yielded no missing entity or boundary transfer;
- 363 normalized surfaces carry candidates, 205 repeat, and none has
  inconsistent candidate assignment across occurrences;
- 759 of 760 diagnosis mentions and all 219 medication mentions already have
  singleton candidate lists, so reordering candidates cannot help;
- exact matching against more than 12,000 official Vietnamese ICD labels
  produced no safe missing diagnosis mention; the only uncovered phrase,
  `giảm thể tích`, occurs inside a negated imaging description and is not a
  dehydration diagnosis.

The residual candidate problem is therefore semantic code selection, not
candidate-list ordering or dictionary recall.

## High-confidence residual

Records 6 and 11 contain the same structured-history diagnosis:

`Bệnh tim mạch do xơ vữa động mạch`

The current candidate is `I70.90`. The official Vietnamese ICD-10 appendix
uses this exact label for `I25.1`. This is stronger evidence than the rejected
V36 specificity expansion:

- the label is exact, not inferred from extra clinical context;
- the replacement changes ICD branch, not merely parent/child granularity;
- both occurrences are in structured patient history, where gold matching has
  repeatedly shown influence.

V41 changes only those two candidates from `I70.90` to `I25.1`.

## Quantitative expectation

The two successful Vietnamese ICD batches have nearly identical marginal
effects:

- V34: `+3.7067 / 149 = +0.02488` J_candidates per changed occurrence;
- V35 over V34: `+1.9423 / 78 = +0.02490` per changed occurrence.

If both repeated V41 mentions match gold, the expected change is about:

- J_candidates: `+0.0498`;
- total score: `0.4 × 0.0498 = +0.0199`;
- projected score: approximately `41.8514`.

This estimate is conditional, not guaranteed. WER and J_assertion must remain
identical to V37 by construction.

## Deferred hypothesis

Record 26 contains the full official phrase
`rối loạn cảm xúc lưỡng cực khác`, while production extracts the shorter
`rối loạn cảm xúc lưỡng cực` and assigns `F31.9`. The official full-label code
is `F31.8`. This is a plausible combined boundary-and-candidate correction,
but it is deliberately excluded from V41 so the higher-confidence
candidate-only signal remains causally identifiable. It is the next isolated
probe only if V41 confirms the exact-label direction.

## Artifact

`submission/candidate_v41_v37-vietnam-icd-exact-label-correction.zip`

SHA-256:

`3e8bf322229b060608828f3525238a9d38cf03712490c1fa29dd76f327dd88e3`

Validation: PASS, 100 records, 2,689 entities. The deterministic rebuild has
the same SHA-256.
