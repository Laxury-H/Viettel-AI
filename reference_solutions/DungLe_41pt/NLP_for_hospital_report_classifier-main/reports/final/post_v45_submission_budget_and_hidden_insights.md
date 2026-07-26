# Post-V45 submission budget and hidden-data audit

## Decision

Production remains V45 at **41.9694**. V46 is **HOLD** and must not be
submitted: its conditional gain is only `+0.0262`, far below the required
`+0.35`.

With WER and J_assertion fixed, a `+0.35` total-score target requires:

```text
0.4 × delta(J_candidates) >= 0.35
delta(J_candidates) >= 0.875
```

The two most relevant empirical candidate marginals imply very different
budgets:

- V42-grade exact semantic repair: at least 22 changed occurrences;
- V45-grade residual exact-label repair: at least 81 changed occurrences.

The lower count is only valid for changes as strong as the two V42 semantic
families. It cannot be applied to parent/child code changes.

## Audit 1 — exact parent labels are a false large batch

The 2026 Ministry workbook was parsed directly from its XLSX XML. Across 760
diagnosis occurrences and 268 unique surface-candidate pairs, 47 occurrences
in 27 records use an unspecified/specific child while their surface exactly
matches a three- or four-character parent display label.

Examples include:

- `suy tim`: I50.9 versus I50 — 7;
- `xuất huyết dưới nhện`: I60.9 versus I60 — 6;
- `loét tá tràng`: K26.9 versus K26 — 5;
- `tiền sản giật`: O14.9 versus O14 — 5;
- `hẹp ống sống`: M48.00 versus M48.0 — 4;
- thirteen smaller families — 20.

This looks large enough only under the inappropriate V35 marginal:

| Calibration class | Projected score delta for 47 |
|---|---:|
| V35 absent-code dialect conversion | `+0.4681` |
| V45 residual exact-label repair | `+0.2049` |
| V36 specificity/abstraction class | `-0.0701` |

The closest causal experiment is V36, not V35. V36 changed valid parent/child
specificity while preserving mention boundaries and reduced J_candidates.
Vietnamese hospital catalogues also retain the unspecified child for ordinary
clinical coding—for example, plain unspecified heart failure is displayed as
I50.9—while the 2026 appendix flags many parent rows as requiring a more
specific code. Therefore the 47-change parent batch is rejected.

## Audit 2 — qualifiers outside the extracted boundary

A separate scan found ten candidate occurrences with a clinically meaningful
qualifier immediately outside the current entity:

- `bệnh thận mạn ... Giai đoạn 4`: N18.9 may need N18.4 — 4;
- `Đái tháo đường, có biến chứng bệnh lý thần kinh ngoại biên`: E11.9 may
  need E11.4 — 2;
- `viêm tủy xương mãn tính`: M86.9 may need a chronic M86 child — 3;
- `rối loạn cảm xúc lưỡng cực khác`: F31.9 may need F31.8 — 1.

These are genuine errors in the rule system, but candidate-only correction is
not guaranteed to match a gold entity whose boundary may include the
qualifier. The full ten-change cluster projects only about `+0.0436` under the
V45 residual rate. It is retained for a future larger cross-family batch, not
submitted alone.

## Audit 3 — billing combination codes are not mention-linking codes

The 2026 Ministry implementation notice requires hospitals to consider the
whole encounter when assigning main and accompanying billing codes. This
creates tempting context rules such as hypertensive heart/renal disease or
diabetes with neuropathy.

The competition output, however, links a candidate to each extracted mention.
Replacing a literal `tăng huyết áp` mention by I13.2 merely because heart
failure and chronic kidney disease occur elsewhere would change the ontology
of that mention. Such encounter-level combination rules are excluded unless
the relation is stated inside the entity boundary.

## Current safe portfolio

- V45: production.
- V46 intracranial-context changes: 6, HOLD.
- qualifier-outside-boundary cluster: 10, research-only.
- parent-label abstraction cluster: 47, rejected as a bulk submission.

Even merging the 16 non-parent changes yields only about `+0.0698` at the
closest observed residual rate. No current artifact meets the `+0.35`
submission threshold.

The next candidate must therefore be a new semantic cross-family normalization
system comparable to V34/V35 or at least 22 V42-grade corrections. More
parent/child remapping, isolated boundary edits, or single clinical
translation hypotheses do not satisfy the submission budget.

## Evidence

- National ICD-10 appendix under Circular 06/2026/TT-BYT:
  https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/06-byt-kem.pdf
- Ministry implementation notice:
  https://kcb.vn/tin-tuc/cong-van-so-4059-byt-bh-trien-khai-thong-tu-06-2026-tt-byt-quy-dinh-ma-hoa-benh-tat-theo-icd-10.html
- Hospital ICD catalogue showing I50/I50.9 distinction:
  https://phusannhidanang.org.vn/TraCuuXetNghiem/lstICD/GetICD?page=370
