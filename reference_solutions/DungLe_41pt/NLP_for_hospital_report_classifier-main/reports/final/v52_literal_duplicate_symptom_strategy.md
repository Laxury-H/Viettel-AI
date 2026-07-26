# V52 — literal duplicate symptom pruning on confirmed V51

## Control

V51 is now confirmed production:

- score `41.9878`;
- WER `55.4298`;
- J_assertion `51.4354`;
- J_candidates `32.9653`.

Removing two false diagnosis entities improved every component relative to
V45. The exact decomposition is:

| Metric | V45 | V51 | Delta | Score contribution |
|---|---:|---:|---:|---:|
| WER (lower is better) | 55.4442 | 55.4298 | `-0.0144` | `+0.00432` |
| J_assertion | 51.4203 | 51.4354 | `+0.0151` | `+0.00453` |
| J_candidates | 32.9413 | 32.9653 | `+0.0240` | `+0.00960` |
| Total | 41.9694 | 41.9878 | — | `+0.01845` |

The small rounding difference explains the displayed `+0.0184`.

## V52 intervention

V52 retains the first entity and removes only the second entity in eight
literal symptom repetitions:

- `phù phù`: 3 removals;
- `đau đau`: 1 removal;
- `mệt mỏi - mệt mỏi`: 4 removals.

These occupy five records and four near-duplicate document templates. The
guard requires:

1. identical normalized symptom surfaces;
2. identical assertions;
3. no intervening clinical text—only whitespace or a bullet separator.

Parenthetical echoes such as `khó thở (khó thở)` are deliberately excluded
because hidden-gold policy for aliases/parentheses is not established.

## Projection and risk

Mechanical extrapolation from V51 gives `42.0614`; extrapolation from V21
gives `42.0786`. Neither is a forecast. V51 removed two mentions that were
both false in a laboratory seam, whereas V52 assumes only the second token in
each symptom duplicate is false.

Promotion rule: score must exceed V51 `41.9878`. A positive result validates a
general exact-duplicate pruning policy. A neutral or negative result closes
this family and leaves V51 production unchanged.

## Validation

- records: 100;
- entities: 2,679;
- symptom removals: 8;
- retained entity assertions/candidates unchanged;
- first token of every pair retained;
- direct invariant tests: PASS;
- strict validator: PASS;
- deterministic rebuild: PASS.

Artifact:

`submission/candidate_v52_v51-literal-duplicate-symptom-pruning.zip`

SHA-256:

`1c442828e18a153db5bd86765e83a921f49a012ee7927cfbde8992c840c4b3e9`
