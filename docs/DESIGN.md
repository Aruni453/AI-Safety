# Design decisions (1 page)

**Goal.** Measure whether a small RAG assistant over public data stays *grounded*, avoids *data leakage* and resists
*instruction override* (direct and via retrieved pages), then propose mitigations backed by the results.

## Key decisions

1. **Public data in SQLite.** KB = SQuAD v1.1 dev (2,067 Wikipedia paragraphs, 10,570 real questions). Real questions
   give real utility numbers (gold answers) and a real false-positive corpus for the filters. Synthetic rows
   (confidential canaries, poisoned copies) are tagged `source='synthetic_*'` so public and planted data never mix up.
2. **SQL does the data work.** Retrieval is FTS5/BM25; the ACL is a `WHERE classification='public'` clause (so it is
   enforced *before* the model sees anything); cases and every result row are tables; all report numbers come from
   named queries in `sql/analysis.sql`, including the leave-one-out self-join.
3. **Offline deterministic mock model by default.** Reproducible, free, no API key. It is a pessimistic *simulation*
   (obeys the most recent instruction-like text; extracts sentences), so results validate the harness and the defense
   layering, not any model. A real backend uses the same cases.
4. **The mock parses the final prompt string**, which is what makes the delimiter-breakout attack real: a poisoned chunk
   containing `</untrusted_context>` ends the "data" region early.
5. **Defenses are independent toggles** - measured alone, together, and leave-one-out.
6. **Attacks are placed fairly but deliverably:** each poison is planted where real questions retrieve it, and a test
   asserts every attack case succeeds at baseline (so no case passes vacuously).
7. **Utility is measured, not assumed** (30 real questions) so the cost of each defense is visible.

## What the results say (mock backend)

- Baseline blocks 0/12 attacks and answers 0/4 out-of-KB questions with a refusal; a plain retrieval leak (L01, L06)
  needs no injection at all.
- **No single control is enough.** Best single: output filter (7/12). `all`: 12/12 attacks, 4/4 refusals.
- **ACL at retrieval is the only thing that stops salary-band leakage (L05)**: the output filter can't, since the
  numbers have no recognizable pattern.
- **Spotlighting alone fixes little (2/12)**: it blocks the "reveal your prompt" page (O06) but not the phishing page
  (the mock still *relays* poisoned text as if it were fact, O04) and a delimiter breakout (O05) beats it until
  `sanitize` strips look-alike tags (3/12).
- **Regex filters are bypassable**: the paraphrased override (O03) slips past the input filter. On the other side, they
  flagged 0 of 10,570 real questions and 0 of 2,067 clean paragraphs, so their cost on this data is a miss rate, not
  false alarms.
- **Grounding guard is useful but costly**: it is the only control that fixes out-of-KB answers (4/4 at tau=0.5) and
  holds O03 under `all`, but it wrongly refuses 4/30 real questions at baseline coverage (2 of which baseline answered
  correctly). The sweep table shows the tradeoff; 0.5 was a round-number default, not tuned per case.

## Proposed mitigations (priority order)

1. **Enforce access control at retrieval** (per-user/role ACL in the query), never rely on the model to withhold
   what it was shown.
2. **Treat retrieved text as data**: spotlight *and* strip delimiter look-alikes; prefer role-separated message
   fields over string concatenation.
3. **Egress controls**: URL allowlist, secret/DLP scanning, no auto-rendered links or images.
4. **Replace regex filters with a classifier or LLM-judge signal** that raises risk and logs; evaluate on the real
   false-positive corpus (here: all SQuAD questions) before hard-blocking.
5. **Ground answers with citations** and verify with entailment rather than word overlap; use a calibrated retrieval
   confidence (not a lexical threshold) to decide when to refuse.
6. **Least privilege**: no secrets in system prompts or the KB; give the assistant no tools or write access.
7. **Provenance for the KB**: sign or review pages before indexing; flag pages that changed recently.
8. **Keep this harness in CI**, grow the case set (multilingual, encoded, multi-turn) and rerun on every model, prompt
   or KB change.

## Residual risk

Paraphrased and multi-turn attacks, semantic poisoning that reads like a legitimate fact, and real-model behaviour are
not covered by this build. Read 12/12 as "this suite, on the mock", not "secure".
