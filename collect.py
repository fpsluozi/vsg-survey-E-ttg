"""Merge every annotator's autosave into one long-format CSV + a per-item summary.

    python collect.py            -> responses/ALL_responses.csv, responses/ALL_summary.csv
"""
import csv
import json
import statistics
from pathlib import Path

from items import load_items, N_ITEMS

HERE = Path(__file__).resolve().parent
OUT = HERE / "responses"
QKEYS = ["q1", "q2", "q3", "q4"]


def leak_text(item, order):
    attrs = item["leak_attributes"]
    if order:
        attrs = [attrs[i] for i in order]
    lead_in = item["q4"].split(":", 1)[0]
    return f"{lead_in}: {'; '.join(attrs)}."


def main():
    items = {it["idx"]: it for it in load_items()}
    files = sorted(p for p in OUT.glob("*.json") if not p.name.startswith("ALL_"))
    if not files:
        print(f"No responses yet in {OUT}")
        return

    rows = []
    per_q = {}          # (idx, qk) -> [ratings]
    for p in files:
        d = json.loads(p.read_text())
        email = d.get("email", p.stem)
        leak_order = d.get("leak_order", {})
        complete = sum(1 for v in d.get("answers", {}).values()
                       if all(v.get(q) for q in QKEYS))
        print(f"{email:<40} {complete:>3}/{N_ITEMS} complete"
              f"{'  [submitted]' if d.get('submitted') else ''}")
        for k, a in d.get("answers", {}).items():
            idx = int(k)
            it = items.get(idx)
            if it is None:
                continue
            qtext = {
                "q1": it["q1"], "q2": it["q2"], "q3": it["q3"],
                "q4": leak_text(it, leak_order.get(k)),
            }
            for q in QKEYS:
                if not a.get(q):
                    continue
                rows.append([email, d.get("submitted", False), idx, it["prompt_id"],
                             it["condition"], it["relation"], it["prompt"],
                             it["image"].name, q, qtext[q], a[q]])
                per_q.setdefault((idx, q), []).append(a[q])

    all_csv = OUT / "ALL_responses.csv"
    with all_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["email", "submitted", "idx", "prompt_id", "condition", "relation",
                    "prompt", "image", "question_id", "question_text", "rating"])
        w.writerows(sorted(rows, key=lambda r: (r[2], r[8], r[0])))

    sum_csv = OUT / "ALL_summary.csv"
    with sum_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idx", "prompt_id", "condition", "relation", "question_id",
                    "n", "mean", "median", "stdev"])
        for (idx, q), vals in sorted(per_q.items()):
            it = items[idx]
            w.writerow([idx, it["prompt_id"], it["condition"], it["relation"], q,
                        len(vals), round(statistics.mean(vals), 3),
                        statistics.median(vals),
                        round(statistics.stdev(vals), 3) if len(vals) > 1 else ""])

    print(f"\n{len(rows)} ratings from {len(files)} annotator(s)")
    print(f"  {all_csv}")
    print(f"  {sum_csv}")


if __name__ == "__main__":
    main()
