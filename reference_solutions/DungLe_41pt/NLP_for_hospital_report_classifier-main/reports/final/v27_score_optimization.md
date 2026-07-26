# V27 score-aware boundary and recall batch

## Data recovery

The exact 100 input records were recovered from the public upstream repository
`Laxury-H/Viettel-AI`. All 100 SHA-256 values match
`data_manifests/raw_manifest_v2.json`; the restored `input/` remains ignored by
Git.

## Composition

V27 starts from V26 and adds 12 changes:

- 11 strict symptom boundary expansions from the two-teacher
  `boundary-95-single` artifact;
- one exact repeated-line symptom addition.

Together with the five stable V26 repairs, the submitted artifact differs from
V24 by 17 changes.

The boundary filter rejects:

- leading event/change modifiers (`Tăng`, `Giảm`, `cơn`);
- compound spans containing `/`;
- spans cut immediately before a required laterality word (`phải`, `trái`);
- additions that are not one-to-one expansions.

The repeated-line stage transfers only a V19 model-consensus addition that is
absent from V18, has empty assertions, occurs in an identical clinical line,
and does not overlap a target entity. It recovers `ngửa đầu ra sau` in record
6 from the same exact line already accepted in record 11.

## Expected range

- confirmed control V24: `39.3762`;
- V26 evidence-backed component: approximately `+0.0041`;
- semantic expansions and repeated-line recall: unscored;
- V27 target range: `39.386`–`39.400`.

This is intentionally a larger, score-aware batch after the single-boundary
V25 probe was confirmed neutral.
