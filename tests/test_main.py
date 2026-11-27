"""Unit tests for the Student Study Planner service layer (main.py).

Run from the project folder with:

    pip install -r requirements-dev.txt
    pytest

Tests use a temporary data file (``main.DATA_FILE`` is pointed at
``tmp_path``), so they never touch the real ``data.json``.
"""

from __future__ import annotations

from datetime import date, time
from pathlib import Path

import pytest

import main as planner


@pytest.fixture(autouse=True)
def isolated_data_file(tmp_path, monkeypatch):
    """Point the service at a fresh temporary data file per test."""
    monkeypatch.setattr(planner, "DATA_FILE", tmp_path / "data.json")


def _subject(name: str = "Mathematics") -> dict:
    return planner.add_subject(name, "Algebra and calculus")


def test_add_subject_defaults():
    """A new subject gets an id, its name and description."""
    subject = _subject()
    assert subject["id"] == 1
    assert subject["name"] == "Mathematics"
    assert subject["description"] == "Algebra and calculus"


def test_add_subject_rejects_blank_name():
    """A blank subject name is refused."""
    with pytest.raises(planner.PlannerError, match="Subject name is required"):
        planner.add_subject("   ")


def test_add_subject_rejects_duplicate_case_insensitive():
    """A subject name that already exists (any case) is refused."""
    _subject()
    with pytest.raises(planner.PlannerError, match="already exists"):
        planner.add_subject("mathematics")


def test_list_subjects_empty_and_filled():
    """Listing works on an empty store and after adds."""
    assert planner.list_subjects() == []
    _subject()
    planner.add_subject("Physics")
    assert [s["name"] for s in planner.list_subjects()] == [
        "Mathematics", "Physics"]


def test_add_exam_defaults_title():
    """An exam without a title is named after its subject."""
    _subject()
    exam = planner.add_exam("Mathematics", date(2026, 12, 15))
    assert exam["id"] == 1
    assert exam["title"] == "Mathematics exam"
    assert exam["date"] == "2026-12-15"


def test_add_exam_rejects_unknown_subject():
    """An exam for a subject that does not exist is refused."""
    with pytest.raises(planner.PlannerError, match="No subject named"):
        planner.add_exam("Chemistry", date(2026, 12, 15))


def test_list_exams_upcoming_only_by_default():
    """By default only exams on or after today are listed, by date."""
    _subject()
    planner.add_exam("Mathematics", date(2026, 11, 1), "Past")
    planner.add_exam("Mathematics", date(2026, 12, 15), "Midterm")
    planner.add_exam("Mathematics", date(2026, 11, 28), "Quiz")
    today = date(2026, 11, 27)
    exams = planner.list_exams(today=today)
    assert [e["title"] for e in exams] == ["Quiz", "Midterm"]
    assert exams[0]["days_left"] == 1
    assert exams[0]["badge_label"] == "in 1d"
    assert exams[0]["badge_class"] == "amber"


def test_list_exams_all_and_days_filter():
    """--all shows past exams; --days limits to the next N days."""
    _subject()
    planner.add_exam("Mathematics", date(2026, 11, 1), "Past")
    planner.add_exam("Mathematics", date(2026, 11, 28), "Soon")
    planner.add_exam("Mathematics", date(2027, 1, 15), "Later")
    today = date(2026, 11, 27)
    assert len(planner.list_exams(upcoming_only=False, today=today)) == 3
    assert [e["title"] for e in planner.list_exams(days=7, today=today)] == [
        "Soon"]
    assert planner.list_exams(days=0, today=today) == []


def test_list_exams_rejects_negative_days():
    """A negative days window is an error."""
    with pytest.raises(planner.PlannerError, match="non-negative"):
        planner.list_exams(days=-1)


def test_exam_badge_labels():
    """Badge labels cover past, today, soon and later exams."""
    assert planner.exam_badge(-2) == ("2d ago", "red")
    assert planner.exam_badge(0) == ("Today", "red")
    assert planner.exam_badge(7) == ("in 7d", "amber")
    assert planner.exam_badge(30) == ("in 30d", "indigo")


def test_add_session_start_end():
    """A session from start+end stores the times and the duration."""
    _subject()
    session = planner.add_session("Mathematics", date(2026, 11, 28),
                                  start=time(9, 0), end=time(10, 30),
                                  topic="Integration")
    assert session["id"] == 1
    assert session["start"] == "09:00"
    assert session["end"] == "10:30"
    assert session["duration_minutes"] == 90
    assert session["topic"] == "Integration"


def test_add_session_duration_defaults_start():
    """A duration-only session starts at 09:00 and ends after it."""
    _subject()
    session = planner.add_session("Mathematics", date(2026, 11, 28),
                                  duration=45, topic="Derivatives")
    assert session["start"] == "09:00"
    assert session["end"] == "09:45"
    assert session["duration_minutes"] == 45


def test_add_session_duration_with_given_start():
    """A duration with an explicit start ends duration minutes later."""
    _subject()
    session = planner.add_session("Mathematics", date(2026, 11, 28),
                                  start=time(14, 0), duration=30)
    assert session["start"] == "14:00"
    assert session["end"] == "14:30"


def test_add_session_rejects_unknown_subject():
    """A session for a missing subject is refused."""
    with pytest.raises(planner.PlannerError, match="No subject named"):
        planner.add_session("Chemistry", date(2026, 11, 28),
                            start=time(9, 0), end=time(10, 0))


