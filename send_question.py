#!/usr/bin/env python3
"""Send one SC-300 question to an ntfy topic as a phone push, at a RANDOM time.

The scheduler runs this every 15 minutes across the window. Once per day this
script deterministically chooses one random minute inside each of five ~90-minute
blocks (so: 5 pushes/day, well spaced, unpredictable day to day). On each run it
checks whether "now" is one of today's chosen times; if not, it exits instantly.

No saved state: the daily choices are derived from the date, so every run that day
computes the same five times.
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
SLOTS_PER_DAY = 5
# ------------------------------------------------------

# Candidate grid: 15-min steps from 00:00 to 07:30 UTC == 08:00 to 15:30 Perth (AWST, UTC+8).
# That's indices 0..30. Split into 5 blocks; one random pick per block per day.
BLOCKS = [(0, 5), (6, 11), (12, 17), (18, 23), (24, 30)]

here = pathlib.Path(__file__).parent
questions = json.loads((here / "questions.json").read_text(encoding="utf-8"))
n = len(questions)


def chosen_index(date_ordinal: int, block: int, lo: int, hi: int) -> int:
    """Deterministic 'random' grid index within [lo, hi] for a given day+block."""
    h = hashlib.sha256(f"{date_ordinal}:{block}".encode()).hexdigest()
    return lo + (int(h, 16) % (hi - lo + 1))


def send(slot: int) -> None:
    day_number = (datetime.datetime.now(datetime.timezone.utc).date() - datetime.date(2024, 1, 1)).days
    counter = day_number * SLOTS_PER_DAY + slot
    q = questions[counter % n]
    o = q["options"]
    title = f"SC-300 - {q['tag']}"
    body = (
        f"{q['question']}\n\n"
        f"A. {o['A']}\nB. {o['B']}\nC. {o['C']}\nD. {o['D']}\n\n"
        f"-- think first --\nscroll down for the answer\n"
        f"\n\n\n\n"
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


# Manual test path: FORCE_SLOT bypasses the random gate and pushes immediately.
if FORCE_SLOT is not None:
    send(int(FORCE_SLOT))
    sys.exit(0)

# Random gate. Round "now" to the nearest 15-min grid point to absorb scheduler drift.
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

lo, hi = BLOCKS[block]
target = chosen_index(now.date().toordinal(), block, lo, hi)
if idx == target:
    send(block)
else:
    print(f"skip: idx={idx} not today's pick for block {block} (target={target})")
