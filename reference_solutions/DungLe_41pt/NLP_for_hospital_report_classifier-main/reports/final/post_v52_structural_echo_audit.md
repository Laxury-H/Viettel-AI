# Structural-echo audit after V51

## Confirmed policy

V51 proves that raw surface occurrence alone does not force a gold entity.
Two literal `đái tháo đường` tokens inside a malformed urinalysis sentence
were false positives: removing them improved WER, assertion Jaccard and
candidate Jaccard simultaneously.

This supports structural precision pruning, but not arbitrary deduplication.
The residual echoes are therefore split by separator and discourse role.

## Tier 1 — literal/list duplicates: V52

| Pattern | Removals | Records | Templates | Decision |
|---|---:|---:|---:|---|
| `phù phù` | 3 | 2 | 1 | Include |
| `đau đau` | 1 | 1 | 1 | Include |
| `mệt mỏi - mệt mỏi` | 4 | 4 | 3 | Include |

V52 always retains the first token and removes the second. It requires equal
surface, type and assertions, with only whitespace or a bullet separator
between entities.

## Tier 2 — exact parenthetical echoes: hold

Four additional entities repeat the same surface inside parentheses:

| Record | Surface | Type |
|---|---|---|
| 8 | `ảo giác thị giác (ảo giác thị giác)` | symptom |
| 35 | `khó thở (khó thở)` | symptom |
| 89 | `khó thở (khó thở)` | symptom |
| 90 | `tăng huyết áp (tăng huyết áp)` | diagnosis |

They occupy four document templates. They are excluded from V52 because
parentheses may represent an alias or source gloss, and gold may deliberately
annotate both lexical mentions. This cohort becomes a later isolated probe
only if V52 is positive.

## Tier 3 — qualified parenthetical echoes: reject

Record 89 contains:

- `Đái tháo đường (tiền sử Đái tháo đường)`;
- `Tăng huyết áp (tăng huyết áp vô căn (nguyên phát))`.

The parenthetical text changes discourse or specificity. These are not exact
structural duplicates and must not be pruned by a generic rule.

## Tier 4 — modifier echoes: hold separately

Four positions look like translation repetitions but contain intervening
clinical modifiers:

- record 10: `Khó thở nhẹ khó thở`;
- records 42 and 62: `sốt lần cuối sốt` (one near-duplicate template);
- record 88: `sốt kèm theo sốt`.

Removing the second entity may improve precision, but it could also erase a
valid repeated mention attached to a modifier. These are not merged into V52.

## Lab-result seam

Record 22 contains raw text `âm tính âm tính - âm tính chụp hida`. The current
submission emits the first and third result spans, not the middle duplicate.
No pruning or recall is required: the existing entities can correspond to the
Doppler ultrasound and HIDA result respectively.

## Policy

The ordering is intentionally conservative:

1. submit V52 literal/list duplicates;
2. if positive, consider a pure parenthetical-echo probe;
3. never mix qualified/modifier echoes into the same experiment;
4. rebase candidate-only branches on the best confirmed production rather
   than submitting obsolete V45-based ZIPs.
