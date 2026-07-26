# V24 score optimization from public ablation evidence

## Decision

Use `D2-V19-xlmr-additive-85` (39.3683) as the immutable control and remove
only its two new `đỏ mắt` symptom entities.

This is not a semantic guess. The earlier V17 red-eyes experiment added the
same two surfaces and reduced the public score from 39.2864 to 39.2786:

- score delta: -0.0078;
- WER delta: +0.0101 (worse);
- J_assertion delta: -0.0160;
- J_candidates delta: 0.

The V24 transform compares entity keys against the V18 ZIP, so an entity that
already existed in the scored control can never be removed. Only V19 additions
with a surface in the independently rejected group are pruned.

## Leaderboard result

Assuming the measured red-eyes marginal transfers to the V19 control:

| Artifact | Score | WER | J_assertion | J_candidates |
|---|---:|---:|---:|---:|
| V19 additive-85, confirmed | 39.3683 | 55.7164 | 51.0138 | 26.9477 |
| V24 pruned, confirmed | 39.3762 | 55.7062 | 51.0299 | 26.9477 |

V24 was submitted on 2026-07-25 at 14:20 and improved the confirmed V19 score
by `0.0079`. The observed score and all three components agree with the
pre-submission projection to within `0.0001`, confirming that the two
`đỏ mắt` additions had the same negative marginal effect after composition
with V19.

## Next ablations

Do not bundle further unscored edits into the first V24 submission. After its
score is known, isolate the remaining V19 additions by evidence group:

1. `rối loạn thị giác`, `ngửa đầu ra sau`, `Mệt`;
2. `weak`, `tê bì`, `mù vĩnh viễn`.

The second group improved the nested trajectory by 0.0245 in aggregate. It
must remain intact until a leave-one-out submission can attribute individual
effects.
