#!/usr/bin/env python3
"""Score a submission against the LexDye defined-terms benchmark answer key.

Usage:
  python3 score.py submissions/my-run.json      # one run, with details
  python3 score.py submissions/*.json           # leaderboard
  python3 score.py my-run.csv                   # CSV with columns: id,found (1/0)

Standard library only. Licensed under the MIT License (see LICENSE-CODE).
"""
import csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_key(benchmark):
    return json.loads((ROOT / benchmark / "answer-key.json").read_text(encoding="utf-8"))


def load_submission(path):
    p = Path(path)
    if p.suffix.lower() == ".csv":
        with p.open(newline="", encoding="utf-8") as f:
            found = [r["id"].strip().upper() for r in csv.DictReader(f)
                     if str(r.get("found", "")).strip().lower() in ("1", "yes", "true", "found")]
        return {"benchmark": "msa-2026-11", "reviewer": p.stem, "found": found}
    return json.loads(p.read_text(encoding="utf-8"))


def score(sub):
    key = load_key(sub.get("benchmark", "msa-2026-11"))
    scored = {e["id"]: e for e in key["errors"] if e["scored"]}
    all_ids = {e["id"] for e in key["errors"]}
    tricky = {t["id"] for t in key["tricky_but_correct"]}
    found = {i.strip().upper() for i in sub.get("found", [])}
    unknown = sorted(found - all_ids)
    hits = sorted(found & set(scored), key=lambda i: int(i[1:]))
    misses = sorted(set(scored) - found, key=lambda i: int(i[1:]))
    by_cat = {}
    for i, e in scored.items():
        c = by_cat.setdefault(e["category"], [0, 0])
        c[1] += 1
        c[0] += i in found
    flagged = sorted({i.strip().upper() for i in sub.get("flagged_correct_items", [])} & tricky)
    return dict(hits=hits, misses=misses, unknown=unknown, by_cat=by_cat,
                total=len(scored), flagged=flagged, scored=scored)


def main(paths):
    if not paths:
        print(__doc__)
        return 1
    rows = []
    for path in paths:
        if Path(path).name == "TEMPLATE.json":
            continue
        sub = load_submission(path)
        r = score(sub)
        rows.append((len(r["hits"]), r["total"], sub.get("reviewer", path), sub.get("prompt", ""), path))
        if len(paths) == 1:
            print(f"{sub.get('reviewer', path)}: {len(r['hits'])} / {r['total']} defined-term errors found\n")
            print("By category:")
            for cat, (got, of) in sorted(r["by_cat"].items()):
                print(f"  {cat:32} {got} / {of}")
            if r["misses"]:
                print("\nMissed:")
                for i in r["misses"]:
                    e = r["scored"][i]
                    print(f"  {i:4} {e['category']:32} {e['location']}")
            if r["flagged"]:
                print("\nFalse positives (flagged a tricky-but-correct item):", ", ".join(r["flagged"]))
            if r["unknown"]:
                print("\nIgnored (not scored or not in key):", ", ".join(r["unknown"]))
    if len(paths) > 1:
        rows.sort(key=lambda x: -x[0])
        print(f"{'Found':>7}  Reviewer | Prompt")
        for got, of, who, prompt, _ in rows:
            print(f"{got:>3} / {of}  {who} | {prompt[:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
