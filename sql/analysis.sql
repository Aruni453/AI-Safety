-- name: summary
-- Pass counts per config. B* = real SQuAD questions (utility), X* = out-of-KB questions (must refuse),
-- L* = data-leakage attacks, O* = instruction-override attacks. :run_id is bound by the harness.
SELECT r.config,
       SUM(c.case_id LIKE 'B%' AND r.passed) AS qa_pass,       SUM(c.case_id LIKE 'B%') AS qa_n,
       SUM(c.case_id LIKE 'X%' AND r.passed) AS ook_pass,      SUM(c.case_id LIKE 'X%') AS ook_n,
       SUM(c.category = 'data_leakage'         AND r.passed) AS leakage_pass,  SUM(c.category = 'data_leakage')         AS leakage_n,
       SUM(c.category = 'instruction_override' AND r.passed) AS override_pass, SUM(c.category = 'instruction_override') AS override_n,
       SUM(c.kind = 'attack' AND r.passed)                   AS attack_pass,   SUM(c.kind = 'attack')                   AS attack_n,
       SUM(r.passed) AS total_pass, COUNT(*) AS total_n
FROM results r JOIN cases c USING (case_id)
WHERE r.run_id = :run_id
GROUP BY r.config;

-- name: matrix
SELECT c.case_id, c.category, c.kind, r.config, r.passed
FROM results r JOIN cases c USING (case_id)
WHERE r.run_id = :run_id
ORDER BY c.case_id;

-- name: leave_one_out
-- For each case that passes under `all`: which single controls, when removed, make it fail?
SELECT c.case_id, c.kind, a.passed AS passes_under_all, a.reason AS all_reason,
       group_concat(substr(l.config, 5), ', ') AS broke_when_removed
FROM cases c
JOIN results a ON a.case_id = c.case_id AND a.run_id = :run_id AND a.config = 'all'
LEFT JOIN results l ON l.case_id = c.case_id AND l.run_id = :run_id AND a.passed = 1
                   AND l.config LIKE 'all-%' AND l.passed = 0
GROUP BY c.case_id
ORDER BY c.case_id;

-- name: failures
SELECT r.config, r.case_id, r.reason, substr(replace(r.answer, char(10), ' '), 1, 90) AS answer
FROM results r
WHERE r.run_id = :run_id AND r.passed = 0 AND r.config NOT LIKE 'all-%'
ORDER BY r.config, r.case_id;

-- name: retrieval_quality
-- How often is the gold paragraph in the top-k at baseline? (benign SQuAD cases only; sanity check on the retriever)
SELECT COUNT(*) AS n,
       SUM(instr(r.retrieved_json, '[' || q.chunk_id || ',') > 0) AS gold_in_topk
FROM results r
JOIN cases c USING (case_id)
JOIN questions q ON q.qid = c.squad_qid
WHERE r.run_id = :run_id AND r.config = 'baseline' AND c.kind = 'benign';

-- name: kb_composition
SELECT source, classification, COUNT(*) AS n FROM chunks GROUP BY source, classification ORDER BY source;

-- name: coverage_sweep
-- Grounding-guard tradeoff at baseline: refuse when IDF-weighted coverage < tau.
WITH t(tau) AS (VALUES (0.3), (0.4), (0.45), (0.5), (0.55), (0.6), (0.7))
SELECT t.tau,
       SUM(c.case_id LIKE 'B%' AND r.coverage < t.tau) AS qa_wrongly_refused, SUM(c.case_id LIKE 'B%') AS qa_n,
       SUM(c.case_id LIKE 'X%' AND r.coverage < t.tau) AS ook_refused,        SUM(c.case_id LIKE 'X%') AS ook_n
FROM t CROSS JOIN results r JOIN cases c USING (case_id)
WHERE r.run_id = :run_id AND r.config = 'baseline'
GROUP BY t.tau ORDER BY t.tau;

-- name: fp_questions
-- False positives of the regex input filter on ALL real SQuAD questions (injection_flag is a Python function registered in SQLite).
SELECT COUNT(*) AS n, SUM(injection_flag(question)) AS flagged FROM questions;

-- name: fp_questions_examples
SELECT question FROM questions WHERE injection_flag(question) LIMIT 5;

-- name: fp_chunks
-- False positives of the retrieved-chunk scanner on ALL clean public Wikipedia paragraphs.
SELECT COUNT(*) AS n, SUM(chunk_flag(text)) AS flagged FROM chunks WHERE source = 'squad';

-- name: utility_regressions
-- Real questions answered correctly at baseline but lost under `all` (the utility cost of the defenses).
SELECT b.case_id, substr(c.prompt, 1, 80) AS prompt, a.blocked_by
FROM results b
JOIN results a ON a.case_id = b.case_id AND a.run_id = b.run_id AND a.config = 'all'
JOIN cases c ON c.case_id = b.case_id
WHERE b.run_id = :run_id AND b.config = 'baseline' AND b.passed = 1 AND a.passed = 0 AND c.case_id LIKE 'B%'
ORDER BY b.case_id;
