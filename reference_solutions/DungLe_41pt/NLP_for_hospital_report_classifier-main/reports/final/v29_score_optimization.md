# V29 high-evidence symptom recall

## Confirmed control

V28 is the new immutable control after scoring **39.4461** (WER 55.5927,
J_assertion 51.1496, J_candidates 26.9477).

## Selection method

The accepted-surface gap inventory scans raw text through the same
Unicode-to-source offset mapping used by production. V29 keeps only omitted
occurrences that are in the previously teacher-reviewed `SAFE_SYMPTOMS`
lexicon and have direct clinical context.

Eight additions survive manual semantic review:

- record 3: `tỉnh chậm`;
- record 6: `cứng đờ`, `cắn lưỡi`, `tiểu tiện không tự chủ`, and the repeated
  summary occurrence `Mất định hướng`;
- records 6 and 11: `nhắm mắt từng lúc` in the duplicated neurologic
  examination line;
- record 6: `Tê bì vùng trán phải` in the explicit admission-symptom list.

The three seizure-associated findings in record 6 retain `isNegated`; the
other five additions have empty assertions. No diagnosis, laboratory,
medication, candidate code, or existing boundary is changed.

Excluded gaps include `môi đỏ` in a parent-facing warning sentence,
communication-level `lo lắng`, and generic adverse-effect descriptions.

## Expected range

V28 confirmed that high-evidence recall can improve both WER and
J_assertion. V29 targets **39.46–39.49** while keeping J_candidates unchanged.

## Confirmed leaderboard result

V29 scored **39.4830**:

| Metric | V28 control | V29 | Delta |
|---|---:|---:|---:|
| Score | 39.4461 | **39.4830** | **+0.0369** |
| WER | 55.5927 | **55.5478** | **-0.0449** |
| J_assertion | 51.1496 | **51.2278** | **+0.0782** |
| J_candidates | 26.9477 | 26.9477 | 0 |

The platform SHA prefix `11d79fdf0d31` matches the deterministic local ZIP.
V29 is promoted to the new confirmed control.
