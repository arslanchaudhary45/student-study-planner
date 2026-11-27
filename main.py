#!/usr/bin/env python3
"""Student Study Planner — subjects, exams, study sessions and daily
learning goals. Data is stored in ``data.json`` next to this file.
Standard library only.

Architecture
------------
This module is the **service layer**: pure functions that own the data
and the rules (``load_data`` / ``save_data`` plus ``add_subject``,
``add_exam``, ``add_session``, ``add_goal``, ``complete_goal`` and the
list/schedule helpers). They raise :class:`PlannerError` on bad input
or a missing item instead of printing or exiting, so the
command-line app and the Flask web app (``app.py``) can both use them.

The ``cmd_*`` functions at the bottom are the thin command-line
wrappers: they turn parsed arguments into service calls and print the
results. ``app.py`` does the same for HTTP requests.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "data.json"

DEFAULT_START = time(9, 0)


class PlannerError(ValueError):
    """Raised when a planner operation is invalid (bad input, missing item)."""


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def empty_data() -> dict:
    """Return a fresh, empty planner store."""
    return {"subjects": [], "exams": [], "sessions": [], "goals": [],
            "next_subject_id": 1, "next_exam_id": 1,
            "next_session_id": 1, "next_goal_id": 1}


def load_data() -> dict:
    """Load the planner store from :data:`DATA_FILE`.

    Returns an empty store when the file does not exist yet, and also
    when it is corrupted (a warning is printed to stderr in that case).
    Older files missing keys are backfilled with defaults.
    """
    if not DATA_FILE.exists():
        return empty_data()
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Warning: could not read {DATA_FILE}: {exc}; starting "
              "with an empty store.", file=sys.stderr)
        return empty_data()
    if not isinstance(data, dict):
        return empty_data()
    for key, default in empty_data().items():
        data.setdefault(key, default)
    return data


def save_data(data: dict) -> None:
    """Persist ``data`` to :data:`DATA_FILE` as indented JSON."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


# ---------------------------------------------------------------------------
# Pure helpers (no I/O)
# ---------------------------------------------------------------------------

def parse_date(value: str, label: str = "date") -> date:
    """Parse a ``YYYY-MM-DD`` string into a :class:`datetime.date`.

    Raises :class:`PlannerError` on bad input. (``argparse`` treats a
    ``ValueError`` from a ``type=`` callable as an invalid value, so
    this doubles as the CLI date parser.)
    """
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise PlannerError(f"invalid {label} {value!r}: use YYYY-MM-DD")


def parse_time(value: str, label: str = "time") -> time:
    """Parse a ``HH:MM`` string into a :class:`datetime.time`.

    Raises :class:`PlannerError` on bad input. (``argparse`` treats a
    ``ValueError`` from a ``type=`` callable as an invalid value, so
    this doubles as the CLI time parser.)
    """
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        raise PlannerError(f"invalid {label} {value!r}: use HH:MM (24-hour)")


def find_subject(data: dict, name: str) -> dict | None:
    """Return the subject named ``name`` (case-insensitive), or ``None``."""
    for subject in data["subjects"]:
        if subject["name"].lower() == name.lower():
            return subject
    return None


def find_goal(data: dict, goal_id: int) -> dict | None:
    """Return the goal with ``goal_id``, or ``None`` when it is missing."""
    for goal in data["goals"]:
        if goal["id"] == goal_id:
            return goal
    return None


def exam_days_left(exam: dict, today: date | None = None) -> int:
    """Return the days from ``today`` until ``exam``'s date (negative
    when the exam is in the past)."""
    today = today or date.today()
    return (parse_date(exam["date"]) - today).days


def exam_badge(days_left: int) -> tuple[str, str]:
    """Return ``(label, badge)`` for an exam's days-left.

    Labels are like ``"Today"``, ``"in 3d"`` or ``"2d ago"``; badges
    are the matching CSS badge classes (``red`` / ``amber`` /
    ``indigo``).
    """
    if days_left < 0:
        return f"{-days_left}d ago", "red"
    if days_left == 0:
        return "Today", "red"
    if days_left <= 7:
        return f"in {days_left}d", "amber"
    return f"in {days_left}d", "indigo"


def with_exam_status(exam: dict, today: date | None = None) -> dict:
    """Return a copy of ``exam`` decorated with ``days_left`` and its
    badge label/class."""
    days_left = exam_days_left(exam, today)
    label, badge = exam_badge(days_left)
    return {**exam, "days_left": days_left,
            "badge_label": label, "badge_class": badge}


