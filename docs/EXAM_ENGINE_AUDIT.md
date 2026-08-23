# Technical Audit: CIT-CognIQ Exam Engine & Student Lifecycle

This document presents a comprehensive, read-only architectural audit of the existing **CIT-CognIQ** exam engine, tracing the full student exam-taking lifecycle across models, views, templates, and JavaScript logic.

---

## 1. Component Audit Matrix

### Model Layer ([`myapp/models.py`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/models.py))

#### Component: `Exam`
- **FILE**: [`myapp/models.py`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/models.py) (Lines 436–593)
- **CLASS/FUNCTION**: `Exam(models.Model)`
- **WHAT IT DOES**: Stores overall assessment metadata, duration, subject, passing criteria, ownership, and class assignments.
- **WHAT DATA IT READS**: `School` (FK), `User` (created_by FK), `StudentClass` (M2M), `Question` (M2M via `ExamQuestion`).
- **WHAT DATA IT WRITES**: Stores rows in table `myapp_exam` and M2M table `myapp_exam_assigned_classes`.
- **WHAT OTHER COMPONENTS IT DEPENDS ON**: `School`, `User`, `StudentClass`, `Question`, `ExamQuestion`.

#### Component: `ExamQuestion`
- **FILE**: [`myapp/models.py`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/models.py) (Lines 659–673)
- **CLASS/FUNCTION**: `ExamQuestion(models.Model)`
- **WHAT IT DOES**: Acts as the explicit junction table between `Exam` and `Question`, maintaining question sequence via the `order` field.
- **WHAT DATA IT READS**: `Exam` (FK), `Question` (FK), `order` (PositiveIntegerField).
- **WHAT DATA IT WRITES**: Stores rows in `myapp_examquestion`.
- **WHAT OTHER COMPONENTS IT DEPENDS ON**: `Exam`, `Question`.

#### Component: `ExamAttempt`
- **FILE**: [`myapp/models.py`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/models.py) (Lines 715–850)
- **CLASS/FUNCTION**: `ExamAttempt(models.Model)`
- **WHAT IT DOES**: Tracks a student's exam session, start/submit timestamps, score, completion flag, randomized question order JSON, and proctoring violation reason.
- **WHAT DATA IT READS**: `User` (student FK), `Exam` (FK), `StudentClass` (FK), `started_at`, `submitted_at`, `question_order` (JSON), `has_violation`, `violation_reason`.
- **WHAT DATA IT WRITES**: Stores session state in `myapp_examattempt`. Updated during initialization (`exam_take`) and completion (`exam_submit`).
- **WHAT OTHER COMPONENTS IT DEPENDS ON**: `User`, `Exam`, `StudentClass`, `StudentAnswer`.

#### Component: `StudentAnswer`
- **FILE**: [`myapp/models.py`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/models.py) (Lines 851–898)
- **CLASS/FUNCTION**: `StudentAnswer(models.Model)`
- **WHAT IT DOES**: Records individual question choices selected by a student for a specific attempt.
- **WHAT DATA IT READS**: `ExamAttempt` (FK), `Question` (FK), `Choice` (selected_choice FK), `is_correct`.
- **WHAT DATA IT WRITES**: Stores rows in `myapp_studentanswer`. Evaluates `self.is_correct = self.selected_choice.is_correct` in `save()`.
- **WHAT OTHER COMPONENTS IT DEPENDS ON**: `ExamAttempt`, `Question`, `Choice`.

#### Component: `ExamAttempt.calculate_score()`
- **FILE**: [`myapp/models.py`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/models.py) (Lines 840–849)
- **CLASS/FUNCTION**: `ExamAttempt.calculate_score(self)`
- **WHAT IT DOES**: Iterates through all `StudentAnswer` rows for an attempt. If `answer.is_correct` is `True`, adds `question.marks` to total score.
- **WHAT DATA IT READS**: `self.answers.all()`, `answer.is_correct`, `answer.question.marks`.
- **WHAT DATA IT WRITES**: Updates `self.score` and saves `ExamAttempt`.
- **WHAT OTHER COMPONENTS IT DEPENDS ON**: `StudentAnswer`, `Question`.

