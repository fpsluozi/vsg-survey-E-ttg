"""Pull this split's long-format responses from the shared Google Sheet and
write a local per-item summary CSV.

Requires a local .streamlit/secrets.toml with [gcp_service_account] and
sheet_id (the same secrets used by the deployed app) or the
GOOGLE_APPLICATION_CREDENTIALS + SHEET_ID environment variables.

    python collect.py            -> ALL_summary.csv
"""
import csv
import os
import statistics
import tomllib
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

HERE = Path(__file__).resolve().parent
SPLIT_LABEL = "E"
MODEL = "ttg"
SHEET_TAB = f"{SPLIT_LABEL}_{MODEL}"

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _client_and_sheet_id():
    secrets_path = HERE / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        with secrets_path.open("rb") as f:
            secrets = tomllib.load(f)
        creds = Credentials.from_service_account_info(
            secrets["gcp_service_account"], scopes=_SCOPES
        )
        sheet_id = secrets["sheet_id"]
    else:
        key_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
        creds = Credentials.from_service_account_file(key_path, scopes=_SCOPES)
        sheet_id = os.environ["SHEET_ID"]
    return gspread.authorize(creds), sheet_id


def main():
    gc, sheet_id = _client_and_sheet_id()
    sh = gc.open_by_key(sheet_id)
    ws = sh.worksheet(f"{SHEET_TAB}_long")
    records = ws.get_all_records()
    if not records:
        print(f"No responses yet in tab {SHEET_TAB}_long")
        return

    all_csv = HERE / "ALL_responses.csv"
    with all_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(list(records[0].keys()))
        for r in records:
            w.writerow(list(r.values()))

    per_q = {}   # (idx, question_id) -> [ratings]
    meta = {}    # (idx, question_id) -> (prompt_id, condition, relation)
    for r in records:
        rating = r.get("rating")
        if rating in (None, ""):
            continue
        key = (r["idx"], r["question_id"])
        per_q.setdefault(key, []).append(float(rating))
        meta[key] = (r["prompt_id"], r["condition"], r["relation"])

    sum_csv = HERE / "ALL_summary.csv"
    with sum_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idx", "prompt_id", "condition", "relation", "question_id",
                    "n", "mean", "median", "stdev"])
        for (idx, q), vals in sorted(per_q.items()):
            prompt_id, condition, relation = meta[(idx, q)]
            w.writerow([idx, prompt_id, condition, relation, q,
                        len(vals), round(statistics.mean(vals), 3),
                        statistics.median(vals),
                        round(statistics.stdev(vals), 3) if len(vals) > 1 else ""])

    emails = sorted({r["email"] for r in records if r.get("email")})
    print(f"{len(records)} response rows from {len(emails)} rater(s): {', '.join(emails)}")
    print(f"  {all_csv}")
    print(f"  {sum_csv}")


if __name__ == "__main__":
    main()
