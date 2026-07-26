# V28 repeated neurologic recall

## Motivation

After restoring the exact raw input, a Unicode-safe inventory found eight
symptom occurrences missing from V27 even though:

1. the symptom surface is already accepted at least twice elsewhere;
2. the target line occurs verbatim in at least two different records;
3. the exact target span does not overlap an existing entity.

## Additions

- `co giật` ×2;
- `ngửa đầu ra sau` ×2;
- `mất định hướng` ×2;
- `đi lại không vững` ×2.

All eight occur in duplicated neurologic history/examination lines in records
6 and 11. Assertions are recomputed from each target context; no offset,
record ID or output entity is hardcoded in the inference rule.

V28 therefore differs from confirmed V24 by:

- 16 score-aware boundary expansions;
- nine repeated-line/model-supported additions;
- 25 total entity changes across the composed V26–V28 stages.

## Expected range

The eight additions are a higher-recall step than V27. Based on the measured
positive V19 addition groups, the target range is `39.40`–`39.44`. This range
is intentionally wider because individual contribution is not identifiable
without a leaderboard result.

## Confirmed leaderboard result

V28 scored **39.4461** on 100/100 records:

| Metric | V24 control | V28 | Delta |
|---|---:|---:|---:|
| Score | 39.3762 | **39.4461** | **+0.0699** |
| WER | 55.7062 | **55.5927** | **-0.1135** |
| J_assertion | 51.0299 | **51.1496** | **+0.1197** |
| J_candidates | 26.9477 | 26.9477 | 0 |

The ZIP SHA-256 shown by the platform starts with `bcc921e35de4`, matching
the locally generated artifact. V28 is therefore promoted to the new
confirmed control. The simultaneous WER and assertion gains support continued
high-precision recovery of omitted symptom mentions.
