# V25 symptom-boundary optimization

## Control

V24 is the confirmed control:

- score: `39.3762`;
- WER: `55.7062`;
- J_assertion: `51.0299`;
- J_candidates: `26.9477`.

## Single causal change

V25 composes the previously prepared V23 boundary repair onto V24:

```text
miệng thấy hơi thở mùi khó chịu
            ↓
hơi thở mùi khó chịu
```

The removed words are a reporting frame rather than the clinical finding.
The transform keeps the end offset, type, assertions, entity count and every
candidate code unchanged. It applies by reusable linguistic structure and
does not reference a record ID or fixed offset.

## Leaderboard result

V25 was submitted on 2026-07-25 at 14:31. The result was exactly neutral:

- score: `39.3762`;
- WER: `55.7062`;
- J_assertion: `51.0299`;
- J_candidates: `26.9477`.

The unchanged components show that this boundary replacement did not alter the
official matching result. V24 remains the simplest confirmed control.
