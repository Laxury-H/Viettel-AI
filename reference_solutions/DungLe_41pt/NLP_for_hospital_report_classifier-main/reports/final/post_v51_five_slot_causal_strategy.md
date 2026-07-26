# Five-slot causal strategy after V49

## Result update and current control

V51 has now replaced V45 as the confirmed best submission:

- score `41.9878`;
- WER `55.4298`;
- J_assertion `51.4354`;
- J_candidates `32.9653`.

Slot 1 succeeded. Four submission slots remain. The immediate next artifact
is V52, an eight-removal literal-duplicate symptom probe built on V51.

V47, V48 and V49 are all rejected. Their negative results close three broad
policies: parent-category replacement, indiscriminate exact-label recall, and
candidate inference from qualifiers outside the mention boundary.

## Priority order for the five remaining slots

### Slot 1 — V51 precision pruning — completed, positive

Remove two E11.9 diagnosis entities from the malformed record-38 urinalysis
seam while retaining the valid type-2 diabetes diagnosis in that record.

This has the strongest relevant causal precedent. V21 also removed exactly
two structurally false diagnosis mentions and improved total score by
`+0.0227`, with all three component metrics improving. V51 is not guaranteed
to repeat that result, but it tests the only residual policy with a confirmed
positive pruning analogue.

### Slot 2 — V52 duplicate-symptom extension

Retain the first token and remove the second in three `phù phù`, one
`đau đau`, and four `mệt mỏi - mệt mỏi` repetitions. This directly exploits
the now-positive structural-pruning policy while keeping parenthetical aliases
out of scope.

### Slot 3 — rebase the V50 stroke-synonym split

Change only two `tai biến mạch máu não` candidates in record 3 from I63.9 to
I64. This separates the stroke synonym from the harmful AA-amyloidosis branch
that was mixed into V49.

### Slot 4 — rebase the V46 intracranial-context split

Change six H40.9 candidates to G93.2 in four records where the local context
is congenital hydrocephalus/CSF shunt or head CT with papilloedema. This is a
separate translation-context hypothesis and must not be merged before it is
measured.

### Final slot — conditional branch

- If V52 is positive, retain it as the new control for candidate rebases.
- Merge only candidate branches that are independently positive.
- Keep the final slot unused rather than merge any neutral or negative branch.

The eight symptom pairs occupy five records and four independent document
templates; records 39 and 47 share one near-duplicate template.

## Why this sequence is efficient

The sequence answers different annotation-policy
question:

| Version | Changed dimension | Causal question |
|---|---|---|
| V51 | entity existence | Are malformed lab-seam diagnoses false positives? |
| V52 | entity existence | Is the second token in literal/list duplication spurious? |
| V50 | candidate substitution | Is generic Vietnamese stroke I64 rather than I63.9? |
| V46 | candidate substitution | Does context recover mistranslated intracranial pressure? |

The sequence avoids repeating the main mistake of V49: combining mechanisms
before their signs are known. It also preserves two slots for exploitation
after the exploratory evidence arrives.
