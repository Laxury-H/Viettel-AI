# V26 stable boundary-group composition

## Why this group

Two independently scored V17 artifacts isolate the value of this boundary
group:

| V17 artifact | Key difference | Score | WER |
|---|---|---:|---:|
| boundary-9875 | four strongest repairs | 39.3053 | 55.8181 |
| boundary-985-single | above + `Nôn` → `Nôn mửa` | 39.3094 | 55.8046 |
| boundary-98-single-stable | above without `Nôn`, but + five stable expansions | 39.3094 | 55.8046 |

Therefore the five stable expansions have the same observed aggregate value as
the independently measured `Nôn` repair: approximately `+0.0041` score and
`-0.0135` WER.

## V26 changes

V26 keeps the confirmed V24 control, including `Nôn mửa`, and composes the five
stable expansions:

1. `đau bụng` → `đau bụng râm ran` (two records);
2. `Đau` → `Đau thượng vị`;
3. `nổi mẩn đỏ ngứa` → `nổi mẩn đỏ ngứa ở lưng`;
4. `đau` → `đau các khớp`.

The transformation is derived automatically from the two model-generated V17
reference ZIPs. It transfers only strict one-to-one symptom supersets and
rejects contractions such as `Nôn mửa` → `Nôn`.

## Projection

- control V24: `39.3762`;
- projected V26: `39.3803`;
- projected WER: `55.6927`;
- J_assertion and J_candidates: unchanged.

The projection assumes the previously measured boundary-group marginal remains
additive after composition with V24. A public score is still required before
promotion.