---

### View Layer ([`myapp/views.py`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/views.py))

#### Component: `student_exam_list`
- **FILE**: [`myapp/views.py`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/views.py) (Lines 1109–1290)
- **CLASS/FUNCTION**: `def student_exam_list(request)`
- **WHAT IT DOES**: Queries and displays available exams assigned to the student's enrolled classes, annotates attempt counts and best scores.
- **WHAT DATA IT READS**: `request.user.student_classes`, `Exam` (filtered by assigned classes), `ExamAttempt`, `ExamAssignmentDate`.
- **WHAT DATA IT WRITES**: None (read-only view).
- **WHAT OTHER COMPONENTS IT DEPENDS ON**: `Exam`, `StudentClass`, `ExamAttempt`, `ExamAssignmentDate`, [`templates/exams/student_exam_list.html`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/templates/exams/student_exam_list.html).

#### Component: `exam_take`
- **FILE**: [`myapp/views.py`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/views.py) (Lines 1294–1430)
- **CLASS/FUNCTION**: `def exam_take(request, exam_pk)`
- **WHAT IT DOES**: Initializes a student exam session. Enforces single-attempt limits for `test` mode, creates `ExamAttempt`, randomizes question and choice order, and renders the single-page exam interface.
- **WHAT DATA IT READS**: `Exam`, `StudentClass`, `Question`, `Choice`, `ExamAttempt`.
- **WHAT DATA IT WRITES**: Creates `ExamAttempt` record; writes randomized question ID array to `attempt.question_order`.
- **WHAT OTHER COMPONENTS IT DEPENDS ON**: `Exam`, `ExamAttempt`, `Question`, `Choice`, [`templates/exams/exam_take.html`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/templates/exams/exam_take.html).

#### Component: `exam_submit`
- **FILE**: [`myapp/views.py`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/views.py) (Lines 1433–1519)
- **CLASS/FUNCTION**: `def exam_submit(request, attempt_pk)`
- **WHAT IT DOES**: Receives POST form data, validates attempt time window, creates `StudentAnswer` records for selected choices, records proctoring violations if submitted via violation hook, calls `calculate_score()`, marks attempt completed, and redirects to results.
- **WHAT DATA IT READS**: `request.POST` (radio input choices `question_{id}`), `ExamAttempt`, `Choice`.
- **WHAT DATA IT WRITES**: Creates `StudentAnswer` records; updates `attempt.submitted_at`, `attempt.is_completed`, `attempt.has_violation`, `attempt.score`.
- **WHAT OTHER COMPONENTS IT DEPENDS ON**: `ExamAttempt`, `StudentAnswer`, `Choice`, `calculate_score()`, `exam_results`.

#### Component: `exam_results`
- **FILE**: [`myapp/views.py`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/views.py) (Lines 1522–1573)
- **CLASS/FUNCTION**: `def exam_results(request, attempt_pk)`
- **WHAT IT DOES**: Displays detailed performance summary for a completed attempt. Reconstructs questions using saved `question_order` JSON and shows selected answers alongside correct choices and explanations.
- **WHAT DATA IT READS**: `ExamAttempt`, `attempt.question_order`, `StudentAnswer`, `Choice`, `Question`.
- **WHAT DATA IT WRITES**: None (read-only view).
- **WHAT OTHER COMPONENTS IT DEPENDS ON**: `ExamAttempt`, `StudentAnswer`, `Question`, [`templates/exams/exam_results.html`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/templates/exams/exam_results.html).

---

## 2. Complete 15-Step Student Exam Lifecycle Trace

