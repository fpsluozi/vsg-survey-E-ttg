"""Google Sheets-backed persistence, replacing local-disk writes.

Streamlit Community Cloud's filesystem is ephemeral (wiped on every reboot /
redeploy), so responses can never be trusted to survive on local disk. Instead:

- One snapshot row per rater in the "<SPLIT>_<model>" tab, holding the full
  progress state as a JSON blob. Upserted (by email) on every answer — cheap,
  single API call, and safe against crashes/reboots mid-survey.
- On final submit, the same data is also expanded into one row per
  (image, question) in the "<SPLIT>_<model>_long" tab for direct analysis.

Requires st.secrets["gcp_service_account"] (the service account JSON, as a
TOML table) and st.secrets["sheet_id"] (the shared spreadsheet's ID).
"""
import json
from datetime import datetime, timezone

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def _client():
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=_SCOPES
    )
    return gspread.authorize(creds)


@st.cache_resource
def _spreadsheet():
    return _client().open_by_key(st.secrets["sheet_id"])


def _snapshot_ws(tab_name):
    return _spreadsheet().worksheet(tab_name)


def _long_ws(tab_name):
    return _spreadsheet().worksheet(f"{tab_name}_long")


def _find_row_by_email(ws, email):
    """1-indexed row number for this email in column A, or None."""
    try:
        cell = ws.find(email, in_column=1)
        return cell.row
    except gspread.exceptions.CellNotFound:
        return None


def save_snapshot(tab_name, model, email, started_at, answers, leak_order,
                   submitted, n_items):
    """Upsert this rater's full progress as one row (email keyed)."""
    ws = _snapshot_ws(tab_name)
    n_complete = sum(
        1 for v in answers.values()
        if all(v.get(q) for q in ("q1", "q2", "q3", "q4"))
    )
    progress = {"answers": answers, "leak_order": leak_order}
    row = [
        email, tab_name, model, started_at,
        datetime.now(timezone.utc).isoformat(timespec="seconds"),
        submitted, n_items, n_complete, json.dumps(progress),
    ]
    existing_row = _find_row_by_email(ws, email)
    if existing_row:
        ws.update(f"A{existing_row}:I{existing_row}", [row])
    else:
        ws.append_row(row)


def load_snapshot(tab_name, email):
    """Return {"answers":..., "leak_order":..., "started_at":..., "submitted":...} or None."""
    ws = _snapshot_ws(tab_name)
    existing_row = _find_row_by_email(ws, email)
    if not existing_row:
        return None
    values = ws.row_values(existing_row)
    if len(values) < 9:
        return None
    _, _, _, started_at, _updated_at, submitted, _n_items, _n_complete, progress_json = values[:9]
    try:
        progress = json.loads(progress_json)
    except json.JSONDecodeError:
        progress = {"answers": {}, "leak_order": {}}
    return {
        "answers": progress.get("answers", {}),
        "leak_order": progress.get("leak_order", {}),
        "started_at": started_at,
        "submitted": str(submitted).strip().lower() == "true",
    }


def write_long_rows(tab_name, model, email, items, answers, q4_text_fn):
    """Append one row per (image, question) to the long-format tab at submit."""
    ws = _long_ws(tab_name)
    submitted_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    qkeys = ["q1", "q2", "q3", "q4"]
    rows = []
    for it in items:
        a = answers.get(str(it["idx"]), {})
        for q in qkeys:
            qtext = {"q1": it["q1"], "q2": it["q2"], "q3": it["q3"],
                      "q4": q4_text_fn(it)}[q]
            rows.append([
                email, tab_name, model, it["idx"], it["prompt_id"],
                it["condition"], it["relation"], it["prompt"], it["image"].name,
                q, qtext, a.get(q, ""), submitted_at,
            ])
    ws.append_rows(rows, value_input_option="RAW")
