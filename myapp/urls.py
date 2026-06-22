from django.urls import path
from . import views
from . import exam_bank_views

urlpatterns = [
    # Home
    path('', views.home, name='home'),

    # --- Signup override: public self-registration is DISABLED ---
    path('accounts/signup/', views.signup_disabled, name='signup_disabled'),
    path('school/register/', views.register_school, name='register_school'),

    # Dashboards
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),

    # =====================================================
    # SCHOOL ADMIN PANEL (role='admin', school-scoped)
    # =====================================================
    path('school-admin/', views.school_admin_dashboard, name='school_admin_dashboard'),
    path('school-admin/settings/', views.school_admin_settings, name='school_admin_settings'),
    path('school-admin/teachers/', views.school_admin_manage_teachers, name='school_admin_manage_teachers'),
    path('school-admin/teachers/create/', views.school_admin_create_teacher, name='school_admin_create_teacher'),
    path('school-admin/teachers/bulk-create/', views.school_admin_bulk_create_teachers, name='school_admin_bulk_create_teachers'),
    path('school-admin/teachers/<int:teacher_id>/toggle/', views.school_admin_toggle_teacher, name='school_admin_toggle_teacher'),
    path('school-admin/students/', views.school_admin_manage_students, name='school_admin_manage_students'),
    path('school-admin/students/create/', views.school_admin_create_student, name='school_admin_create_student'),
    path('school-admin/students/bulk-create/', views.school_admin_bulk_create_students, name='school_admin_bulk_create_students'),
    path('school-admin/students/<int:student_id>/toggle/', views.school_admin_toggle_student, name='school_admin_toggle_student'),
    path('school-admin/classes/', views.school_admin_classes_overview, name='school_admin_classes_overview'),
    path('school-admin/reset-password/<int:user_id>/', views.school_admin_reset_user_password, name='school_admin_reset_user_password'),

    # =====================================================
    # EXAM MANAGEMENT (Teacher)
    # =====================================================
    path('exams/', views.ExamListView.as_view(), name='exam_list'),
    path('exams/create/', views.ExamCreateView.as_view(), name='exam_create'),
    path('exams/<int:pk>/', views.ExamDetailView.as_view(), name='exam_detail'),
    path('exams/<int:pk>/edit/', views.ExamUpdateView.as_view(), name='exam_update'),
    path('exams/<int:pk>/delete/', views.ExamDeleteView.as_view(), name='exam_delete'),

    # Question Management
    path('exams/<int:exam_pk>/add-questions/', views.exam_add_questions, name='exam_add_questions'),
    path('exams/<int:exam_pk>/question/<int:question_pk>/edit/', views.question_edit, name='question_edit'),
    path('exams/<int:exam_pk>/question/<int:question_pk>/delete/', views.question_delete, name='question_delete'),

    # Shared Exam Bank
    path('exam-bank/', exam_bank_views.exam_bank, name='exam_bank'),
    path('exam-bank/api/categories/', exam_bank_views.api_search_categories, name='api_search_categories'),
    path('exam-bank/<int:exam_pk>/assign/', exam_bank_views.assign_exam_from_bank, name='assign_exam_from_bank'),
    path('exam-bank/<int:exam_pk>/clone/', exam_bank_views.clone_exam, name='clone_exam'),

    # Bulk Question Upload
    path('exams/<int:exam_pk>/bulk-upload/', views.bulk_upload_questions, name='bulk_upload_questions'),
    path('exams/<int:exam_pk>/bulk-upload/preview/', views.bulk_upload_preview, name='bulk_upload_preview'),
    path('exams/<int:exam_pk>/bulk-upload/confirm/', views.bulk_upload_confirm, name='bulk_upload_confirm'),
    path('exams/<int:exam_pk>/download-template/', views.download_question_template, name='download_question_template'),

    # =====================================================
    # STUDENT EXAM TAKING
    # =====================================================
    path('student/exams/', views.student_exam_list, name='student_exam_list'),
    path('student/exams/<int:exam_pk>/take/', views.exam_take, name='exam_take'),
    path('student/attempts/<int:attempt_pk>/submit/', views.exam_submit, name='exam_submit'),
    path('student/attempts/<int:attempt_pk>/results/', views.exam_results, name='exam_results'),
    path('student/history/', views.attempt_history, name='attempt_history'),

    # =====================================================
    # TEACHER ANALYTICS
    # =====================================================
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('analytics/exam/<int:exam_pk>/', views.exam_analytics, name='exam_analytics'),
    path('analytics/student/<int:student_id>/', views.student_analytics, name='student_analytics'),
    path('analytics/exam/<int:exam_pk>/questions/', views.question_analytics, name='question_analytics'),

    # Teacher Response Management (Google Forms Style)
    path('teacher/responses/', views.teacher_exam_responses, name='teacher_exam_responses'),
    path('teacher/responses/attempt/<int:attempt_pk>/', views.teacher_view_attempt, name='teacher_view_attempt'),
    path('teacher/responses/api/search-exams/', views.api_search_exams, name='api_search_exams'),

    # =====================================================
    # CLASS MANAGEMENT (Teacher)
    # =====================================================
    path('classes/', views.class_list, name='class_list'),
    path('classes/create/', views.class_create, name='class_create'),
    path('classes/<int:class_pk>/', views.class_detail, name='class_detail'),
    path('classes/<int:class_pk>/edit/', views.class_update, name='class_update'),
    path('classes/<int:class_pk>/delete/', views.class_delete, name='class_delete'),
    path('classes/<int:class_pk>/search-students/', views.search_students_for_class, name='search_students_for_class'),
    path('classes/<int:class_pk>/search-exams/', views.search_exams_for_class, name='search_exams_for_class'),
    path('classes/<int:class_pk>/add-students/', views.class_add_students, name='class_add_students'),
    path('classes/<int:class_pk>/remove-student/<int:student_id>/', views.class_remove_student, name='class_remove_student'),
    path('classes/<int:class_pk>/assign-exam/', views.class_assign_exam, name='class_assign_exam'),
    path('classes/<int:class_pk>/unassign-exam/<int:exam_pk>/', views.class_unassign_exam, name='class_unassign_exam'),

    # =====================================================
    # STUDENT PROGRESS TRACKING
    # =====================================================
    path('student/progress/', views.student_progress_dashboard, name='student_progress_dashboard'),
    path('student/progress/exam/<int:exam_id>/', views.exam_progress, name='exam_progress'),
    path('student/progress/subject/<str:subject>/', views.subject_progress, name='subject_progress'),

    # Leaderboard (Class-scoped only)
    path('leaderboard/class/<int:class_id>/', views.class_leaderboard, name='class_leaderboard'),
    path('rankings/', views.student_rankings, name='student_rankings'),

    # =====================================================
    # ENROLLMENT SYSTEM
    # =====================================================
    path('enrollment/', views.student_enrollment, name='student_enrollment'),
    path('enrollment/join/', views.join_class_by_code, name='join_class_by_code'),
    path('enrollment/leave/<int:class_pk>/', views.leave_class, name='leave_class'),
    path('classes/<int:class_pk>/toggle-enrollment/', views.toggle_self_enrollment, name='toggle_self_enrollment'),
    path('classes/<int:class_pk>/regenerate-code/', views.regenerate_enrollment_code, name='regenerate_enrollment_code'),
    path('classes/<int:class_pk>/enrollment-settings/', views.class_enrollment_settings, name='class_enrollment_settings'),

    # =====================================================
    # PROFILE / SETTINGS
    # =====================================================
    path('settings/profile/', views.profile_settings, name='profile_settings'),
    path('settings/change-password/', views.teacher_change_password, name='teacher_change_password'),

    # Teacher Password Reset for Students (Class-scoped)
    path('teacher/reset-password/<int:student_id>/', views.teacher_reset_student_password, name='teacher_reset_student_password'),

    # Teacher Retest Authorization (Class-scoped)
    path('teacher/retest/<int:attempt_pk>/', views.teacher_retest_exam, name='teacher_retest_exam'),
]
