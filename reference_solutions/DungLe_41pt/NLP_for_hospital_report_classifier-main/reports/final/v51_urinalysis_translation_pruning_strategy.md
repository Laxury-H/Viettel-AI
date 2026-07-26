# V51 — precision pruning at a Vietnamese translation seam

## Leaderboard decision

V51 is **CONFIRMED AND PROMOTED TO PRODUCTION**. It starts from confirmed
V45 (`41.9694`) and removes exactly two diagnosis entities in record 38:

| Position | Surface | Candidate |
|---|---|---|
| `[1733, 1747]` | `đái tháo đường` | E11.9 |
| `[1747, 1761]` | `đái tháo đường` | E11.9 |

The raw source around both entities is:

```text
tổng phân tích nước tiểu có đái tháo đườngđái tháo đường
```

This is a malformed translation seam in a urinalysis result, not a normal
diagnosis statement. The same record already contains a valid historical
entity `Đái tháo đường típ 2` with E11.9, and V51 preserves it.

## Why this is a new mechanism

V47 tested parent versus child ICD codes and failed. V48 tested broad recall
additions and failed. V49 tested source semantics outside the extracted span
and failed. V51 does none of those:

- it changes no candidate on a retained entity;
- it infers nothing from a qualifier outside the span;
- it adds no dictionary match;
- it prunes only a duplicated diagnosis produced inside a laboratory-result
  translation seam.

This is therefore a direct precision hypothesis about annotation type and
entity existence. Its expected signal is a lower WER and possibly higher
J_assertion. J_candidates may stay unchanged because record 38 still contains
the valid E11.9 diagnosis.

## Risk and interpretation

The hidden gold may mechanically annotate both literal `đái tháo đường`
tokens despite the malformed sentence. A neutral or negative result would
show that the gold follows token surface more closely than discourse role.
A positive result would establish a valuable pruning policy for other
translation seams.

Because there are only two removals in one record, no large gain is promised.
The experiment is useful now specifically because the earlier `+0.35`
per-submission requirement has been removed.

The closest positive leaderboard precedent is V21: it removed exactly two
structurally false diagnosis mentions and gained `+0.0227`, with WER,
J_assertion and J_candidates all improving. That result supports precision
pruning as a policy, but it is not used as a guaranteed V51 projection because
the linguistic structures differ.

Observed result: score `41.9878` (`+0.0184` over V45), WER `55.4298`,
J_assertion `51.4354`, and J_candidates `32.9653`. All three components
improved, so the pruning hypothesis is accepted.

## Validation

- control: V45 `submission/output.zip`;
- records: 100;
- entities: 2,687;
- diagnosis removals: 2;
- every non-target entity unchanged byte-for-byte;
- valid record-38 type-2 diabetes diagnosis retained;
- record-level candidate-set delta: 0;
- strict validator: PASS;
- two direct invariant tests: PASS;
- deterministic rebuild: PASS.

Artifact:

`submission/candidate_v51_v45-urinalysis-translation-pruning.zip`

SHA-256:

`c0df1d0b6eeaed0996d4a3fc13ac552050fd4c9cac97ec554786bb835781985b`
