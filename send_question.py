#!/usr/bin/env python3
"""Send one SC-300 question to an ntfy topic as a phone push, at a RANDOM time.

The scheduler runs this every 15 minutes across the window. Once per day this
script deterministically chooses one random minute inside each of five ~90-minute
blocks (so: 5 pushes/day, well spaced, unpredictable day to day). On each run it
checks whether "now" is at or past one of today's chosen times AND that block has
not already fired today; if neither, it exits instantly.

State: a small state.json records today's date and which blocks have already
fired. When the stored date is not today, the fired list resets (daily reset).
The workflow restores/saves state.json via the Actions cache (keyed by date),
so it survives between runs without committing to the repo. A date-keyed cache
miss at midnight gives the daily reset for free.
"""
import hashlib
import json
import os
import datetime
import pathlib
import sys
import urllib.request

# ---- config (override via environment variables) ----
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "REPLACE-WITH-YOUR-TOPIC")
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")
FORCE_SLOT = os.environ.get("FORCE_SLOT")   # set 0..4 for a manual test push
# Blank lines between the question and the hidden answer. Sized for an iPhone 16
# expanded notification (~44 chars/line): shortest question block ~11 lines, so
# 40 - 11 + 3 = 32 keeps the answer below the fold on the shortest question too.
# Bump it if the answer still shows; drop it if the scroll is too long.
GAP_LINES = int(os.environ.get("GAP_LINES", "32"))
SLOTS_PER_DAY = 5
# ------------------------------------------------------

# Candidate grid: 15-min steps from 00:00 to 07:30 UTC == 08:00 to 15:30 Perth (AWST, UTC+8).
# That's indices 0..30. Split into 5 blocks; one random pick per block per day.
BLOCKS = [(0, 5), (6, 11), (12, 17), (18, 23), (24, 30)]

here = pathlib.Path(__file__).parent
STATE_PATH = here / "state.json"
questions = json.loads((here / "questions.json").read_text(encoding="utf-8"))
n = len(questions)


def chosen_index(date_ordinal: int, block: int, lo: int, hi: int) -> int:
    """Deterministic 'random' grid index within [lo, hi] for a given day+block."""
    h = hashlib.sha256(f"{date_ordinal}:{block}".encode()).hexdigest()
    return lo + (int(h, 16) % (hi - lo + 1))


def load_state(today_iso: str) -> dict:
    """Read state.json, resetting fired[] if the stored date is not today."""
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}
    if state.get("date") != today_iso:
        # New day (or no/corrupt state): reset.
        state = {"date": today_iso, "fired": []}
    state.setdefault("fired", [])
    return state


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def send(slot: int) -> None:
    day_number = (datetime.datetime.now(datetime.timezone.utc).date() - datetime.date(2024, 1, 1)).days
    counter = day_number * SLOTS_PER_DAY + slot
    q = questions[counter % n]
    o = q["options"]
    title = f"SC-300 - {q['tag']}"
    gap = "\n" * GAP_LINES  # blank lines pushing the answer below the fold
    body = (
        f"{q['question']}\n\n"
        f"A. {o['A']}\nB. {o['B']}\nC. {o['C']}\nD. {o['D']}\n\n"
        f"-- think first --\nscroll down for the answer\n"
        f"{gap}"
        f"Answer: {q['answer']}\n\n{q['explanation']}"
    )
    req = urllib.request.Request(
        f"{NTFY_SERVER}/{NTFY_TOPIC}",
        data=body.encode("utf-8"),
        headers={"Title": title, "Tags": "books", "Priority": "default"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(f"SENT ntfy {resp.status} | slot={slot} | id={q['id']} | index={counter % n}")


# Manual test path: FORCE_SLOT bypasses the gate and pushes immediately.
# Note: on scheduled runs the runner sets FORCE_SLOT to "" (empty string), not
# None, so we test truthiness rather than `is not None`.
if FORCE_SLOT and FORCE_SLOT.strip():
    send(int(FORCE_SLOT.strip()))
    sys.exit(0)

# State-file gate. Fire if now is at or past today's target for this block and
# the block hasn't already fired today. Round "now" to the nearest 15-min grid
# point to absorb scheduler drift.
now = datetime.datetime.now(datetime.timezone.utc)
mins = now.hour * 60 + now.minute
idx = round(mins / 15)
if idx < 0 or idx > 30:
    print(f"skip: outside window (idx={idx})")
    sys.exit(0)

block = next((b for b, (lo, hi) in enumerate(BLOCKS) if lo <= idx <= hi), None)
if block is None:
    print(f"skip: no block for idx={idx}")
    sys.exit(0)

today_iso = now.date().isoformat()
state = load_state(today_iso)

if block in state["fired"]:
    print(f"skip: block {block} already fired today")
    save_state(state)  # rewrite to ensure a possible date-reset is persisted
    sys.exit(0)

lo, hi = BLOCKS[block]
target = chosen_index(now.date().toordinal(), block, lo, hi)

if idx >= target:
    send(block)
    state["fired"].append(block)
    save_state(state)
    print(f"fired: block {block} at idx={idx} (target={target})")
else:
    print(f"skip: idx={idx} before today's target for block {block} (target={target})")
    save_state(state)  # persist any date reset even when not firing