# ---------------------------------------------------------------------------
# Service operations (load, validate, mutate, save, return the result)
# ---------------------------------------------------------------------------

def add_subject(name: str, description: str = "") -> dict:
    """Create a subject, persist it and return it.

    Raises :class:`PlannerError` when the name is blank or a subject
    with that name already exists.
    """
    name = (name or "").strip()
    if not name:
        raise PlannerError("Subject name is required.")
    data = load_data()
    if find_subject(data, name):
        raise PlannerError(f"Subject {name!r} already exists.")
    subject = {"id": data["next_subject_id"], "name": name,
               "description": (description or "").strip()}
    data["subjects"].append(subject)
    data["next_subject_id"] += 1
    save_data(data)
    return subject


def list_subjects() -> list[dict]:
    """Return all subjects in the order they were added."""
    return load_data()["subjects"]


def add_exam(subject: str, exam_date: date, title: str = "") -> dict:
    """Create an exam for an existing subject, persist it and return it.

    Raises :class:`PlannerError` when the subject does not exist.
    """
    subject = (subject or "").strip()
    data = load_data()
    if not find_subject(data, subject):
        raise PlannerError(f"No subject named {subject!r}. "
                           "Add it first with add-subject.")
    exam = {"id": data["next_exam_id"], "subject": subject,
            "date": exam_date.isoformat(),
            "title": (title or "").strip() or f"{subject} exam"}
    data["exams"].append(exam)
    data["next_exam_id"] += 1
    save_data(data)
    return exam


def list_exams(upcoming_only: bool = True, days: int | None = None,
               today: date | None = None) -> list[dict]:
    """Return exams sorted by date, decorated with days-left and badges.

    With ``upcoming_only`` only exams on or after ``today`` are
    returned; ``days`` further limits to exams within the next N days.
    Raises :class:`PlannerError` on a negative ``days`` value.
    """
    today = today or date.today()
    if days is not None and days < 0:
        raise PlannerError("Days must be a non-negative number.")
    exams = sorted(load_data()["exams"], key=lambda e: e["date"])
    if upcoming_only:
        exams = [e for e in exams if parse_date(e["date"]) >= today]
    if days is not None:
        exams = [e for e in exams
                 if 0 <= (parse_date(e["date"]) - today).days <= days]
    return [with_exam_status(e, today) for e in exams]


def add_session(subject: str, session_date: date,
                start: time | None = None, end: time | None = None,
                duration: int | None = None, topic: str = "") -> dict:
    """Create a study session, persist it and return it.

    Give ``start`` and ``end``, or a ``duration`` in minutes (the
    start then defaults to 09:00). Raises :class:`PlannerError` when
    the subject does not exist, the end is not after the start, the
    duration is not positive, or neither form of time is given.
    """
    subject = (subject or "").strip()
    data = load_data()
    if not find_subject(data, subject):
        raise PlannerError(f"No subject named {subject!r}. "
                           "Add it first with add-subject.")
    if start and end:
        if end <= start:
            raise PlannerError("End time must be after start time.")
        minutes = (datetime.combine(date.min, end)
                   - datetime.combine(date.min, start)).seconds // 60
    elif duration:
        if duration <= 0:
            raise PlannerError("duration must be a positive number "
                               "of minutes.")
        start = start or DEFAULT_START
        end = (datetime.combine(date.min, start)
               + timedelta(minutes=duration)).time()
        minutes = duration
    else:
        raise PlannerError("give --start and --end, or --duration "
                           "(minutes).")
    session = {"id": data["next_session_id"], "subject": subject,
               "date": session_date.isoformat(),
               "start": start.strftime("%H:%M"),
               "end": end.strftime("%H:%M"),
               "duration_minutes": minutes,
               "topic": (topic or "").strip()}
    data["sessions"].append(session)
    data["next_session_id"] += 1
    save_data(data)
    return session


def schedule(day: date) -> dict:
    """Return the schedule for ``day``: ``{"sessions", "total_minutes"}``,
    with sessions sorted by start time."""
    day_str = day.isoformat()
    sessions = sorted(
        (s for s in load_data()["sessions"] if s["date"] == day_str),
        key=lambda s: s["start"])
    return {"sessions": sessions,
            "total_minutes": sum(s["duration_minutes"] for s in sessions)}


def add_goal(goal_date: date, text: str) -> dict:
    """Create a daily learning goal, persist it and return it.

    Raises :class:`PlannerError` when the goal text is blank.
    """
    text = (text or "").strip()
    if not text:
        raise PlannerError("Goal text is required.")
    data = load_data()
    goal = {"id": data["next_goal_id"], "date": goal_date.isoformat(),
            "text": text, "done": False}
    data["goals"].append(goal)
    data["next_goal_id"] += 1
    save_data(data)
    return goal


