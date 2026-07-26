# V47 canonical Vietnamese ICD category strategy

## Observed outcome

V47 was submitted at 03:25 on 2026-07-26 and scored **41.4810**:

- control: confirmed V45 at **41.9694**;
- 94 candidate-only replacements;
- WER unchanged at `55.4442`;
- J_assertion unchanged at `51.4203`;
- J_candidates `32.9413 → 31.7203` (`-1.2210`);
- total score `41.9694 → 41.4810` (`-0.4884`).

The candidate-only attribution is exact:

`0.4 × -1.2210 = -0.4884`.

V47 is rejected. V45 remains production and parent-category replacement must
not be expanded further.

The artifact is:

`submission/candidate_v47_v45-vietnam-icd-canonical-category-label.zip`

SHA-256:

`144f63831e96723cf26378cd288844d41452dd4847de2f49495b5e0098096b71`

Production `submission/output.zip` remains V45.

## Causal hypothesis

The official Vietnamese ICD catalogue contains category labels such as
`béo phì` (E66), `suy tim` (I50) and `đau nửa đầu [Migraine]` (G43).
Production currently emits a singleton unspecified child such as E66.9,
I50.9 or G43.9 for those generic surfaces.

V47 tests whether the competition gold follows the mention's exact ontology
abstraction level rather than forcing the most specific billable child. This
direction is supported by:

1. V42's positive exact-label experiment;
2. V36's negative result from blindly selecting more specific children;
3. the task format accepting a list of ontology identifiers rather than
   evaluating primary billing validity.

The leaderboard result directly rejects this batch-level hypothesis. The gold
prefers unspecified child codes for enough of the 94 occurrences that any
category-label gains are dominated by losses.

## Safety boundary

The V47 allowlist is frozen. A diagnosis changes only when:

1. its canonical surface is one of 27 reviewed official category labels;
2. its current singleton candidate equals the reviewed unspecified child;
3. the replacement is an ancestor in the same ICD family.

Canonicalization is limited to Unicode/case/space, optional leading `bệnh`,
bracketed synonyms, dash variants and catalogue presentation `và/hoặc`.
There is no fuzzy matching, contextual inference or cross-family mapping.

V46's H40.9→G93.2 changes, multi-code augmentation, boundary repairs,
assertion repairs and recall additions are all excluded.

## Validation evidence

- source compile: PASS;
- three V47 unit tests run manually: PASS;
- expected cohort counts: 27/27;
- expected candidate changes: 94/94;
- changed records: 50/50;
- independent official-workbook audit: PASS;
- submission validator: PASS, 100 records and 2,689 entities;
- ZIP layout: exactly `output/1.json` through `output/100.json`;
- delta audit: exactly 94 diagnosis `change` rows, assertions unchanged;
- deterministic rebuild: byte-for-byte PASS.

`pytest` is not installed in the environment, so the three test functions were
executed directly after `py_compile`.

## Resulting rule

- Keep V45 as production.
- Do not submit V47 again.
- Do not add parent categories as second candidates: the observed replacement
  loss is too large for the earlier half-credit assumption to justify a slot.
- Do not infer that every cohort is negative; the aggregate score cannot
  identify winners. With limited submissions, however, cohort-by-cohort parent
  probing is strategically dominated by higher-evidence cross-family exact
  label corrections.
