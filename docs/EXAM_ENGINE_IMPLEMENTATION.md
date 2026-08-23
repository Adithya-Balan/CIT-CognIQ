# Implementation Report: Core Aptitude Exam Engine Rebuild (Phase 1)

This document details the architectural implementation of the core NPTEL/Gate-style single-question aptitude testing engine for **CIT-CognIQ**.

---

## 1. Files Changed & Added

- **[`myapp/models.py`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/models.py)**: Added `status` field to `ExamAttempt` (`in_progress`, `submitted`, `timed_out`, `terminated`). Added `state` and `is_marked_for_review` fields to `StudentAnswer`, and updated `selected_choice` to be nullable for cleared/visited responses.
- **[`myapp/views.py`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/views.py)**:
  - Updated `exam_take` for attempt resumption, single-question pagination context, and initial state dictionary construction.
  - Added AJAX endpoint `api_save_answer` for real-time answer persistence, state computation, and review toggles.
  - Updated `exam_submit` for state transitions, time verification, and JSON response support.
- **[`myapp/urls.py`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/urls.py)**: Registered `api_save_answer` route (`POST /student/attempts/<int:attempt_pk>/save-answer/`).
- **[`myapp/templatetags/timezone_filters.py`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/templatetags/timezone_filters.py)**: Added `get_item` filter for dictionary lookups in Django templates.
- **[`templates/exams/exam_take.html`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/templates/exams/exam_take.html)**: Rebuilt single-question aptitude testing interface with interactive Question Palette grid, real-time autosave status, clear response, mark for review, server timer, and pre-submission summary modal.
- **[`myapp/migrations/0036_examattempt_status_and_more.py`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/migrations/0036_examattempt_status_and_more.py)**: Migration for model updates.
- **[`myapp/tests.py`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/tests.py)**: Automated unit test suite verifying attempt lifecycle, autosave, resumption, palette states, and score calculation.

---

## 2. Model & Database Schema Changes

### `ExamAttempt`
- Added field `status`: `CharField` with choices (`in_progress`, `submitted`, `timed_out`, `terminated`), defaulting to `'in_progress'`.

### `StudentAnswer`
- Altered field `selected_choice`: `ForeignKey(Choice, null=True, blank=True)` to support visited/unanswered or cleared choices.
- Added field `state`: `CharField` with choices (`not_visited`, `visited_unanswered`, `answered`, `marked_for_review`, `answered_marked_for_review`), defaulting to `'visited_unanswered'`.
- Added field `is_marked_for_review`: `BooleanField(default=False)`.

---

## 3. New Endpoints Added

| Endpoint URL | View Function | Method | Description |
|---|---|---|---|
| `/student/attempts/<int:attempt_pk>/save-answer/` | `api_save_answer` | `POST` | Real-time AJAX endpoint that validates attempt ownership/timing and saves choice selection, clear response, or mark-for-review state. |

---

## 4. Exam Engine Architecture & Behaviors

### A. Attempt Resumption
- Upon hitting `/student/exams/<exam_id>/take/`, `exam_take` queries for an active `ExamAttempt` where `student=request.user`, `is_completed=False`, and `status='in_progress'`.
- If an active attempt exists and hasn't expired, it **resumes that attempt**, retrieving the stored `question_order` JSON and all existing `StudentAnswer` states.

### B. Real-Time Auto-Save
- Selecting an option, clearing a response, or toggling mark for review triggers `sendAutosave(...)` via `fetch()`.
- Top header displays save status (`Saving...` → `All changes saved` or `Connection issue`).
- Backend validates attempt ownership, active status, and server deadline before committing transaction.

### C. Question Palette Grid
- Renders an interactive `01..N` grid.
- Reflects 5 color-coded states:
  - ⬜ `NOT_VISITED`
  - 🟥 `VISITED_UNANSWERED`
  - 🟩 `ANSWERED`
  - 🟪 `MARKED_FOR_REVIEW`
  - 🟪🟩 `ANSWERED_AND_MARKED`
- Clicking any number jumps directly to that question.

### D. Server-Authoritative Timer
- Server calculates `remaining_seconds = max(0, int((started_at + duration - now).total_seconds()))`.
- Client countdown initializes using server seconds.
- On expiry (`remainingSeconds <= 0`), frontend triggers auto-submit while backend independently rejects late answers and marks attempt `timed_out`.

---

## 5. Automated Testing Performed

All 6 integration tests in `myapp/tests.py` passed:
- `test_01_student_login_and_exam_start`: Student login & attempt creation.
- `test_02_attempt_resumption_on_refresh`: Refreshing browser reuses existing active attempt.
- `test_03_realtime_autosave_and_state_persistence`: Real-time choice saving and DB persistence.
- `test_04_mark_for_review_and_clear_response`: Review flags and clear response logic.
- `test_05_server_authoritative_timer_and_timeout`: Server timeout validation.
- `test_06_final_submission_and_score_calculation`: Score calculation & final submission.

---

## 6. Known Limitations (Phase 1 Scope)

- Advanced analytics, percentile ranks, section-wise breakdown, and negative marking will be implemented in subsequent phases.