def test_add_session_rejects_end_not_after_start():
    """An end time at or before the start is refused."""
    _subject()
    with pytest.raises(planner.PlannerError,
                       match="End time must be after start time"):
        planner.add_session("Mathematics", date(2026, 11, 28),
                            start=time(10, 0), end=time(10, 0))
    with pytest.raises(planner.PlannerError,
                       match="End time must be after start time"):
        planner.add_session("Mathematics", date(2026, 11, 28),
                            start=time(11, 0), end=time(10, 0))


def test_add_session_rejects_bad_duration():
    """A non-positive duration is refused."""
    _subject()
    with pytest.raises(planner.PlannerError,
                       match="duration must be a positive number"):
        planner.add_session("Mathematics", date(2026, 11, 28), duration=-30)


def test_add_session_rejects_no_time_given():
    """A session with no times at all is refused."""
    _subject()
    with pytest.raises(planner.PlannerError, match="give --start and --end"):
        planner.add_session("Mathematics", date(2026, 11, 28))


def test_schedule_returns_day_sorted_with_total():
    """A day's schedule is sorted by start time with a minute total."""
    _subject()
    planner.add_session("Mathematics", date(2026, 11, 28),
                        start=time(14, 0), end=time(15, 0))
    planner.add_session("Mathematics", date(2026, 11, 28),
                        start=time(9, 0), end=time(9, 45))
    planner.add_session("Mathematics", date(2026, 11, 29),
                        start=time(9, 0), end=time(10, 0))
    result = planner.schedule(date(2026, 11, 28))
    assert [s["start"] for s in result["sessions"]] == ["09:00", "14:00"]
    assert result["total_minutes"] == 105
    assert planner.schedule(date(2026, 11, 30)) == {
        "sessions": [], "total_minutes": 0}


def test_add_goal_and_complete_goal():
    """Goals are added undone and completing marks them done."""
    goal = planner.add_goal(date(2026, 11, 28),
                            "Finish 20 integration problems")
    assert goal["id"] == 1
    assert goal["done"] is False
    done = planner.complete_goal(1)
    assert done["done"] is True


def test_add_goal_rejects_blank_text():
    """A blank goal is refused."""
    with pytest.raises(planner.PlannerError, match="Goal text is required"):
        planner.add_goal(date(2026, 11, 28), "  ")


def test_complete_goal_missing_or_already_done_raises():
    """Completing a missing or already-done goal is an error."""
    with pytest.raises(planner.PlannerError, match="No goal with id 9"):
        planner.complete_goal(9)
    planner.add_goal(date(2026, 11, 28), "Study")
    planner.complete_goal(1)
    with pytest.raises(planner.PlannerError, match="was already done"):
        planner.complete_goal(1)


def test_goals_summary_counts_done():
    """A day's goals come with a done/total count."""
    planner.add_goal(date(2026, 11, 28), "One")
    planner.add_goal(date(2026, 11, 28), "Two")
    planner.add_goal(date(2026, 11, 29), "Other day")
    planner.complete_goal(1)
    result = planner.goals_summary(date(2026, 11, 28))
    assert result["done"] == 1
    assert result["total"] == 2
    assert [g["id"] for g in result["goals"]] == [1, 2]


def test_planner_stats_counts():
    """Dashboard stats count subjects, upcoming exams, sessions and goals."""
    _subject()
    planner.add_exam("Mathematics", date(2026, 12, 15))
    planner.add_exam("Mathematics", date(2026, 11, 1))
    planner.add_session("Mathematics", date(2026, 11, 28),
                        start=time(9, 0), end=time(10, 0))
    planner.add_goal(date(2026, 11, 28), "One")
    planner.add_goal(date(2026, 11, 28), "Two")
    planner.complete_goal(1)
    stats = planner.planner_stats(date(2026, 11, 28),
                                  today=date(2026, 11, 27))
    assert stats == {"subjects": 1, "upcoming_exams": 1,
                     "sessions_today": 1, "goals_done_today": "1/2"}


def test_parse_date_and_time_valid_and_invalid():
    """Valid dates/times parse; anything else raises PlannerError."""
    assert planner.parse_date("2026-11-27") == date(2026, 11, 27)
    assert planner.parse_time("09:30") == time(9, 30)
    with pytest.raises(planner.PlannerError, match="use YYYY-MM-DD"):
        planner.parse_date("27/11/2026")
    with pytest.raises(planner.PlannerError, match="use HH:MM"):
        planner.parse_time("9:30am")


def test_load_data_survives_corrupted_file(tmp_path, monkeypatch):
    """A corrupted data.json starts empty instead of crashing."""
    bad_file = tmp_path / "data.json"
    bad_file.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(planner, "DATA_FILE", bad_file)
    assert planner.load_data() == planner.empty_data()


def test_load_data_backfills_missing_keys(tmp_path, monkeypatch):
    """An older file missing keys still loads with defaults."""
    old_file = tmp_path / "data.json"
    old_file.write_text('{"subjects": [{"id": 1, "name": "Math", '
                        '"description": ""}]}', encoding="utf-8")
    monkeypatch.setattr(planner, "DATA_FILE", old_file)
    data = planner.load_data()
    assert data["subjects"][0]["name"] == "Math"
    assert data["exams"] == []
    assert data["next_subject_id"] == 1


def test_save_and_load_round_trip():
    """Saved subjects load back exactly."""
    _subject()
    stored = planner.load_data()
    assert stored["subjects"][0]["name"] == "Mathematics"
    assert stored["next_subject_id"] == 2


def test_data_file_is_a_path(tmp_path, monkeypatch):
    """The service works when DATA_FILE is a pathlib Path (as shipped)."""
    monkeypatch.setattr(planner, "DATA_FILE", tmp_path / "data.json")
    assert isinstance(planner.DATA_FILE, Path)
    _subject()
    assert planner.list_subjects()[0]["name"] == "Mathematics"
