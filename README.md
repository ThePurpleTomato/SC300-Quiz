# SC-300 push quiz

Pushes one SC-300 exam question to your phone 5 times a day, at **random times**
between 8:00am and 3:30pm Perth time (weekdays). The notification shows the question
and options; the answer and full explanation sit below, so you think first and then
scroll to reveal.

Free, runs without a server, works on **iPhone** and Android.

## How the random timing works

The window (8:00-15:30) is split into five ~90-minute blocks. Each day the script
picks one random minute inside each block, so you get exactly 5 pushes a day, spread
out, but at times you can't predict from one day to the next. (Worst case two pushes
land ~15 min apart at a block boundary; usually they're well spaced.)

The scheduler just runs a quick check every 15 minutes; the runs that aren't a
chosen time exit in about a second. The daily choices come from the date, so there's
no saved state to manage.

## Files

- **questions.json** - the question bank (100 questions, all four domains).
- **send_question.py** - decides whether now is a chosen time and, if so, pushes.
- **.github/workflows/sc300-quiz.yml** - runs the check every 15 min in the window.

Question selection is sequential: it walks the whole bank in order and only repeats
after all 100 (about 4 weeks of weekdays at 5/day).

## Setup (about 5 minutes)

1. **Install the ntfy app** on your iPhone (App Store, search "ntfy").

2. **Pick a topic name** - long and random so nobody stumbles on it, e.g.
   `sc300-quiz-7fK29qLp4m`. In the app, subscribe to that exact topic. (The default
   ntfy.sh server is public, so a random name keeps it yours. iPhone push works on
   the default server with no extra config - the self-hosted caveats in ntfy's docs
   don't apply here.)

3. **Create a GitHub repo** (free). A **public** repo is simplest - Actions minutes
   are unlimited on public repos, and the content isn't secret. Upload these files,
   keeping the layout: the workflow must stay at `.github/workflows/sc300-quiz.yml`.

4. **Add your topic as a secret:** repo **Settings -> Secrets and variables ->
   Actions -> New repository secret**. Name `NTFY_TOPIC`, value = your topic name.

5. **Test it now:** **Actions** tab -> "SC-300 push quiz" -> **Run workflow**
   (optionally set a slot 0-4). A question should hit your phone within seconds.
   A manual run always pushes; the random gate only applies to the scheduled runs.

From then on it fires on its own at random times each weekday.

## Tweaks

- **Shift the window:** edit the two `cron:` lines (they're in UTC; Perth = UTC+8,
  so subtract 8 hours) and the `BLOCKS` / index range in the script if you change
  the span.
- **Run all 7 days:** change `1-5` to `*` in both cron lines.
- **More/fewer per day:** change the number of `BLOCKS` and `SLOTS_PER_DAY` in the
  script.

## Honest limitations

- **Timing isn't to the minute.** GitHub's scheduled runs can be delayed several
  minutes (occasionally more) when their infrastructure is busy; the script rounds to
  the nearest 15-min grid point to absorb that. Rarely, a heavily-delayed or dropped
  run could shift or miss a push. Fine for study nudges.
- **GitHub disables schedules on idle repos.** If a repo has no activity for 60 days,
  scheduled workflows pause until you act in the repo. A push every couple of months
  keeps it alive.
- **It's one-way.** You self-mark by thinking, then scrolling to the answer. For
  adaptive drilling on your weak spots, bring results back to a chat.
- **Bank size.** 100 questions repeat after about 4 weeks of weekdays. Ask any
  time and I can expand it further or weight it to your weak spots.

## No GitHub? Two alternatives

- **Any always-on machine:** run `send_question.py` every 15 min via cron
  (Mac/Linux) or Task Scheduler (Windows), with `NTFY_TOPIC` set. The random gate
  works the same way.
- **iPhone, no code:** Shortcuts can run time-based automations that show a
  notification - lighter to set up, but you maintain the questions by hand in the
  shortcut, and truly-random timing is harder there.
