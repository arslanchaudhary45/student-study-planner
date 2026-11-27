# Student Study Planner

A small command-line app to create study schedules, subjects, exam dates,
and daily learning goals. Python 3.12, standard library only — no
third-party packages for the CLI; the web app adds Flask.

All data is stored in `data.json` next to `main.py`.

## Setup

```bash
cd student-study-planner
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Web app

```bash
cd student-study-planner
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 in your browser. The web app covers the
same features as the command line: add/list subjects, add/list exams with
upcoming-only and next-N-days filters and days-left badges, add study
sessions (start + end or duration) with a schedule view per date, and add,
complete and list daily goals per date. Set the `PORT` environment
variable to run on a different port.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests in `tests/` cover the service layer in `main.py`: subjects,
exams (including days-left badges and filters), study sessions (start+end
and duration forms, validation), schedules, goals (add/complete/counts),
and corrupted data files.

## Architecture

- `main.py` — the service layer: planner rules, validation and storage
  (typed functions, `PlannerError` on bad input). The `cmd_*` functions
  at the bottom are thin command-line wrappers around it.
- `app.py` — the Flask web UI: thin routes that validate HTTP input
  and call the service. No planner rules live in the routes.
- `templates/` + `static/` — the web pages and the shared design
  system (same layout, colors and components as the other projects).
- `data.json` — the data file (created on first use).

## Run

```bash
cd student-study-planner
python3 main.py --help
```

## Commands

```bash
# Subjects
python3 main.py add-subject Mathematics --description "Algebra and calculus"
python3 main.py list-subjects

# Exams
python3 main.py add-exam Mathematics 2026-12-15 --title "Midterm"
python3 main.py list-exams            # upcoming exams only
python3 main.py list-exams --all      # include past exams
python3 main.py list-exams --days 30  # exams within the next 30 days

# Study sessions / schedule (start+end, or duration in minutes)
python3 main.py add-session Mathematics 2026-11-28 --start 09:00 --end 10:30 --topic "Integration"
python3 main.py add-session Mathematics 2026-11-28 --duration 45 --topic "Derivatives"
python3 main.py schedule 2026-11-28   # schedule for a date
python3 main.py schedule              # today's schedule

# Daily goals
python3 main.py add-goal 2026-11-28 "Finish 20 integration problems"
python3 main.py goals                 # today's goals
python3 main.py goals 2026-11-28      # goals for a date
python3 main.py complete-goal 1       # mark goal #1 done
```

Dates use `YYYY-MM-DD`, times use 24-hour `HH:MM`. Exams and sessions
require the subject to exist first — add it with `add-subject`.
