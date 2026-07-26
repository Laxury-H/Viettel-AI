# Post-V49 candidate-set and annotation-policy audit

## Decision

Keep V45 production at **41.9694**. V49 is rejected at **41.8633**. No
remaining candidate currently justifies one of the five submission slots.

## Insight 1 — count candidate effects at two granularities

V49 contains five entity edits but only four record-level candidate-set
changes:

| Record | Set effect |
|---|---|
| 3 | remove I63.9, add I64 |
| 21 | add E85.3; E85.9 remains elsewhere |
| 32 | add E85.3; E85.9 remains elsewhere |
| 79 | add E85.3; E85.9 remains elsewhere |

This does not by itself prove the scorer aggregates candidates per record;
the rules describe Jaccard scoring per concept. It does prove that raw
occurrence count overstates independent evidence and can hide additive
false-positive risk.

The same audit gives:

- V42: seven entity edits, three record-level substitutions, positive
  J_candidates `+0.2903`;
- V45: five entity edits, five substitutions, positive but small
  J_candidates `+0.0543`;
- V47: 94 entity edits across 50 changed record sets, negative
  J_candidates `-1.2210`;
- V49: five entity edits across four changed record sets, negative
  J_candidates `-0.2650`.

Future candidates must report both numbers and distinguish substitution from
addition.

## Insight 2 — eliminate qualifier-outside-span coding

V49 demonstrates that a clinically meaningful suffix outside the extracted
entity is not a safe basis for replacing its code. The remaining cohorts with
the same mechanism are removed from the submission portfolio:

- CKD stage 4 outside boundary: 4;
- diabetes with neuropathy: 2;
- diabetes with renal disease: 2;
- chronic osteomyelitis outside boundary: 4;
- bipolar `khác` outside boundary: 1.

Together with the three AA changes tested in V49, this closes a 16-occurrence
family that previously looked promising but did not respect mention-level
linking.

## Insight 3 — the national-code conversion is exhausted

The official 2026 workbook contains 15,844 codes. V45 has 760 diagnosis
occurrences and 268 unique surface/candidate pairs. Only two emitted
candidate values are absent from the workbook: B19.1 and B19.2 on one
negated family-history composite `nhiễm virus viêm gan B, C`.

There is no exact replacement that preserves acute/chronic status and both
viruses. B16.9/B17.1 would assert acute disease; B18.1/B18.2 would assert
chronic disease; B19.9 would erase the stated viruses. The residual is held,
not guessed.

## Insight 4 — remaining small hypotheses do not meet the budget

- V46 H40.9→G93.2: six occurrences/four records, translation-context risk.
- Varicella/zoster multi-code augmentation: two occurrences, additive
  false-positive risk.
- Urinalysis `đái tháo đườngđái tháo đường`: two malformed occurrences in one
  record; likely a translation/type error but too small for a slot.
- `tai biến mạch máu não` I64: two occurrences in one record; V49 cannot
  isolate its sign.

None has a credible path to the requested `+0.35`.

## Insight 5 — precision pruning needs policy evidence, not relevance

V48 proved that new dictionary matches in educational fragments are mostly
false-positive. It does not prove that existing entities in every educational
fragment are false-positive: many may be part of the original annotation
vocabulary. V40 also showed that changing six assertions at hybrid seams was
neutral.

Therefore a broad removal of educational or unrelated clinical content is
not yet justified. The next precision candidate requires a repeated
structural signature already supported by a positive pruning experiment,
such as the polar-question rule from V21, and enough affected record sets to
meet the submission threshold.
