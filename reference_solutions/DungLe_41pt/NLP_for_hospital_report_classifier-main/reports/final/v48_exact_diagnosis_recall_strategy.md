# V48 — exact Vietnamese diagnosis recall

## Outcome

V48 is a validated, isolated recall probe on confirmed V45 production:

- control score: **41.9694**;
- records: **100**;
- existing V45 entities changed: **0**;
- diagnosis additions: **15** across **8** records;
- output entities: **2704**;
- validator: **PASS**;
- direct invariant tests: **PASS**;
- deterministic rebuild: **PASS**;
- SHA-256:
  `18c702c704574445fe7add31cf15b6508fe297a63d7f1aacc3ceb26b3f1b75d1`.

The candidate is:

`submission/candidate_v48_v45-vietnam-exact-diagnosis-recall.zip`

## Confirmed leaderboard result

V48 scored **41.7881** and is rejected:

| Metric | V45 control | V48 | Delta |
|---|---:|---:|---:|
| Score | **41.9694** | 41.7881 | **-0.1813** |
| WER | **55.4442** | 55.5975 | **+0.1533** |
| J_assertion | **51.4203** | 51.0402 | **-0.3801** |
| J_candidates | **32.9413** | 32.8884 | **-0.0529** |

The weighted decomposition is approximately `-0.0460` from WER, `-0.1140`
from assertion matching, and `-0.0212` from candidates. The result falsifies
the assumption that an official ICD label plus neighbouring annotations is
enough to justify a new entity. Educational and explanatory disease mentions
are annotated selectively. V45 remains production.

## Why the search direction changed

V47 replaced 94 unspecified child codes with official category parents. It
lost `1.2210` J_candidates and `0.4884` total score while WER and assertions
were exactly unchanged. This falsifies parent-category canonicalization and
provides a strong rule for all later work:

> When a mention lacks subtype detail, retain the leaf-level unspecified code
> used by Vietnamese hospital coding, not the category parent.

V48 therefore does not rewrite candidates. It searches for omitted diagnosis
mentions and assigns a leaf or unspecified-leaf code.

## Three evidence filters

Every V48 addition passes all three filters:

1. **Official terminology** — the diagnosis is present in the 2026 Vietnam
   ICD catalogue.
2. **Local annotation evidence** — the same document contains an annotated
   same-family diagnosis or a parallel item in the same medical list.
3. **No overlap** — the added span does not overlap any V45 entity.

| Surface | Count | Code | Local evidence |
|---|---:|---|---|
| `trứng cá` | 6 | L70.9 | Seven `mụn trứng cá` mentions already use L70.9 |
| `rụng tóc toàn bộ` | 2 | L63.1 | Same documents annotate `rụng tóc từng mảng/vùng` |
| `mày đay` | 2 | L50.9 | Explicit adverse-effect list beside annotated dermatitis |
| `bạch biến` | 2 | L80 | Same explicit adverse-effect list |
| `cao răng` | 1 | K03.6 | Periodontal treatment context |
| `viêm túi mật` | 1 | K81.9 | Negated imaging result beside negated bile-duct stone |
| `Parkinson` | 1 | G20 | Same document already annotates `hội chứng Parkinson` |

The `viêm túi mật` addition keeps `isNegated`; all other additions have empty
assertions.

## Hidden recall layers kept separate

The audit found other plausible gaps, but they are not mixed into V48:

- high-context symptoms: two `ảo thanh`, one `môi đỏ`, one negated
  `thay đổi thói quen đại tiện`;
- one repeated template: eight negated `buồn ngủ`;
- secondary diagnoses: two `đột tử`, two `nhiễm nấm`, one
  `suy giảm miễn dịch`, and two vitamin-B12 deficiency mentions;
- conversational or generic terms: `lo lắng`, `dị ứng`, `nhiễm khuẩn`,
  `nhiễm virus`, `tổn thương`, and `tư vấn`.

The last group is excluded because an official ICD match alone does not prove
that the corpus annotates the occurrence as a clinical concept.

## Expected value and seven-submission policy

V29 gained `0.0369` from eight high-evidence recall additions, or roughly
`0.00461` total score per addition under a deliberately conservative linear
calibration. Applied to 15 additions, V48 projects to about **42.0386**
(`+0.0692`). This is an evidence-based expectation, not a guarantee and not
the previously requested `+0.35`.

The seven remaining submissions should be used adaptively:

V48 consumed the first of seven slots and was negative. The six remaining
slots must therefore avoid broad recall:

1. return to V45 as the immutable control;
2. prioritize candidate-only changes on existing entities in direct patient
   context;
3. do not submit the secondary diagnosis or symptom-recall cohorts;
4. use small, coherent candidate cohorts so metric movement remains causal;
5. reserve at least two slots for confirmation/union of positive cohorts;
6. reserve the final slot for the best leaderboard-confirmed combination.

The V48 skin-topic cohort should not be retried without an independent gold
signal; a smaller recall batch would have low upside and would consume a
scarce slot merely to ablate a now-disfavoured mechanism.
