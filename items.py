"""Build the 26 survey pages (13 prompts x base/Gemma4 condition) for the ttg model.

Sources:
  vsg_survey_items.csv        Q1-Q4 sentence text (13 prompts x 4 items = 52 rows).
  vsgv2_full_finalized.jsonl  short leak_attributes phrases used to reshuffle Q4.
Images: survey_images/ttg_base/<id>.png and survey_images/ttg_gemma/<id>.png.

Page order: for each prompt, in CSV order, the base image immediately
followed by its Gemma4-augmented image (condition is hidden from raters).
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "vsg_survey_items.csv"
JSONL_PATH = ROOT / "vsgv2_full_finalized.jsonl"
IMG_ROOT = ROOT / "survey_images"
MODEL = "ttg"
CONDITIONS = ["base", "gemma"]
N_PROMPTS = 13
N_ITEMS = N_PROMPTS * len(CONDITIONS)


def _image_path(condition, prompt_id):
    return IMG_ROOT / f"{MODEL}_{condition}" / f"{prompt_id}.png"


def _load_jsonl_rows():
    """id -> full jsonl row (has A, B, prompt, leak_attributes, ...)."""
    out = {}
    with JSONL_PATH.open() as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            out[row["id"]] = row
    return out


def load_items():
    """Returns a list of 26 page dicts, one per (prompt, condition)."""
    rows_by_id = {}
    order = []
    with CSV_PATH.open(newline="") as f:
        for row in csv.DictReader(f):
            pid = row["id"]
            if pid not in rows_by_id:
                rows_by_id[pid] = {}
                order.append(pid)
            rows_by_id[pid][row["item"]] = row

    jsonl_rows = _load_jsonl_rows()

    items = []
    idx = 0
    for pid in order:
        by_item = rows_by_id[pid]
        q1 = by_item["Q1"]
        q2 = by_item["Q2"]
        q3 = by_item["Q3"]
        q4 = by_item["Q4"]
        jr = jsonl_rows[pid]
        for condition in CONDITIONS:
            items.append({
                "idx": idx,
                "prompt_id": pid,
                "condition": condition,
                "relation": q1["relation"],
                "prompt": q1["prompt"],
                "A": jr["A"],
                "B": jr["B"],
                "image": _image_path(condition, pid),
                "q1": f'This image is a good depiction of {q1["prompt"]}.',
                "q2": q2["text"],
                "q3": "In this image, " + q3["text"][0].lower() + q3["text"][1:],
                "q4": "In this image, " + q4["text"][0].lower() + q4["text"][1:],
                "leak_attributes": [la["attribute"] for la in jr["leak_attributes"]],
            })
            idx += 1
    return items


if __name__ == "__main__":
    for it in load_items():
        print(f'{it["idx"]:>3}  {it["prompt_id"]:<10} {it["condition"]:<6} {it["relation"]:<24} {it["prompt"]}')