```
 1. Authentication ──► 2. Student Dashboard ──► 3. Exam List Discovery
                                                       │
 6. Question Fetch ◄── 5. ExamAttempt Row ◄── 4. Exam Initialization (`exam_take`)
         │
         ▼
 7. Randomization ──► 8. Answer Handling ──► 9. Client Timer ──► 10. Proctoring Check
    (Python Shuffle)   (DOM-Only Radio)     (JS Countdown)      (Blur / Visibility)
                                                                      │
15. Results Display ◄── 14. Score Calculation ◄── 13. Form Submit ◄── 11 & 12. Single-Page Scroll
    (Explanations)     (Sum Correct Marks)   (POST Request)       (No Pagination)
```

1. **Student Authentication**:
   - URL: `/accounts/login/` (`LoginView`)
   - Validates student credentials against `myapp.User`. Authenticated session retains `user.role == 'student'`.
2. **Student Dashboard**:
   - URL: `/dashboard/student/` (`views.student_dashboard`)
   - Displays student metrics (exams available, completed attempts, overall average score).
3. **Available Exams Retrieval**:
   - URL: `/student/exams/` (`views.student_exam_list`)
   - Queries `Exam.objects.filter(assigned_classes__in=user.student_classes.all())`. Annotates class assignment dates from `ExamAssignmentDate`.
4. **Starting an Exam**:
   - URL: `/student/exams/<exam_pk>/take/` (`views.exam_take`)
   - Student clicks "Take Exam". View checks if student is enrolled in a class assigned to the exam.
5. **`ExamAttempt` Creation**:
   - `ExamAttempt.objects.create(student=user, exam=exam, student_class=student_class, attempt_mode=mode)` creates a database row synchronously on page load.
6. **Question Retrieval**:
   - `questions = list(exam.questions.prefetch_related('choices').order_by('examquestion__order'))`.
7. **Question Ordering & Randomization**:
   - View executes `random.shuffle(questions)`.
   - Stores `attempt.question_order = [q.id for q in questions]`.
   - Shuffles choices per question into `question.shuffled_choices`.
8. **Answer Handling**:
   - Questions rendered as HTML radio buttons (`<input type="radio" name="question_{{ q.id }}" value="{{ choice.id }}">`).
   - Selecting a choice triggers JS `updateProgress()` which updates the DOM counter (`X/Y Answered`).
   - **No network/AJAX request occurs**. Answers exist solely in browser RAM.
9. **Timer Operation**:
   - JavaScript calculates `endTime = startTime + durationMinutes * 60000`.
   - `setInterval(updateTimer, 1000)` counts down locally in the browser header.
10. **Tab/Focus-Loss Detection**:
    - JS listens to `visibilitychange` and `blur` events.
    - 1st focus loss: Displays warning alert.
    - 2nd focus loss: Sets `has_violation=true` and invokes `document.getElementById('examForm').submit()`.
11. **Page Rendering**:
    - Rendered via [`templates/exams/exam_take.html`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/templates/exams/exam_take.html).
    - Renders **all questions in a single long scrollable vertical list**.
12. **Navigation**:
    - No pagination or section tabs exist. Navigation relies on native browser page scrolling or floating "Jump to Submit" button.
13. **Exam Submission**:
    - URL: `/student/attempts/<attempt_pk>/submit/` (`views.exam_submit`).
    - Standard HTML form `POST`. Server reads `request.POST.get(f'question_{question.id}')`.
    - Creates `StudentAnswer` records for submitted choice IDs.
14. **Score Calculation**:
    - Calls `attempt.calculate_score()`.
    - Iterates over `StudentAnswer` entries: if `selected_choice.is_correct == True`, adds `question.marks` to `attempt.score`.
15. **Results Display**:
    - URL: `/student/attempts/<attempt_pk>/results/` (`views.exam_results`).
    - Renders [`templates/exams/exam_results.html`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/templates/exams/exam_results.html).
    - Displays overall score, percentage, pass/fail status, correct answers, and explanations.

---

## 3. Database Relationships Map

