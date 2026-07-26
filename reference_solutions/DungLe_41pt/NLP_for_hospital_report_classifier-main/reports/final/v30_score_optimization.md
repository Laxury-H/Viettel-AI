# V30 evidence-fusion breakthrough candidate

## Confirmed control

V29 scored **39.4830** (WER 55.5478, J_assertion 51.2278,
J_candidates 26.9477) and is the immutable control.

## Four independent evidence channels

V30 composes only changes supported by at least one reusable evidence source:

1. **15 accepted-boundary expansions.** A longer symptom surface already
   exists as an accepted entity elsewhere in V29. The target contains exactly
   one shorter symptom. Two false `đau đầu` matches inside `đau đầu gối` are
   rejected explicitly by a lexical-continuation guard.
2. **11 teacher-reviewed symptom additions.** These are clinically meaningful
   gaps such as negated catheter leakage, negated chest discomfort, blurred
   vision, serous wound drainage, and a historical stress mention. Generic
   communication `lo lắng`, food/behavior fragments, `buồn ngủ`, `mày đay`,
   and the previously negative red-eye/Kawasaki recall family remain excluded.
3. **Three safe diagnosis additions.** The reviewed aliases recover two
   actual `tăng HA` history/diagnosis mentions and one stroke-code mention.
   The previously proven-negative `có phải là tăng HA ... không` question
   mentions are filtered by syntax. A `Phát hiện ... từ năm YYYY` cue preserves
   `isHistorical` on the history occurrence.
4. **Five top-1 candidate corrections.** Two GERD mentions are reduced to
   `K21.9` when no esophagitis is present, and three G6PD hemolytic-anemia
   mentions are reduced to `D55.0`.

The top-1 decision is supported by public competition A/B evidence that a
single code outperformed `k=2`, and by CMS descriptions:

- K21.9: gastro-esophageal reflux disease without esophagitis;
- D55.0: anemia due to G6PD deficiency.

## Expected range

V30 changes 34 entity/candidate decisions while preserving all existing
assertions during boundary expansion. Target range: **39.55–39.63**.

## Confirmed leaderboard result

V30 scored **39.5367**:

| Metric | V29 control | V30 | Delta |
|---|---:|---:|---:|
| Score | 39.4830 | **39.5367** | **+0.0537** |
| WER | 55.5478 | **55.4442** | **-0.1036** |
| J_assertion | 51.2278 | **51.3029** | **+0.0751** |
| J_candidates | 26.9477 | 26.9477 | 0 |

The weighted metric deltas explain approximately `+0.0311` from text and
`+0.0225` from assertions. The five top-1 changes and three diagnosis
additions did not move aggregate J_candidates at four decimal places.
Candidate-only work is therefore deprioritized; V30 becomes the new control
for boundary and recall expansion.