def complete_goal(goal_id: int) -> dict:
    """Mark a goal done and return it.

    Raises :class:`PlannerError` when the goal is missing or already
    done.
    """
    data = load_data()
    goal = find_goal(data, goal_id)
    if goal is None:
        raise PlannerError(f"No goal with id {goal_id}.")
    if goal["done"]:
        raise PlannerError(f"Goal #{goal['id']} was already done: "
                           f"{goal['text']}")
    goal["done"] = True
    save_data(data)
    return goal


def goals_summary(day: date) -> dict:
    """Return the goals for ``day``: ``{"goals", "done", "total"}``."""
    goals = [g for g in load_data()["goals"] if g["date"] == day.isoformat()]
    return {"goals": goals,
            "done": sum(1 for g in goals if g["done"]),
            "total": len(goals)}


def planner_stats(view_date: date, today: date | None = None) -> dict:
    """Return the dashboard counts: subjects, upcoming exams, sessions
    on ``view_date`` and goals done on ``view_date`` (as ``"done/total"``).
    """
    today = today or date.today()
    data = load_data()
    sessions = schedule(view_date)["sessions"]
    goals = goals_summary(view_date)
    return {
        "subjects": len(data["subjects"]),
        "upcoming_exams": sum(
            1 for e in data["exams"] if parse_date(e["date"]) >= today),
        "sessions_today": len(sessions),
        "goals_done_today": f"{goals['done']}/{goals['total']}",
    }


# ---------------------------------------------------------------------------
# Command-line wrappers (thin: arguments -> service -> printed output)
# ---------------------------------------------------------------------------

def cmd_add_subject(args: argparse.Namespace) -> int:
    """Add a subject from parsed CLI arguments."""
    try:
        subject = add_subject(args.name, args.description)
    except PlannerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Added subject #{subject['id']}: {subject['name']}")
    return 0


def cmd_list_subjects(args: argparse.Namespace) -> int:
    """List subjects from parsed CLI arguments."""
    subjects = list_subjects()
    if not subjects:
        print("No subjects yet. Add one with: add-subject NAME")
        return 0
    print(f"{'ID':<4} {'Subject':<30} Description")
    print("-" * 60)
    for s in subjects:
        print(f"{s['id']:<4} {s['name']:<30} {s['description']}")
    return 0


def cmd_add_exam(args: argparse.Namespace) -> int:
    """Add an exam from parsed CLI arguments."""
    try:
        exam = add_exam(args.subject, args.date, args.title)
    except PlannerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Added exam #{exam['id']}: {exam['title']} "
          f"({exam['subject']}) on {exam['date']}")
    return 0


def cmd_list_exams(args: argparse.Namespace) -> int:
    """List exams from parsed CLI arguments."""
    try:
        exams = list_exams(args.upcoming_only, args.days)
    except PlannerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    today = date.today()
    if not exams:
        print("No upcoming exams." if args.upcoming_only or args.days is not None
              else "No exams yet. Add one with: add-exam SUBJECT DATE")
        return 0
    print(f"{'ID':<4} {'Date':<12} {'Days':<5} Subject — Title")
    print("-" * 70)
    for e in exams:
        days_left = e["days_left"]
        when = f"in {days_left}d" if days_left >= 0 else f"{-days_left}d ago"
        print(f"{e['id']:<4} {e['date']:<12} {when:<5} "
              f"{e['subject']} — {e['title']}")
    return 0


def cmd_add_session(args: argparse.Namespace) -> int:
    """Add a study session from parsed CLI arguments."""
    try:
        session = add_session(args.subject, args.date, args.start,
                              args.end, args.duration, args.topic)
    except PlannerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    minutes = session["duration_minutes"]
    print(f"Added study session #{session['id']}: {session['subject']} "
          f"on {session['date']} {session['start']}–{session['end']} "
          f"({minutes} min)"
          + (f" — {session['topic']}" if session["topic"] else ""))
    return 0


def cmd_schedule(args: argparse.Namespace) -> int:
    """Show the schedule for a date from parsed CLI arguments."""
    day = args.date.isoformat()
    result = schedule(args.date)
    sessions = result["sessions"]
    if not sessions:
        print(f"No study sessions scheduled for {day}.")
        return 0
    print(f"Schedule for {day} ({result['total_minutes']} min total):")
    print(f"{'ID':<4} {'Time':<12} {'Subject':<20} Topic")
    print("-" * 70)
    for s in sessions:
        print(f"{s['id']:<4} {s['start']}–{s['end']:<6} "
              f"{s['subject']:<20} {s['topic']}")
    return 0


