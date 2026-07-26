# Post-V45 ICD parent/candidate-list structure audit

## Outcome

This audit finds the first post-V45 hypothesis whose mechanical projection
clears the `+0.35` submission threshold at every historical marginal:

- **94 candidate-only replacements**;
- 50 records and 38 near-duplicate-adjusted templates;
- 27 surface/code cohorts;
- projected score gain from `+0.4098` to `+1.5591`.

The proposed direction is to map a generic Vietnamese mention to the exact
ICD category label instead of its automatically chosen `không xác định`
subcategory. No entity, boundary, type or assertion would change.

This is still a **research hold**, not a promoted submission. The size is now
large enough, but the category-versus-unspecified direction has not yet been
isolated on the leaderboard. `submission/output.zip` remains V45.

## Why this hypothesis is different

Production emits a singleton candidate for 759 of 760 diagnoses. Yet the
problem asks for a *list* of suitable identifiers, and the published GERD
example is rendered with two K21-family values. The exact second value is
ambiguous in the available mirror, so that example is evidence for inspecting
candidate hierarchy, not proof that every gold list contains parent and child.

Sources:

- Current official contest page:
  <https://competition.viettel.vn/contests/medical-2026>
- Readable mirror of the earlier detailed brief:
  <https://www.studocu.vn/vn/document/truong-dai-hoc-bach-khoa-dai-hoc-quoc-gia-thanh-pho-ho-chi-minh/mang-may-tinh/ai-race-2026-ontological-reasoning-in-medical-knowledge-retrieval/168063103>

The local national appendix contains 15,844 codes. There are 690 production
diagnosis occurrences whose current child code also has an official parent.
The audit does **not** modify all 690. It retains only cases where the
Vietnamese surface equals the parent label after presentation-only
normalization:

- Unicode/case/space normalization;
- optional leading `bệnh`;
- bracketed synonyms such as `[Migraine]` or `[thống phong]`;
- dash variants in labels such as `dạ dày - thực quản`.

No fuzzy similarity or clinical inference is used in the 94-item allowlist.

## Cohort inventory

| Canonical surface | Current | Exact category | Occurrences | Templates |
|---|---|---|---:|---:|
| béo phì | E66.9 | E66 | 12 | 9 |
| thoái hóa tinh bột | E85.9 | E85 | 10 | 2 |
| suy tim | I50.9 | I50 | 7 | 5 |
| đau nửa đầu | G43.9 | G43 | 7 | 1 |
| xuất huyết dưới nhện | I60.9 | I60 | 6 | 1 |
| loét tá tràng | K26.9 | K26 | 5 | 1 |
| tiền sản giật | O14.9 | O14 | 5 | 2 |
| đái tháo đường típ 2 | E11.9 | E11 | 5 | 5 |
| hẹp ống sống | M48.00 | M48.0 | 4 | 4 |
| hội chứng ruột kích thích | K58.8 | K58 | 3 | 1 |
| não úng thủy | G91.9 | G91 | 3 | 2 |
| sỏi mật | K80.2 | K80 | 3 | 3 |
| 15 cohort còn lại | — | — | 24 | — |
| **Tổng** | | | **94** | **38 distinct** |

The strict form, without removing `bệnh`, brackets or dashes, already contains
47 occurrences in 24 templates. Presentation normalization adds 47 more; it
does not introduce any fuzzy-label cohort.

## Triangulation from prior leaderboard experiments

Three pieces of evidence point in the same direction:

1. V42 showed that exact Vietnamese display labels can beat plausible codes
   from another semantic branch.
2. V36 forced 25 mentions to more detailed official children and reduced
   J_candidates by `0.0932`. The gold did not simply reward maximum billing
   specificity.
3. The detailed problem example exposes the K21 category for a generic GERD
   phrase.

There is also contrary evidence: all 17 strict parent codes are marked in the
2026 appendix as not suitable for primary billing when a 4/5-character child
exists. The competition evaluates ontology linking rather than primary
billing, but this prevents treating the batch as certain.

## Score projection

| Calibration | Replace child with exact category | Add category as second code |
|---|---:|---:|
| V34/V35 code-system mean | `+0.9358` | `+0.4679` max half-credit |
| V42 exact-label optimistic | `+1.5591` | `+0.7795` max half-credit |
| V45 exact-label residual | **`+0.4098`** | `+0.2049` max half-credit |

The replacement variant clears `+0.35` even at the V45 residual rate. The
two-code variant is safer under a parent/child ambiguity but does not clear
the threshold at the conservative residual rate.

The table is a mechanical extrapolation, not a calibrated probability-weighted
expectation. If gold consistently uses unspecified children, replacement can
be negative. If gold uses exact category labels, replacement has the larger
upside. If gold lists both, augmentation is superior.

## Submission decision

Do not mix this with V46, assertion repairs, boundary changes or fuzzy label
changes. If a leaderboard slot is allocated to this direction, it must be one
candidate-only causal probe:

1. first choice for information gain: strict 47-item exact-label replacement;
2. first choice for maximum projected score: canonical 94-item replacement;
3. do not promote unless WER remains `55.4442`, J_assertion remains `51.4203`,
   and total score exceeds V45 by a material margin.

Because the user requires a predicted gain of at least `+0.35`, only the
94-item replacement qualifies mechanically. No ZIP was generated during this
research pass.

## Reproduction

```bash
python3 scripts/analyze_icd_parent_candidate_structure.py \
  --input input \
  --submission submission/output.zip \
  --workbook /path/to/icd2026.xlsx \
  --output /tmp/icd_parent_candidate_structure.json
```

Expected key results:

```text
diagnosis candidate cardinality: 759 singleton, 1 double
official child-parent eligible: 690
strict exact parent label: 47 occurrences / 24 templates
canonical exact parent label: 94 occurrences / 38 templates
V45-residual replacement projection: +0.4098
decision: research_hold
```

Production SHA-256 remains:

```text
c5afa4be374c7a329f63b2bfe67a613b99910e71408f8c73c755db785e77ece3
```
