# V54 — explicit past mention temporality

## Goal

Use the first of four remaining submission slots for an assertion-only probe
whose changes are independently auditable. V54 is based on confirmed V53
production and does not mix entity recall or candidate changes.

## Evidence

Every target satisfies all three conditions:

1. an explicit past cue occurs on the same raw line;
2. the same surface and type already has an `isHistorical` occurrence in the
   same record;
3. no mention, boundary, type or candidate is changed.

The eight additions are:

- record 4: six entities on lines beginning `Triệu chứng cách đây vài năm`;
- record 69: `trầm cảm` and `ý định tự tử` in a negated statement about
  prior history. Their existing `isNegated` assertions are retained.

## Validation

- control: V53 `41.9901`;
- records: 100;
- entities: 2,687;
- assertion additions: 8;
- entity/span/type/candidate changes: 0;
- direct and regression tests: PASS;
- strict validator: PASS;
- deterministic rebuild: PASS.

Mechanical extrapolation from V53's two-change result gives approximately
`41.9995`. This is a reference, not a forecast, because assertion Jaccard is
not guaranteed to be linear per mention.

Promote only if:

- total score is greater than `41.9901`;
- J_assertion is greater than `51.4432`;
- WER remains `55.4298`;
- J_candidates remains `32.9653`.

Artifact:

`submission/candidate_v54_v53-explicit-past-mention-temporality.zip`

SHA-256:

`e0f5a7471bae4659bb2cded51dbb8e18ad779d868c481dede84881365c832f2e`

## Leaderboard result

V54 was submitted at 16:23 on 26/07/2026 and scored `41.9973`, improving
over V53 by `+0.0072`.

| Metric | V53 | V54 | Delta |
|---|---:|---:|---:|
| WER | 55.4298 | 55.4298 | 0 |
| J_assertion | 51.4432 | 51.4670 | +0.0238 |
| J_candidates | 32.9653 | 32.9653 | 0 |
| Total | 41.9901 | 41.9973 | +0.0072 |

The movement is assertion-only as predicted. V54 is promoted to production;
V53 remains its rollback artifact.
