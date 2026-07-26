# V31 semantic-boundary and contextual-recall candidate

## Confirmed control and metric signal

V30 is the immutable control at **39.5367**:

| Metric | V29 | V30 | Delta |
|---|---:|---:|---:|
| Score | 39.4830 | **39.5367** | **+0.0537** |
| WER | 55.5478 | **55.4442** | **-0.1036** |
| J_assertion | 51.2278 | **51.3029** | **+0.0751** |
| J_candidates | 26.9477 | 26.9477 | 0 |

The score is `0.3 * (100 - WER) + 0.3 * J_assertion + 0.4 *
J_candidates`. Therefore V30 gained about `+0.0311` from span/text quality
and `+0.0225` from matched assertions. Candidate work is deliberately frozen
in V31.

## Connected insights

Three independent observations point to the same intervention:

1. V26's stable boundary group and V27's semantic-boundary group contributed
   to the positive V28 aggregate result.
2. V30 moved both WER and J_assertion upward after completing 15 additional
   symptom spans and recovering reviewed mentions.
3. The remaining V30 boundary gaps have the same linguistic form: a generic
   symptom head followed by a location, body part, duration, or severity.

V31 therefore completes all 34 reviewed aliases left by that pattern:

- anatomical complements such as `đau đầu vùng thái dương phải`, `đau vùng
  gan phải`, `phù ngoại vi`, and `phù nhẹ 2 chi dưới`;
- lexical symptom completions such as `đau thắt ngực`, `đau rát khi đi tiểu`,
  and `hạ huyết áp tư thế đứng`;
- duration/severity complements such as `đau lưng âm ỉ`, `đau dữ dội`, and
  `ngứa toàn thân`.

The two known failure modes remain excluded: `tăng đánh trống ngực` adds a
change-of-degree prefix, while `cơn ngất xỉu` adds an event noun rather than a
clinical boundary.

## Contextual recall and assertion scope

Seven reviewed symptom mentions are added:

- three medication side effects in one enumerated list: `bồn chồn`, `bứt rứt
  trong người`, and `giảm ham muốn`;
- two repeated `đi cầu phân sống` mentions in a clinical consultation;
- two `căng thẳng` occurrences backed by accepted occurrences in V30.

The phrase `không biết là tình trạng đi cầu phân sống ...` expresses
uncertainty in a question; it does not negate the symptom. V31 removes the
spurious `isNegated` only for that precise epistemic construction and keeps
true negation such as `không có đi cầu phân sống`.

## Artifact verification

- Records: **100**
- Entities: **2696**
- Changed records: **28**
- Semantic boundary expansions: **34**
- Contextual recall additions: **7**
- Relevant regression tests: **41 passed**
- Strict submission validator: **PASS**
- Deterministic rebuild: byte-identical
- SHA-256:
  `42b1004dad77ac3457b7a9541cca5db24ddec110b9fb5e558b36fea0a361a124`

## Confirmed leaderboard result

V31 scored **39.4604**, so it is rejected:

| Metric | V30 control | V31 | Delta |
|---|---:|---:|---:|
| Score | **39.5367** | 39.4604 | **-0.0763** |
| WER | **55.4442** | 55.5456 | **+0.1014** |
| J_assertion | **51.3029** | 51.1501 | **-0.1528** |
| J_candidates | 26.9477 | 26.9477 | 0 |

The weighted regression is approximately `-0.0304` from text and `-0.0458`
from assertion matching. The experiment falsifies the assumption that every
unseen teacher boundary alias should be completed. V30 remains the production
control. Future iterations must use smaller causal groups backed by accepted
occurrences or exact repeated-context agreement.