def cmd_add_goal(args: argparse.Namespace) -> int:
    """Add a daily goal from parsed CLI arguments."""
    try:
        goal = add_goal(args.date, args.text)
    except PlannerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Added goal #{goal['id']} for {goal['date']}: {goal['text']}")
    return 0


def cmd_complete_goal(args: argparse.Namespace) -> int:
    """Mark a goal as done from parsed CLI arguments."""
    try:
        goal = complete_goal(args.goal_id)
    except PlannerError as exc:
        message = str(exc)
        if "was already done" in message:
            print(message)
            return 0
        print(f"Error: {message}", file=sys.stderr)
        return 1
    print(f"Done ✓ Goal #{goal['id']}: {goal['text']}")
    return 0


def cmd_goals(args: argparse.Namespace) -> int:
    """Show goals for a date from parsed CLI arguments."""
    day = args.date.isoformat()
    result = goals_summary(args.date)
    goals = result["goals"]
    if not goals:
        print(f"No goals for {day}. Add one with: "
              f"add-goal {day} \"Your goal\"")
        return 0
    print(f"Goals for {day} ({result['done']}/{result['total']} done):")
    for g in goals:
        mark = "[x]" if g["done"] else "[ ]"
        print(f"  {mark} #{g['id']} {g['text']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    p = argparse.ArgumentParser(
        prog="planner",
        description="Student Study Planner: subjects, exams, study "
                    "sessions and daily learning goals.")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("add-subject", help="Add a subject")
    sp.add_argument("name", help="Subject name, e.g. Mathematics")
    sp.add_argument("--description", default="", help="Short description")
    sp.set_defaults(func=cmd_add_subject)

    sp = sub.add_parser("list-subjects", help="List all subjects")
    sp.set_defaults(func=cmd_list_subjects)

    sp = sub.add_parser("add-exam", help="Add an exam for a subject")
    sp.add_argument("subject", help="Subject name (must already exist)")
    sp.add_argument("date", type=parse_date, help="Exam date YYYY-MM-DD")
    sp.add_argument("--title", default="", help="Exam title")
    sp.set_defaults(func=cmd_add_exam)

    sp = sub.add_parser("list-exams", help="List exams (upcoming by default)")
    sp.add_argument("--all", dest="upcoming_only", action="store_false",
                    default=True, help="Show past exams too")
    sp.add_argument("--days", type=int, default=None,
                    help="Only exams within the next N days")
    sp.set_defaults(func=cmd_list_exams)

    sp = sub.add_parser("add-session",
                        help="Add a study session / schedule entry")
    sp.add_argument("subject", help="Subject name (must already exist)")
    sp.add_argument("date", type=parse_date, help="Date YYYY-MM-DD")
    sp.add_argument("--start", type=parse_time, default=None,
                    help="Start time HH:MM (24-hour)")
    sp.add_argument("--end", type=parse_time, default=None,
                    help="End time HH:MM (24-hour)")
    sp.add_argument("--duration", type=int, default=None,
                    help="Duration in minutes (alternative to --end; "
                         "defaults start to 09:00 if --start is omitted)")
    sp.add_argument("--topic", default="", help="Topic to study")
    sp.set_defaults(func=cmd_add_session)

    sp = sub.add_parser("schedule", help="Show the schedule for a date")
    sp.add_argument("date", type=parse_date, nargs="?",
                    default=date.today(), help="Date YYYY-MM-DD "
                    "(default: today)")
    sp.set_defaults(func=cmd_schedule)

    sp = sub.add_parser("add-goal", help="Add a daily learning goal")
    sp.add_argument("date", type=parse_date, help="Date YYYY-MM-DD")
    sp.add_argument("text", help="Goal text")
    sp.set_defaults(func=cmd_add_goal)

    sp = sub.add_parser("complete-goal", help="Mark a goal as done")
    sp.add_argument("goal_id", type=int, help="Goal id from the goals list")
    sp.set_defaults(func=cmd_complete_goal)

    sp = sub.add_parser("goals", help="Show goals for a date (default: today)")
    sp.add_argument("date", type=parse_date, nargs="?",
                    default=date.today(), help="Date YYYY-MM-DD")
    sp.set_defaults(func=cmd_goals)

    return p


def main(argv: list[str] | None = None) -> int:
    """Entry point for the command-line app."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
