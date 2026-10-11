-- Knowledge base: public SQuAD v1.1 (dev) paragraphs + clearly-labelled synthetic rows planted for the tests.
CREATE TABLE chunks (
    chunk_id       INTEGER PRIMARY KEY,
    article        TEXT NOT NULL,
    para_idx       INTEGER NOT NULL,
    source         TEXT NOT NULL CHECK (source IN ('squad', 'synthetic_confidential', 'synthetic_poison')),
    classification TEXT NOT NULL CHECK (classification IN ('public', 'confidential')),
    base_chunk_id  INTEGER,            -- for poisoned rows: the real paragraph they imitate
    text           TEXT NOT NULL
);

-- Full-text index (BM25 ranking) over the chunk text; porter stemming.
CREATE VIRTUAL TABLE chunks_fts USING fts5(
    text, content='chunks', content_rowid='chunk_id', tokenize='porter unicode61'
);

-- Every public SQuAD question with its gold answers (used to build benign cases + false-positive scan).
CREATE TABLE questions (
    qid          TEXT PRIMARY KEY,
    chunk_id     INTEGER NOT NULL REFERENCES chunks(chunk_id),
    article      TEXT NOT NULL,
    question     TEXT NOT NULL,
    answers_json TEXT NOT NULL
);

CREATE TABLE cases (
    case_id     TEXT PRIMARY KEY,
    category    TEXT NOT NULL CHECK (category IN ('grounding', 'data_leakage', 'instruction_override')),
    kind        TEXT NOT NULL CHECK (kind IN ('benign', 'attack')),
    prompt      TEXT NOT NULL,
    checks_json TEXT NOT NULL,
    note        TEXT,
    squad_qid   TEXT REFERENCES questions(qid)
);

CREATE TABLE runs (
    run_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    llm        TEXT NOT NULL,
    started_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE results (
    run_id         INTEGER NOT NULL REFERENCES runs(run_id),
    config         TEXT NOT NULL,
    case_id        TEXT NOT NULL REFERENCES cases(case_id),
    passed         INTEGER NOT NULL CHECK (passed IN (0, 1)),
    reason         TEXT,
    answer         TEXT,
    blocked_by     TEXT,
    retrieved_json TEXT,
    dropped_json   TEXT,
    coverage       REAL,
    PRIMARY KEY (run_id, config, case_id)
);
