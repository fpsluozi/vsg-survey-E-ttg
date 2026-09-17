"""VSG Human Survey E — ttg model, 26 images (13 prompts x base/Gemma4 condition).

Run:  streamlit run app.py            (then open http://localhost:8501)
"""
import csv
import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from items import load_items, N_ITEMS

SPLIT_LABEL = "E"
TITLE = f"VSG Human Survey {SPLIT_LABEL}"

OUT_DIR = Path(__file__).resolve().parent / "responses"
OUT_DIR.mkdir(exist_ok=True)

SCALE = [1, 2, 3, 4, 5]
QKEYS = ["q1", "q2", "q3", "q4"]

st.set_page_config(page_title=TITLE, page_icon="🖼️", layout="centered")


# ----------------------------------------------------------------- persistence
def slug(email):
    return re.sub(r"[^a-zA-Z0-9._-]", "_", email.strip().lower()) or "anonymous"


def save_path(email):
    return OUT_DIR / f"{slug(email)}.json"


def save_progress():
    """Atomic snapshot of everything answered so far. Called on every answer."""
    email = st.session_state.email
    if not email:
        return
    payload = {
        "email": email,
        "split": SPLIT_LABEL,
        "started_at": st.session_state.started_at,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_items": N_ITEMS,
        "answers": st.session_state.answers,
        "leak_order": st.session_state.leak_order,
        "submitted": st.session_state.submitted,
    }
    p = save_path(email)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(p)


def load_progress(email):
    p = save_path(email)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return None


def write_csv(email, items):
    """Long-format CSV: one row per (image, question)."""
    path = OUT_DIR / f"{slug(email)}.csv"
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["email", "split", "idx", "prompt_id", "condition", "relation",
                    "prompt", "image", "question_id", "question_text", "rating"])
        for it in items:
            a = st.session_state.answers.get(str(it["idx"]), {})
            for q in QKEYS:
                qtext = {"q1": it["q1"], "q2": it["q2"], "q3": it["q3"],
                          "q4": q4_text(it)}[q]
                w.writerow([email, SPLIT_LABEL, it["idx"], it["prompt_id"],
                            it["condition"], it["relation"], it["prompt"],
                            it["image"].name, q, qtext, a.get(q, "")])
    return path


# --------------------------------------------------------------- session state
def init_state():
    st.session_state.setdefault("email", "")
    st.session_state.setdefault("answers", {})       # {"0": {"q1": 3, ...}, ...}
    st.session_state.setdefault("leak_order", {})     # {"0": [2, 0, 1], ...}
    st.session_state.setdefault("pos", 0)
    st.session_state.setdefault("started_at", "")
    st.session_state.setdefault("submitted", False)
    st.session_state.setdefault("page", "welcome")


init_state()
ITEMS = load_items()


def get_leak_order(item):
    """Shuffled, stable-per-session order of the 3 leak attributes for Q4."""
    key = str(item["idx"])
    order = st.session_state.leak_order.get(key)
    n = len(item["leak_attributes"])
    if order is None or sorted(order) != list(range(n)):
        order = list(range(n))
        random.shuffle(order)
        st.session_state.leak_order[key] = order
    return order


def q4_text(item):
    """Q4 sentence with its 3 leak attributes reordered per the session's shuffle."""
    order = get_leak_order(item)
    attrs = [item["leak_attributes"][i] for i in order]
    lead_in = item["q4"].split(":", 1)[0]
    return f"{lead_in}: {'; '.join(attrs)}."


def answered(idx):
    a = st.session_state.answers.get(str(idx), {})
    return all(a.get(q) for q in QKEYS)


def incomplete_items():
    return [it["idx"] for it in ITEMS if not answered(it["idx"])]


# -------------------------------------------------------------------- welcome
if st.session_state.page == "welcome":
    st.title(TITLE)
    st.markdown(
        f"You will see **{N_ITEMS} images**, each showing a visual simile prompt "
        "(e.g. \"a moon that looks like a boat\"). For each image, answer **4 questions** "
        "on a 1–5 scale, where **1 = strongly disagree** and **5 = strongly agree**.\n\n"
        "Judge only what you actually see in the image. All questions are required. "
        "Your progress is saved automatically, so you can close the tab and come back "
        "with the same email address."
    )
    email = st.text_input("Your email", value=st.session_state.email,
                          placeholder="you@example.com")
    valid = bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()))
    if email and not valid:
        st.warning("Please enter a valid email address.")

    prior = load_progress(email) if valid else None
    if prior:
        done = sum(1 for k, v in prior["answers"].items() if all(v.get(q) for q in QKEYS))
        st.info(f"Found earlier progress for this email: **{done}/{N_ITEMS}** images completed.")

    if st.button("Start", type="primary", disabled=not valid):
        st.session_state.email = email.strip()
        if prior:
            st.session_state.answers = prior["answers"]
            st.session_state.leak_order = prior.get("leak_order", {})
            st.session_state.started_at = prior.get("started_at", "")
            st.session_state.submitted = prior.get("submitted", False)
            nxt = incomplete_items()
            st.session_state.pos = next(
                (i for i, it in enumerate(ITEMS) if it["idx"] == nxt[0]), 0) if nxt else 0
        if not st.session_state.started_at:
            st.session_state.started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        st.session_state.page = "survey"
        st.rerun()
    st.stop()


