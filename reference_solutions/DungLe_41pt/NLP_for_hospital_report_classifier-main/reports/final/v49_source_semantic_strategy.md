# V49 source-semantic candidate strategy

## Confirmed leaderboard result

V49 scored **41.8633**:

| Metric | V45 | V49 | Delta |
|---|---:|---:|---:|
| WER | 55.4442 | 55.4442 | 0 |
| J_assertion | 51.4203 | 51.4203 | 0 |
| J_candidates | 32.9413 | 32.6763 | -0.2650 |
| Total | 41.9694 | 41.8633 | -0.1061 |

The candidate metric alone explains the loss:
`0.4 × -0.2650 = -0.1060`, with `0.0001` rounding difference.

Reject V49 and keep V45 production.

## Artifact design

V49 is a validated candidate-only artifact on the confirmed V45 production
control. It changes five existing diagnosis candidate lists and leaves all
2,689 entities, spans, types, and assertions unchanged.

| Cohort | Occurrences | Records | Change |
|---|---:|---:|---|
| Unspecified cerebrovascular event | 2 | 1 | I63.9 → I64 |
| Autoimmune/AA amyloidosis | 3 | 3 | E85.9 → E85.3 |

Artifact:

```text
submission/candidate_v49_v45-vietnam-source-semantic-cross-family.zip
SHA-256 2bbf6f3d0fad8c292b5ce753b46f2572634538c8365840d622c8b5dc7aeab7f3
```

Validation, three direct tests, and deterministic byte-for-byte rebuild pass.
`submission/output.zip` remains the confirmed V45 artifact.

## Why this is different from V48

V48 added new diagnoses from educational and explanatory passages. Its
leaderboard result showed that exact ICD labels and nearby clinical evidence
do not imply that the gold policy annotates those mentions.

V49 adds nothing. Every changed diagnosis already exists in V45, so WER and
J_assertion are invariant by construction. Only the candidate code can move.

## Evidence and risk

`Tai biến mạch máu não` is a common Vietnamese synonym for unspecified
stroke. I63.9 asserts cerebral infarction, while I64 leaves haemorrhage versus
infarction unspecified. This directly extends the already-positive V45
mapping for `đột quỵ`.

The amyloidosis passages enumerate source categories translated into
Vietnamese. The entity boundary stops at `Bệnh amyloidosis`, but the immediate
suffix is `tự miễn dịch`, corresponding to autoimmune/AA amyloidosis. E85.3
is secondary systemic amyloidosis; E85.9 is unspecified. All three
occurrences are one repeated source template, so their metric impact repeats
but their evidential independence does not.

## Post-result decision

The pre-submit conservative V45 marginal projected `41.9912` (`+0.0218`) and
the optimistic V42 marginal projected `42.0523` (`+0.0829`). The observed
result was negative, showing that the five changes are not members of the
previous positive exact-span class.

The strongest causal interpretation is that a candidate must describe the
actual extracted span. A qualifier immediately outside the boundary is not a
safe basis for replacing the candidate. This eliminates the remaining CKD,
diabetes-complication, bipolar, and chronic-osteomyelitis qualifier cohorts.

Do not spend a submission to isolate the two `tai biến mạch máu não` changes:
the combined result cannot establish that they are positive, and their
maximum plausible gain is far below the requested `+0.35`.
