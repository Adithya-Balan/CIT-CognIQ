# CIT-CognIQ Codebase Architecture & Execution Flow Walkthrough

This document provides a comprehensive, read-only architectural analysis and execution flow trace of the existing **CIT-CognIQ** Django application before any migration or refactoring.

---

## 1. Project Structure & App Architecture

### Directory Overview
- **[`CognIQ/`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/CognIQ)**: Django project root configuration directory (`settings.py`, `urls.py`, `wsgi.py`, `asgi.py`).
- **[`myapp/`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp)**: Main application containing models, views, forms, and custom tags.
  - `models.py`: All 10 core domain models.
  - `views.py`: Primary HTTP views (~4,500 lines).
  - `exam_bank_views.py`: Shared exam bank cloning and assignment logic.
  - `urls.py`: App routing endpoints.
  - `forms.py`: Django ModelForms for users, exams, questions, and bulk uploads.
  - `migrations/`: 35 schema migration scripts.
- **[`templates/`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/templates)**: Global server-side HTML templates organized by domain (`account/`, `dashboard/`, `exams/`, `classes/`, `school_admin/`, `analytics/`).
- **[`static/`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/static)**: Static assets (`assets/` for logos, `styles/` for compiled Tailwind CSS).

---

## 2. Configuration & Authentication (`CognIQ/settings.py`)

- **Environment Decoupling**: Uses `python-decouple` (`config()`).
- **Database Routing**:
  - `DEBUG=True`: Routes to local SQLite (`BASE_DIR / 'db.sqlite3'`).
  - `DEBUG=False`: Parses production PostgreSQL via `dj_database_url`.
- **Custom User Model**: `AUTH_USER_MODEL = 'myapp.User'`.
- **Authentication App**: `django-allauth` handles session authentication (`allauth`, `allauth.account`).
- **Registration Policy**: Public self-registration is **DISABLED**. `urls.py` overrides `accounts/signup/` to redirect to login. Accounts are created exclusively by School Admins or Teachers.
- **Timezone**: `TIME_ZONE = 'Asia/Kolkata'` (Indian Standard Time).

---

## 3. Data Models & Relationships ([`myapp/models.py`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/models.py))

```
┌─────────────────┐       1:N       ┌─────────────────┐
│     School      │ ────────────────┼─►     User      │
│  (Tenant Root)  │                 │ (Admin/Tch/Stu) │
└────────┬────────┘                 └────────┬────────┘
         │ 1:N                               │ 1:N (created_by)
         ▼                                   ▼
┌─────────────────┐       M:N       ┌─────────────────┐
│  StudentClass   │ ◄───────────────┤      Exam       │
│ (Dept/Batch/Sec)│                 │ (Duration/Marks)│
└─────────────────┘                 └────────┬────────┘
                                             │ M:N (via ExamQuestion)
                                             ▼
                                    ┌─────────────────┐       1:N       ┌─────────────────┐
                                    │    Question     │ ────────────────┼─►    Choice     │
                                    │ (Text/Expl/Marks│                 │ (Text/IsCorrect)│
                                    └────────┬────────┘                 └─────────────────┘
                                             │ 1:N
                                             ▼
                                    ┌─────────────────┐       1:N       ┌─────────────────┐
                                    │   ExamAttempt   │ ────────────────┼─► StudentAnswer │
                                    │(Score/Time/Order│                 │ (SelectedChoice)│
                                    └─────────────────┘                 └─────────────────┘
```

### Core Models & Fields

