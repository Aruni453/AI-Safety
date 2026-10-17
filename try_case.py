"""Run one (or all) test cases against a defense config and print the answer + PASS/FAIL.

    python try_case.py O01                 # case O01 on baseline AND all
    python try_case.py O05 spotlight       # case O05 on one config
    python try_case.py --list              # list all 46 cases
    python try_case.py --all baseline      # run every case on one config
Configs: baseline input_filter acl context_scan spotlight spotlight+sanitize output_filter grounding all
Run from the project folder, after `python -m harness.build`.
"""
import json
import sqlite3
import sys

from harness.run import evaluate
from rag.assistant import Assistant
from rag.defenses import CONFIGS
from rag.llm import MockNaiveLLM

con = sqlite3.connect("data/bench.db")
CASES = {r[0]: r for r in con.execute("SELECT case_id, category, kind, prompt, checks_json FROM cases ORDER BY case_id")}


def run(case_id, cfg):
    cid, cat, kind, prompt, checks = CASES[case_id]
    res = Assistant(MockNaiveLLM(), CONFIGS[cfg]).ask(prompt)
    ok, why = evaluate({"checks": json.loads(checks)}, res)
    print(f"[{case_id} | {cat} | {kind} | {cfg}] {'PASS' if ok else 'FAIL'}  ({why})")
    print(f"  prompt : {prompt}")
    print(f"  answer : {res.answer[:160]!r}")
    if res.trace.blocked_by:
        print(f"  blocked: {res.trace.blocked_by}")


args = sys.argv[1:]
if not args or args[0] == "--list":
    for c in CASES.values():
        print(f"{c[0]:4} {c[1]:21} {c[2]:7} {c[3][:75]}")
elif args[0] == "--all":
    for cid in CASES:
        run(cid, args[1] if len(args) > 1 else "baseline")
else:
    cid = args[0].upper()
    for cfg in ([args[1]] if len(args) > 1 else ["baseline", "all"]):
        run(cid, cfg)