# ----------------------------------------------------------------------- done
if st.session_state.page == "done":
    st.title("Thank you — responses recorded")
    st.success(f"All {N_ITEMS} images annotated by **{st.session_state.email}**.")
    csv_path = OUT_DIR / f"{slug(st.session_state.email)}.csv"
    st.markdown(f"Saved to `{csv_path}` and `{save_path(st.session_state.email)}`.")
    if csv_path.exists():
        st.download_button("Download my responses (CSV)", csv_path.read_bytes(),
                           file_name=csv_path.name, mime="text/csv")
    if st.button("Back to the images"):
        st.session_state.page = "survey"
        st.rerun()
    st.stop()


# --------------------------------------------------------------------- survey
pos = st.session_state.pos
item = ITEMS[pos]
key = str(item["idx"])
ans = st.session_state.answers.setdefault(key, {})

with st.sidebar:
    st.markdown(f"**{st.session_state.email}**")
    done = N_ITEMS - len(incomplete_items())
    st.progress(done / N_ITEMS, text=f"{done} / {N_ITEMS} complete")
    jump = st.number_input("Jump to image #", min_value=1, max_value=N_ITEMS,
                           value=pos + 1, step=1)
    if jump - 1 != pos:
        st.session_state.pos = int(jump) - 1
        st.rerun()
    st.caption("Grid — ✅ done, ⬜ not yet")
    grid = "".join("✅" if answered(it["idx"]) else "⬜" for it in ITEMS)
    st.markdown("\n".join(grid[i:i + 10] for i in range(0, len(grid), 10)))

st.markdown(f"### Image {pos + 1} of {N_ITEMS}")
st.caption(f'Prompt: "{item["prompt"]}"')
if item["image"].exists():
    st.image(str(item["image"]), width="stretch")
else:
    st.error(f"Missing image: {item['image']}")

st.markdown(
    f'Intention: We want to realistically illustrate a special kind of {item["A"]}, '
    f'which bears some resemblance to {item["B"]}.'
)

st.divider()

changed = False

# --- Q1 alone first ---------------------------------------------------------
st.markdown(f"**{item['q1']}** <span style='color:#d33'>*</span>", unsafe_allow_html=True)
prev = ans.get("q1")
val = st.radio(
    item["q1"], SCALE, index=(SCALE.index(prev) if prev in SCALE else None),
    key=f"{key}_q1", horizontal=True, label_visibility="collapsed",
    captions=["Strongly disagree", "", "", "", "Strongly agree"],
)
if val != prev:
    ans["q1"] = val
    changed = True

st.divider()

# --- Q2-Q4 together ----------------------------------------------------------
QUESTIONS = [
    ("q2", item["q2"]),
    ("q3", item["q3"]),
    ("q4", q4_text(item)),
]
for qk, qtext in QUESTIONS:
    st.markdown(f"**{qtext}** <span style='color:#d33'>*</span>", unsafe_allow_html=True)
    prev = ans.get(qk)
    val = st.radio(
        qtext, SCALE, index=(SCALE.index(prev) if prev in SCALE else None),
        key=f"{key}_{qk}", horizontal=True, label_visibility="collapsed",
        captions=["Strongly disagree", "", "", "", "Strongly agree"],
    )
    if val != prev:
        ans[qk] = val
        changed = True
    st.write("")

if changed:
    save_progress()

st.divider()
c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    if st.button("← Previous", disabled=pos == 0, width="stretch"):
        st.session_state.pos -= 1
        st.rerun()
with c2:
    if st.button("Next →", disabled=pos >= N_ITEMS - 1, type="primary",
                 width="stretch"):
        if not answered(item["idx"]):
            st.warning("Please answer all 4 questions before moving on.")
        else:
            st.session_state.pos += 1
            st.rerun()
with c3:
    missing = incomplete_items()
    if st.button(f"Submit all {N_ITEMS}", disabled=bool(missing), width="stretch"):
        st.session_state.submitted = True
        save_progress()
        write_csv(st.session_state.email, ITEMS)
        st.session_state.page = "done"
        st.rerun()

if incomplete_items():
    miss = incomplete_items()
    st.caption(f"{len(miss)} image(s) still incomplete — first is #{miss[0] + 1}. "
               "Submit unlocks when all are answered.")