1. **`School`** ([models.py:L32](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/models.py#L32)): Multi-tenant root. Scopes all Users, Classes, Questions, and Exams.
   - Fields: `name`, `slug`, `address`, `phone`, `email`, `logo`, `is_active`.
2. **`User`** ([models.py:L187](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/models.py#L187)): Custom `AbstractUser`.
   - Fields: `username`, `email`, `role` (`teacher`, `student`, `admin`), `phone_number`, `batch`, `school` (FK).
   - Enforces strict school isolation in `clean()`.
3. **`StudentClass`** ([models.py:L285](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/models.py#L285)): Cohort grouping.
   - Fields: `name`, `description`, `batch`, `department`, `school` (FK), `created_by` (User FK), `students` (M2M User), `enrollment_code`, `allow_self_enrollment`.
4. **`Question`** ([models.py:L595](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/models.py#L595)): Shared question bank unit.
   - Fields: `school` (FK), `created_by` (User FK), `subject`, `department`, `chapter`, `question_text`, `marks`, `explanation`.
5. **`Choice`** ([models.py:L675](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/models.py#L675)): Options per question.
   - Fields: `question` (FK), `choice_text`, `is_correct`, `order`.
6. **`Exam`** ([models.py:L436](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/models.py#L436)): Assessment definition.
   - Fields: `title`, `subject`, `description`, `department`, `chapter`, `exam_type` (`practice_test`, `test`), `duration_minutes`, `total_marks`, `pass_percentage`, `school` (FK), `created_by` (User FK), `assigned_classes` (M2M StudentClass), `questions` (M2M via ExamQuestion).
7. **`ExamQuestion`** ([models.py:L659](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/models.py#L659)): Junction table preserving question order per exam.
   - Fields: `exam` (FK), `question` (FK), `order`.
8. **`ExamAssignmentDate`** ([models.py:L899](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/models.py#L899)): Tracks assignment timestamps per class.
   - Fields: `exam` (FK), `student_class` (FK), `assigned_at`.
9. **`ExamAttempt`** ([models.py:L715](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/models.py#L715)): Student test session audit trail.
   - Fields: `student` (User FK), `exam` (Exam FK), `student_class` (StudentClass FK), `attempt_mode`, `started_at`, `submitted_at`, `score`, `total_marks`, `is_completed`, `has_violation`, `violation_reason`, `question_order` (JSONField).
10. **`StudentAnswer`** ([models.py:L851](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/models.py#L851)): Recorded choice for each question per attempt.
    - Fields: `attempt` (ExamAttempt FK), `question` (Question FK), `selected_choice` (Choice FK), `is_correct`.

---

## 4. Front-End & Embedded JavaScript Architecture

JavaScript in CIT-CognIQ is **not** decoupled into external `.js` files. It is **embedded directly in Django HTML templates**:

- **[`templates/exams/exam_take.html`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/templates/exams/exam_take.html)**:
  - `updateTimer()`: Calculates remaining time from `started_at` timestamp + `duration_minutes`.
  - `updateProgress()`: Counts selected radio inputs and updates header progress bar.
  - Navigation Interception: `window.addEventListener('beforeunload')` + link click listener.
  - Proctoring Engine: `visibilitychange` & `blur` events track tab switches/window focus loss. Allows 1 warning; on 2nd violation, submits form with `has_violation=true`.
- **[`templates/exams/bulk_upload_preview.html`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/templates/exams/bulk_upload_preview.html)**: Interactive client-side CSV validation table.

---

## 5. Execution Flow Traces

### Flow A: User Login
1. **User Request**: User navigates to `/accounts/login/`.
2. **URL Mapping**: [`CognIQ/urls.py:L18`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/CognIQ/urls.py#L18) includes `allauth.urls`.
3. **View Processing**: `allauth.account.views.LoginView` renders [`templates/account/login.html`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/templates/account/login.html).
4. **Authentication**: Authenticates username and password against `myapp.User` model using Django session auth.
5. **Redirect**: Upon successful login, `LOGIN_REDIRECT_URL = '/dashboard/'` routes user to `views.dashboard` ([myapp/views.py:L23](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/views.py#L23)).
6. **Role Routing**: `dashboard` inspects `user.role`:
   - `teacher` ➔ `teacher_dashboard` ([views.py:L46](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/views.py#L46)) ➔ [`templates/dashboard/teacher_dashboard.html`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/templates/dashboard/teacher_dashboard.html).
   - `student` ➔ `student_dashboard` ([views.py:L110](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/views.py#L110)) ➔ [`templates/dashboard/student_dashboard.html`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/templates/dashboard/student_dashboard.html).
   - `admin` ➔ `school_admin_dashboard` ([views.py:L3169](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/views.py#L3169)) ➔ [`templates/school_admin/dashboard.html`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/templates/school_admin/dashboard.html).

---

### Flow B: Question Creation
1. **User Action**: Teacher clicks "Add Questions" on an Exam detail page.
2. **URL & View**: GET/POST `/exams/<exam_pk>/add-questions/` (`name='exam_add_questions'`) ➔ `views.exam_add_questions` ([myapp/views.py:L635](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/views.py#L635)).
3. **Form Processing**: Teacher submits POST payload containing `question_{i}_text`, `question_{i}_marks`, `question_{i}_choice_{j}_text`, and `question_{i}_choice_{j}_correct`.
4. **Database Operations** (inside `transaction.atomic()`):
   - Creates `Question` record (`school=exam.school`, `created_by=request.user`, `subject=exam.subject`, `question_text`, `marks`).
   - Creates `ExamQuestion` junction record (`exam=exam`, `question=question`, `order=base_order + i`).
   - Validates that exactly 4 choices exist and exactly 1 has `is_correct=True`.
   - Creates 4 `Choice` records (`question=question`, `choice_text`, `is_correct`, `order`).
   - Calls `exam.update_total_marks()`.
5. **Template & Redirect**: Redirects to `exam_detail` ([`templates/exams/exam_detail.html`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/templates/exams/exam_detail.html)).

---

### Flow C: Exam Creation & Assignment
1. **Creation Step**:
   - URL & View: GET/POST `/exams/create/` (`name='exam_create'`) ➔ `ExamCreateView` ([myapp/views.py:L394](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/views.py#L394)).
   - Form: Uses `ExamForm` ([`templates/exams/exam_form.html`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/templates/exams/exam_form.html)).
   - Save: Sets `created_by=request.user` and `school=request.user.school`, saving an `Exam` record.
2. **Assignment Step**:
   - URL & View: POST `/classes/<class_pk>/assign-exam/` (`name='class_assign_exam'`) ➔ `views.class_assign_exam` ([myapp/views.py:L2953](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/views.py#L2953)).
   - Database Action: Executes `exam.assigned_classes.add(student_class)` and creates an `ExamAssignmentDate` record (`exam=exam`, `student_class=student_class`).

---

### Flow D: Student Starts Exam
1. **User Action**: Student selects an assigned exam from `/student/exams/` ([`templates/exams/student_exam_list.html`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/templates/exams/student_exam_list.html)).
2. **URL & View**: GET `/student/exams/<exam_pk>/take/` (`name='exam_take'`) ➔ `views.exam_take` ([myapp/views.py:L1294](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/views.py#L1294)).
3. **Access & Mode Validation**:
   - Validates student belongs to an active `StudentClass` assigned to the exam.
   - Checks existing `ExamAttempt` records. If `exam_type=='test'` and a completed attempt exists, denies access and redirects to `exam_results`.
4. **Session Creation**:
   - Creates a new `ExamAttempt` row (`student=request.user`, `exam=exam`, `student_class=student_class`, `attempt_mode=mode`).
   - Fetches questions, shuffles question order (`random.shuffle(questions)`), and stores randomized order as JSON in `attempt.question_order`.
   - Shuffles choices per question (`question.shuffled_choices`).
5. **Template Rendering**: Renders [`templates/exams/exam_take.html`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/templates/exams/exam_take.html).

---

### Flow E: Student Answers (In-Exam Interaction)
1. **UI Action**: Student clicks a radio input choice `<input type="radio" name="question_{{ question.id }}" value="{{ choice.id }}">`.
2. **Client JS Execution**: Triggers `onchange="updateProgress()"` in `exam_take.html`.
3. **State Management**:
   - JS updates answered counter (`X/Y Answered`) and progress bar width.
   - JS highlights the selected option container label.
4. **Data Persistence Notice**: **No AJAX / background API request is sent.** Choices remain strictly in the browser DOM until full form submission.

---

### Flow F: Exam Submission
1. **Trigger**: Student clicks "Submit Exam", timer hits zero, or proctoring detects 2 focus violations.
2. **URL & View**: POST `/student/attempts/<attempt_pk>/submit/` (`name='exam_submit'`) ➔ `views.exam_submit` ([myapp/views.py:L1433](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/views.py#L1433)).
3. **Processing** (inside `transaction.atomic()`):
   - Server checks if `timezone.now() > end_time` (auto-submits if expired).
   - Iterates through `attempt.exam.questions.all()`.
   - Reads `choice_id = request.POST.get(f'question_{question.id}')`.
   - If `choice_id` exists, creates `StudentAnswer` (`attempt=attempt`, `question=question`, `selected_choice=selected_choice`).
   - Sets `submitted_at=timezone.now()` and `is_completed=True`.
   - Calls `attempt.calculate_score()`.
4. **Score Calculation**: In `ExamAttempt.calculate_score()` ([models.py:L840](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/models.py#L840)), sums `question.marks` for every `answer` where `is_correct==True`.
5. **Redirect**: Redirects to `exam_results` (`attempt_pk=attempt.pk`).

---

### Flow G: Result Viewing
1. **URL & View**: GET `/student/attempts/<attempt_pk>/results/` (`name='exam_results'`) ➔ `views.exam_results` ([myapp/views.py:L1522](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/myapp/views.py#L1522)).
2. **Data Retrieval**:
   - Queries `ExamAttempt` with `select_related('exam', 'student')`.
   - Reads `attempt.question_order` JSON to restore exact presentation order.
   - Retrieves `StudentAnswer` and `correct_choice` for each question.
3. **Template Rendering**: Renders [`templates/exams/exam_results.html`](file:///Users/pawaneswaran/Desktop/Work/PROJECTS/Aptitude-Project/CIT-CognIQ/templates/exams/exam_results.html).
4. **UI Displays**:
   - Score badge (`score / total_marks`, `percentage %`, Pass/Fail indicator).
   - Card per question displaying student selection, correct choice, correctness indicator, and teacher explanation.