```
School (1) ────◄ User (N)
  │               ▲
  │ (1)           │ (N)
  ▼               │
StudentClass (N) ─┘ (M:N students)
  ▲
  │ (M:N assigned_classes)
  │
Exam (1) ─────────◄ ExamQuestion (N) ─────────► Question (1) ─────────◄ Choice (N)
  │                      │                         ▲                      ▲
  │ (1)                  │ (Order tracking)        │ (1)                  │ (1)
  ▼                      ▼                         │                      │
ExamAttempt (N) ───────────────────────────────────┼──────────────────────┘
  │                                                │
  └───────────────► StudentAnswer (N) ─────────────┘
```

---

## 4. Current Limitations vs. Aptitude Platform Requirements

| Feature | Current CognIQ Engine | Professional Aptitude Platform Standard | Gap Analysis |
|---|---|---|---|
| **Question Navigation** | Single long vertical scroll page for all questions. | Single-question pagination with Section tabs (Quant, Logical, Verbal). | High DOM overhead; risk of accidental submission while scrolling. |
| **Question Palette** | **Not implemented**. Basic text counter `0/N Answered`. | Interactive 1..N grid with 5 color-coded states (*Answered, Unanswered, Marked for Review, Ans & Marked, Unvisited*). | No visual progress tracking or quick jump capability. |
| **Mark for Review** | **Not implemented**. | Explicit "Mark for Review & Next" button to revisit flagged questions. | Students cannot flag uncertain questions. |
| **Clear Response** | **Not implemented**. Cannot uncheck a selected radio option. | Dedicated "Clear Response" button per question. | Student cannot deselect an answer once clicked. |
| **Answer Persistence** | **DOM-Only**. Answers sent only on final POST submit. | **Real-Time Auto-Save** via background AJAX per question selection. | Browser crash, refresh, or network drop causes **100% data loss**. |
| **Network Recovery** | **Not implemented**. Form submission fails if offline. | Background retry queue & offline state caching. | Vulnerable to momentary connection drops. |
| **Timer Implementation** | Client-authoritative JS countdown based on local clock. | **Server-Authoritative Timer** with periodic sync/heartbeat. | Vulnerable to local computer clock tampering or manipulation. |
| **Attempt Lifecycle** | Attempt created on GET request; binary `is_completed` boolean. | State machine (`NOT_STARTED` → `IN_PROGRESS` → `SUBMITTED` / `TIMED_OUT` / `TERMINATED`). | Abandoned GET requests leave dirty incomplete attempt rows. |
| **Scoring & Penalties** | Simple positive mark summation (`calculate_score()`). | Negative marking penalties (e.g. -0.25) & section accuracy breakdown. | No support for competitive exam penalty scoring. |

---

## 5. Recommended Implementation Order for New Exam Engine

To transform this system cleanly into the target Aptitude Examination Engine without breaking existing data:

1. **Phase 1: Model Schema Enhancements**
   - Add `status` field (`in_progress`, `submitted`, `timed_out`, `terminated`) to `ExamAttempt`.
   - Add `review_status` (`unvisited`, `unanswered`, `answered`, `marked`, `answered_marked`) to `StudentAnswer` (make `selected_choice` nullable for unvisited/unanswered states).
   - Add `negative_marks` field to `Question` and `enable_negative_marking` to `Exam`.

2. **Phase 2: Real-Time Auto-Save & Server-Synced Timer API**
   - Create AJAX endpoint `POST /student/attempts/<id>/save-answer/` for atomic real-time choice persistence.
   - Create AJAX endpoint `GET /student/attempts/<id>/time-remaining/` for server-authoritative timer validation.

3. **Phase 3: Split-Screen Aptitude UI & Question Palette**
   - Rebuild `exam_take.html` into a two-column interface (Left: Question Paper + Options + Action bar; Right: Timer + Interactive Question Palette Grid).
   - Implement "Save & Next", "Mark for Review & Next", and "Clear Response" actions.

4. **Phase 4: Sectional Scoring & Percentile Engine**
   - Update `calculate_score()` to deduct negative marks for incorrect choices.
   - Add section-wise accuracy breakdown and batch percentile calculation to `exam_results`.
