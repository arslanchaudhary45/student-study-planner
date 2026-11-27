#!/usr/bin/env python3
"""Student Study Planner — web UI (Flask).

Thin routes only: each handler parses and validates its HTTP input,
calls one service function from :mod:`main`, then renders a page or
redirects. All rules (validation, ids, days-left, badges) live in
``main.py``; nothing about subjects, exams, sessions or goals is
decided here.

Run it with:

    pip install -r requirements.txt
    python app.py

Then open http://127.0.0.1:5000 in your browser.
Set the PORT environment variable to use a different port.
The command-line app still works exactly as before: python3 main.py --help
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, time

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import main as planner

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-key")

APP_NAME = "Student Study Planner"
APP_TAGLINE = "Subjects, exams, study sessions and daily learning goals"


def parse_date_field(value: str | None,
                     default: date | None = None) -> date | None:
    """Parse a ``YYYY-MM-DD`` form value; ``default`` when blank.

    Raises :class:`planner.PlannerError` on a malformed date.
    """
    value = (value or "").strip()
    if not value:
        return default
    return planner.parse_date(value)


def parse_time_field(value: str | None) -> time | None:
    """Parse a ``HH:MM`` form value; ``None`` when blank.

    Raises :class:`planner.PlannerError` on a malformed time.
    """
    value = (value or "").strip()
    if not value:
        return None
    return planner.parse_time(value)


@app.context_processor
def inject_globals() -> dict:
    """Make the app name and tagline available to every template."""
    return {"app_name": APP_NAME, "app_tagline": APP_TAGLINE}


@app.route("/")
def index() -> str:
    """Dashboard: stat cards, today's schedule and goals, subjects,
    exams with days-left badges, and the add forms."""
    today = date.today()
    try:
        view_date = parse_date_field(request.args.get("date"), default=today)
    except planner.PlannerError as exc:
        flash(str(exc), "error")
        view_date = today
    exam_filter = request.args.get("exams", "upcoming")
    try:
        days = int(request.args.get("days", "")) if request.args.get("days") else None
    except ValueError:
        days = None
    try:
        exams = planner.list_exams(exam_filter != "all", days, today)
    except planner.PlannerError as exc:
        flash(str(exc), "error")
        exams = []
    day_schedule = planner.schedule(view_date)
    day_goals = planner.goals_summary(view_date)
    stats = planner.planner_stats(view_date, today)
    return render_template(
        "index.html", subjects=planner.list_subjects(), exams=exams,
        exam_filter=exam_filter, days=days,
        sessions=day_schedule["sessions"],
        total_minutes=day_schedule["total_minutes"],
        goals=day_goals["goals"],
        view_date=view_date, today=today, stats=stats)


@app.route("/add-subject", methods=["POST"])
def add_subject() -> str:
    """Add a subject from the dashboard form, then go back to the list."""
    try:
        subject = planner.add_subject(
            request.form.get("name", ""),
            request.form.get("description", ""))
    except planner.PlannerError as exc:
        flash(str(exc), "error")
        return redirect(url_for("index"))
    flash(f"Added subject #{subject['id']}: {subject['name']}.", "success")
    return redirect(url_for("index"))


@app.route("/add-exam", methods=["POST"])
def add_exam() -> str:
    """Add an exam from the dashboard form, then go back to the list."""
    try:
        exam_date = parse_date_field(request.form.get("date"))
        if exam_date is None:
            raise planner.PlannerError("Exam date is required.")
        exam = planner.add_exam(request.form.get("subject", ""),
                                exam_date, request.form.get("title", ""))
    except planner.PlannerError as exc:
        flash(str(exc), "error")
        return redirect(url_for("index"))
    flash(f"Added exam #{exam['id']}: {exam['title']} "
          f"({exam['subject']}) on {exam['date']}.", "success")
    return redirect(url_for("index"))


@app.route("/add-session", methods=["POST"])
def add_session() -> str:
    """Add a study session from the dashboard form, then go back."""
    try:
        session_date = parse_date_field(request.form.get("date"))
        start = parse_time_field(request.form.get("start"))
        end = parse_time_field(request.form.get("end"))
    except planner.PlannerError as exc:
        flash(str(exc), "error")
        return redirect(url_for("index"))
    duration_raw = request.form.get("duration", "").strip()
    try:
        duration = int(duration_raw) if duration_raw else None
    except ValueError:
        flash("Duration must be a number of minutes.", "error")
        return redirect(url_for("index"))
    if session_date is None:
        flash("Session date is required.", "error")
        return redirect(url_for("index"))
    try:
        session = planner.add_session(
            request.form.get("subject", ""), session_date,
            start, end, duration, request.form.get("topic", ""))
    except planner.PlannerError as exc:
        flash(str(exc), "error")
        return redirect(url_for("index"))
    flash(f"Added study session #{session['id']}: {session['subject']} "
          f"on {session['date']} {session['start']}–{session['end']} "
          f"({session['duration_minutes']} min).", "success")
    return redirect(url_for("index"))


@app.route("/add-goal", methods=["POST"])
def add_goal() -> str:
    """Add a daily goal from the dashboard form, then go back."""
    try:
        goal_date = parse_date_field(request.form.get("date"))
        if goal_date is None:
            raise planner.PlannerError("Goal date is required.")
        goal = planner.add_goal(goal_date, request.form.get("text", ""))
    except planner.PlannerError as exc:
        flash(str(exc), "error")
        return redirect(url_for("index"))
    flash(f"Added goal #{goal['id']} for {goal['date']}.", "success")
    return redirect(url_for("index", date=goal["date"]))


@app.route("/complete-goal/<int:goal_id>", methods=["POST"])
def complete_goal(goal_id: int) -> str:
    """Mark a goal done, then go back to the same date view."""
    try:
        goal = planner.complete_goal(goal_id)
    except planner.PlannerError as exc:
        flash(str(exc), "error")
        return redirect(url_for("index", date=request.form.get("date", "")))
    flash(f"Done ✓ Goal #{goal['id']}: {goal['text']}.", "success")
    return redirect(url_for("index", date=request.form.get("date", "")))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port)
