from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import json
from myapp.models import (
    School, User, StudentClass, Question, Choice, Exam, ExamQuestion, ExamAttempt, StudentAnswer
)


class CoreExamEngineTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name='Chennai Institute of Technology',
            slug='chennai-institute-of-technology'
        )
        self.teacher = User.objects.create_user(
            username='teacher_test',
            first_name='Faculty',
            last_name='User',
            role='teacher',
            password='Teacher@12345',
            school=self.school
        )
        self.student = User.objects.create_user(
            username='student1',
            first_name='Student',
            last_name='One',
            role='student',
            password='Student@12345',
            school=self.school,
            batch='2024-2028'
        )
        self.student_class = StudentClass.objects.create(
            name='CSBS 2024-2028',
            batch='2024-2028',
            department='Computer Science & Business Systems',
            created_by=self.teacher,
            school=self.school
        )
        self.student_class.students.add(self.student)

        # Create Exam
        self.exam = Exam.objects.create(
            title='Aptitude Mock Test 01',
            subject='Aptitude',
            department='Computer Science & Business Systems',
            chapter='General Aptitude',
            exam_type='test',
            duration_minutes=30,
            pass_percentage=40,
            created_by=self.teacher,
            school=self.school
        )
        self.exam.assigned_classes.add(self.student_class)

        # Create 10 Questions with 4 choices each
        self.questions = []
        for i in range(1, 11):
            q = Question.objects.create(
                school=self.school,
                created_by=self.teacher,
                subject='Aptitude',
                chapter='General Aptitude',
                question_text=f'Question {i} text',
                marks=1
            )
            ExamQuestion.objects.create(exam=self.exam, question=q, order=i)
            # Create choices
            Choice.objects.create(question=q, choice_text='Option A', is_correct=True, order=1)
            Choice.objects.create(question=q, choice_text='Option B', is_correct=False, order=2)
            Choice.objects.create(question=q, choice_text='Option C', is_correct=False, order=3)
            Choice.objects.create(question=q, choice_text='Option D', is_correct=False, order=4)
            self.questions.append(q)

        self.exam.update_total_marks()

    def test_01_student_login_and_exam_start(self):
        """Test student login, exam list, and starting an attempt."""
        login_success = self.client.login(username='student1', password='Student@12345')
        self.assertTrue(login_success)

        # Get exam list
        res = self.client.get(reverse('student_exam_list'))
        self.assertEqual(res.status_code, 200)

        # Start exam
        res_take = self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}))
        self.assertEqual(res_take.status_code, 200)

        # Verify ExamAttempt created with in_progress status
        attempt = ExamAttempt.objects.filter(student=self.student, exam=self.exam).first()
        self.assertIsNotNone(attempt)
        self.assertEqual(attempt.status, 'in_progress')
        self.assertFalse(attempt.is_completed)

    def test_02_attempt_resumption_on_refresh(self):
        """Test that refreshing browser reuses the existing active ExamAttempt."""
        self.client.login(username='student1', password='Student@12345')
        
        # 1st request
        self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}))
        count1 = ExamAttempt.objects.filter(student=self.student, exam=self.exam).count()

        # 2nd request (refresh)
        self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}))
        count2 = ExamAttempt.objects.filter(student=self.student, exam=self.exam).count()

        self.assertEqual(count1, 1)
        self.assertEqual(count2, 1)

    def test_03_realtime_autosave_and_state_persistence(self):
        """Test answer autosaving via AJAX and state progression."""
        self.client.login(username='student1', password='Student@12345')
        self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}))
        attempt = ExamAttempt.objects.get(student=self.student, exam=self.exam)

        q1 = self.questions[0]
        c1 = q1.choices.filter(is_correct=True).first()

        # Autosave answer for Q1
        save_url = reverse('api_save_answer', kwargs={'attempt_pk': attempt.pk})
        res = self.client.post(
            save_url,
            data=json.dumps({
                'question_id': q1.id,
                'choice_id': c1.id,
                'action': 'save',
                'is_marked_for_review': False
            }),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['state'], 'answered')

        # Verify StudentAnswer persisted in DB
        sa = StudentAnswer.objects.get(attempt=attempt, question=q1)
        self.assertEqual(sa.selected_choice, c1)
        self.assertEqual(sa.state, 'answered')

    def test_04_mark_for_review_and_clear_response(self):
        """Test marking for review, toggle review, and clear response."""
        self.client.login(username='student1', password='Student@12345')
        self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}))
        attempt = ExamAttempt.objects.get(student=self.student, exam=self.exam)
        save_url = reverse('api_save_answer', kwargs={'attempt_pk': attempt.pk})

        q2 = self.questions[1]
        c2 = q2.choices.filter(is_correct=True).first()

        # 1. Answer + Mark for review
        self.client.post(
            save_url,
            data=json.dumps({
                'question_id': q2.id,
                'choice_id': c2.id,
                'action': 'save',
                'is_marked_for_review': True
            }),
            content_type='application/json'
        )
        sa = StudentAnswer.objects.get(attempt=attempt, question=q2)
        self.assertEqual(sa.state, 'answered_marked_for_review')

        # 2. Clear response
        self.client.post(
            save_url,
            data=json.dumps({
                'question_id': q2.id,
                'choice_id': None,
                'action': 'clear',
                'is_marked_for_review': True
            }),
            content_type='application/json'
        )
        sa.refresh_from_db()
        self.assertIsNone(sa.selected_choice)
        self.assertEqual(sa.state, 'marked_for_review')

    def test_05_server_authoritative_timer_and_timeout(self):
        """Test that server remaining time is authoritative and expired attempts block modification."""
        self.client.login(username='student1', password='Student@12345')
        self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}))
        attempt = ExamAttempt.objects.get(student=self.student, exam=self.exam)

        # Force start time to 31 minutes ago (past 30 min duration)
        attempt.started_at = timezone.now() - timedelta(minutes=31)
        attempt.save()

        save_url = reverse('api_save_answer', kwargs={'attempt_pk': attempt.pk})
        q1 = self.questions[0]
        c1 = q1.choices.first()

        # Attempt to save after duration expired
        res = self.client.post(
            save_url,
            data=json.dumps({
                'question_id': q1.id,
                'choice_id': c1.id,
                'action': 'save'
            }),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 400)
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, 'timed_out')
        self.assertTrue(attempt.is_completed)

    def test_06_final_submission_and_score_calculation(self):
        """Test final submission and score calculation."""
        self.client.login(username='student1', password='Student@12345')
        self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}))
        attempt = ExamAttempt.objects.get(student=self.student, exam=self.exam)
        save_url = reverse('api_save_answer', kwargs={'attempt_pk': attempt.pk})

        # Answer 8 questions correctly out of 10
        for i in range(8):
            q = self.questions[i]
            correct_c = q.choices.get(is_correct=True)
            self.client.post(
                save_url,
                data=json.dumps({'question_id': q.id, 'choice_id': correct_c.id, 'action': 'save'}),
                content_type='application/json'
            )

        # Submit exam
        submit_url = reverse('exam_submit', kwargs={'attempt_pk': attempt.pk})
        res = self.client.post(submit_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(res.status_code, 200)

        attempt.refresh_from_db()
        self.assertTrue(attempt.is_completed)
        self.assertEqual(attempt.status, 'submitted')
        self.assertEqual(attempt.score, 8)

    # =========================================================================
    # REFRESH & STATE CONTRACT HARDENING TESTS (TESTS A, B, C, D)
    # =========================================================================

    def test_A_fresh_exam_start_all_questions_not_visited(self):
        """Test A: Start new exam where no StudentAnswer exists -> HTTP 200, all questions state 'not_visited'."""
        self.client.login(username='student1', password='Student@12345')
        res = self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}))
        self.assertEqual(res.status_code, 200)
        
        # Inspect context questions
        questions_in_ctx = res.context['questions']
        self.assertEqual(len(questions_in_ctx), 10)
        for q in questions_in_ctx:
            self.assertEqual(q.state, 'not_visited')
            self.assertIsNone(q.selected_choice_id)
            self.assertFalse(q.is_marked_for_review)

    def test_B_answer_one_question_and_refresh(self):
        """Test B: Answer Q1, refresh -> Q1 state 'answered', others 'not_visited', no template error."""
        self.client.login(username='student1', password='Student@12345')
        self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}))
        attempt = ExamAttempt.objects.get(student=self.student, exam=self.exam)

        q1 = self.questions[0]
        c1 = q1.choices.first()

        # Autosave answer for Q1
        save_url = reverse('api_save_answer', kwargs={'attempt_pk': attempt.pk})
        self.client.post(
            save_url,
            data=json.dumps({'question_id': q1.id, 'choice_id': c1.id, 'action': 'save'}),
            content_type='application/json'
        )

        # Refresh page (re-GET exam_take)
        res_refresh = self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}))
        self.assertEqual(res_refresh.status_code, 200)

        questions_in_ctx = {q.id: q for q in res_refresh.context['questions']}
        self.assertEqual(questions_in_ctx[q1.id].state, 'answered')
        self.assertEqual(questions_in_ctx[q1.id].selected_choice_id, c1.id)

        for q_id, q in questions_in_ctx.items():
            if q_id != q1.id:
                self.assertEqual(q.state, 'not_visited')

    def test_C_mark_for_review_and_refresh(self):
        """Test C: Mark question for review, refresh -> marked_for_review state persists, no template error."""
        self.client.login(username='student1', password='Student@12345')
        self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}))
        attempt = ExamAttempt.objects.get(student=self.student, exam=self.exam)

        q2 = self.questions[1]
        save_url = reverse('api_save_answer', kwargs={'attempt_pk': attempt.pk})
        self.client.post(
            save_url,
            data=json.dumps({'question_id': q2.id, 'choice_id': None, 'action': 'toggle_review', 'is_marked_for_review': True}),
            content_type='application/json'
        )

        # Refresh page
        res_refresh = self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}))
        self.assertEqual(res_refresh.status_code, 200)

        questions_in_ctx = {q.id: q for q in res_refresh.context['questions']}
        self.assertEqual(questions_in_ctx[q2.id].state, 'marked_for_review')
        self.assertTrue(questions_in_ctx[q2.id].is_marked_for_review)

    def test_D_clear_answer_and_refresh(self):
        """Test D: Answer Q1, then clear answer, refresh -> question is visited_unanswered, no template error."""
        self.client.login(username='student1', password='Student@12345')
        self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}))
        attempt = ExamAttempt.objects.get(student=self.student, exam=self.exam)
        save_url = reverse('api_save_answer', kwargs={'attempt_pk': attempt.pk})

        q1 = self.questions[0]
        c1 = q1.choices.first()

        # 1. Answer Q1
        self.client.post(
            save_url,
            data=json.dumps({'question_id': q1.id, 'choice_id': c1.id, 'action': 'save'}),
            content_type='application/json'
        )

        # 2. Clear Q1
        self.client.post(
            save_url,
            data=json.dumps({'question_id': q1.id, 'choice_id': None, 'action': 'clear'}),
            content_type='application/json'
        )

        # Refresh page
        res_refresh = self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}))
        self.assertEqual(res_refresh.status_code, 200)

        questions_in_ctx = {q.id: q for q in res_refresh.context['questions']}
        self.assertEqual(questions_in_ctx[q1.id].state, 'visited_unanswered')
        self.assertIsNone(questions_in_ctx[q1.id].selected_choice_id)

    def test_E_question_url_parameter_support(self):
        """Test E: Requesting exam take with ?question=5 loads successfully and includes URL param logic."""
        self.client.login(username='student1', password='Student@12345')
        res = self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}) + '?question=5')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'getInitialQuestionIndex')

    def test_instructions_page_loads_and_does_not_create_attempt(self):
        """Test instructions page loads for student and DOES NOT create an ExamAttempt."""
        self.client.login(username='student1', password='Student@12345')
        instructions_url = reverse('exam_instructions', kwargs={'exam_pk': self.exam.pk})
        
        # Verify no attempt before loading instructions
        self.assertEqual(ExamAttempt.objects.filter(student=self.student, exam=self.exam).count(), 0)

        res = self.client.get(instructions_url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'General Instructions')
        self.assertContains(res, 'Marking Scheme')
        self.assertContains(res, 'ackCheckbox')

        # Verify STILL no attempt after loading instructions
        self.assertEqual(ExamAttempt.objects.filter(student=self.student, exam=self.exam).count(), 0)

    def test_start_exam_creates_attempt_and_resumes_without_duplicates(self):
        """Test clicking Start Exam creates an attempt, and starting twice resumes existing attempt."""
        self.client.login(username='student1', password='Student@12345')
        take_url = reverse('exam_take', kwargs={'exam_pk': self.exam.pk})

        # First visit to exam_take (Simulating clicking "Start Exam ->")
        res1 = self.client.get(take_url)
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(ExamAttempt.objects.filter(student=self.student, exam=self.exam).count(), 1)
        attempt1 = ExamAttempt.objects.get(student=self.student, exam=self.exam)

        # Second visit to exam_take (Simulating clicking "Start Exam ->" or "Resume Exam ->" again)
        res2 = self.client.get(take_url)
        self.assertEqual(res2.status_code, 200)

        # Verify NO duplicate attempt was created
        self.assertEqual(ExamAttempt.objects.filter(student=self.student, exam=self.exam).count(), 1)
        attempt2 = ExamAttempt.objects.get(student=self.student, exam=self.exam)
        self.assertEqual(attempt1.pk, attempt2.pk)

    # =========================================================================
    # PROCTORING & EVENT DETECTION TESTS (TESTS 1 to 12)
    # =========================================================================

    def test_01_practice_attempt_loads_without_proctoring(self):
        """TEST 1 & 2: Practice attempt loads and refreshes with is_proctored=False."""
        # Create practice_test exam
        practice_exam = Exam.objects.create(
            title='Practice & Test Exam',
            subject='Aptitude',
            department='Computer Science & Business Systems',
            chapter='General Aptitude',
            exam_type='practice_test',
            duration_minutes=30,
            pass_percentage=40,
            created_by=self.teacher,
            school=self.school
        )
        practice_exam.assigned_classes.add(self.student_class)
        for i, q in enumerate(self.questions[:5], start=1):
            ExamQuestion.objects.create(exam=practice_exam, question=q, order=i)

        self.client.login(username='student1', password='Student@12345')
        res = self.client.get(reverse('exam_take', kwargs={'exam_pk': practice_exam.pk}) + '?mode=practice')
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.context['is_proctored'])
        self.assertEqual(res.context['attempt'].attempt_mode, 'practice')

        # Refresh practice attempt
        res_refresh = self.client.get(reverse('exam_take', kwargs={'exam_pk': practice_exam.pk}) + '?mode=practice')
        self.assertEqual(res_refresh.status_code, 200)
        self.assertFalse(res_refresh.context['is_proctored'])

    def test_03_actual_take_test_attempt_has_proctoring_enabled(self):
        """TEST 3 & 9: Actual Take Test attempt enables is_proctored=True and persists on refresh."""
        self.client.login(username='student1', password='Student@12345')
        res = self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}) + '?mode=test')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.context['is_proctored'])
        self.assertEqual(res.context['attempt'].attempt_mode, 'test')

        # Refresh
        res_refresh = self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}))
        self.assertEqual(res_refresh.status_code, 200)
        self.assertTrue(res_refresh.context['is_proctored'])

    def test_04_test_first_violation_records_warning(self):
        """TEST 4: First violation returns warning and does not terminate exam."""
        self.client.login(username='student1', password='Student@12345')
        self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}) + '?mode=test')
        attempt = ExamAttempt.objects.get(student=self.student, exam=self.exam)

        event_url = reverse('api_record_event', kwargs={'attempt_pk': attempt.pk})
        res = self.client.post(
            event_url,
            data=json.dumps({'event_type': 'Tab switch', 'violation_count': 1}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'warning')

        attempt.refresh_from_db()
        self.assertFalse(attempt.has_violation)
        self.assertFalse(attempt.is_completed)
        self.assertEqual(attempt.status, 'in_progress')

    def test_05_five_violation_lifecycle_and_termination(self):
        """TEST 5 & L: Violations 1 to 4 issue warnings, 5th violation terminates attempt."""
        self.client.login(username='student1', password='Student@12345')
        self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}) + '?mode=test')
        attempt = ExamAttempt.objects.get(student=self.student, exam=self.exam)

        event_url = reverse('api_record_event', kwargs={'attempt_pk': attempt.pk})
        
        # Violations 1 through 4 should only issue warnings
        for v in range(1, 5):
            res = self.client.post(
                event_url,
                data=json.dumps({'event_type': 'TAB_SWITCH', 'reason': f'Tab switch #{v}', 'violation_count': v}),
                content_type='application/json'
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data['action'], 'warning')
            self.assertEqual(data['violation_count'], v)
            self.assertEqual(data['max_violations'], 5)

            attempt.refresh_from_db()
            self.assertFalse(attempt.has_violation)
            self.assertFalse(attempt.is_completed)
            self.assertEqual(attempt.status, 'in_progress')

        # 5th violation terminates exam
        res5 = self.client.post(
            event_url,
            data=json.dumps({'event_type': 'FULLSCREEN_EXIT', 'reason': 'ESC pressed', 'violation_count': 5}),
            content_type='application/json'
        )
        self.assertEqual(res5.status_code, 200)
        data5 = res5.json()
        self.assertTrue(data5['success'])
        self.assertEqual(data5['action'], 'terminate')
        self.assertEqual(data5['violation_count'], 5)
        self.assertEqual(data5['max_violations'], 5)

        attempt.refresh_from_db()
        self.assertTrue(attempt.has_violation)
        self.assertTrue(attempt.is_completed)
        self.assertEqual(attempt.status, 'terminated')

    def test_06_refresh_active_test_preserves_violation_count(self):
        """TEST Q: Refreshing active test keeps proctoring enabled and preserves server violation count."""
        self.client.login(username='student1', password='Student@12345')
        self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}) + '?mode=test')
        attempt = ExamAttempt.objects.get(student=self.student, exam=self.exam)

        event_url = reverse('api_record_event', kwargs={'attempt_pk': attempt.pk})
        self.client.post(
            event_url,
            data=json.dumps({'event_type': 'WINDOW_FOCUS_LOSS', 'reason': 'Window lost focus', 'violation_count': 1}),
            content_type='application/json'
        )

        # Refresh page
        res_refresh = self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}))
        self.assertEqual(res_refresh.status_code, 200)
        self.assertTrue(res_refresh.context['is_proctored'])
        self.assertEqual(res_refresh.context['initial_violation_count'], 1)

    def test_10_practice_attempt_ignores_violation_endpoint(self):
        """TEST 10 & O: Attempting to call violation endpoint on a practice attempt is rejected/ignored."""
        practice_exam = Exam.objects.create(
            title='Practice Exam',
            subject='Aptitude',
            department='Computer Science & Business Systems',
            chapter='General Aptitude',
            exam_type='practice_test',
            duration_minutes=30,
            pass_percentage=40,
            created_by=self.teacher,
            school=self.school
        )
        practice_exam.assigned_classes.add(self.student_class)

        self.client.login(username='student1', password='Student@12345')
        self.client.get(reverse('exam_take', kwargs={'exam_pk': practice_exam.pk}) + '?mode=practice')
        attempt = ExamAttempt.objects.get(student=self.student, exam=practice_exam)
        self.assertEqual(attempt.attempt_mode, 'practice')

        event_url = reverse('api_record_event', kwargs={'attempt_pk': attempt.pk})
        res = self.client.post(
            event_url,
            data=json.dumps({'event_type': 'TAB_SWITCH', 'reason': 'Tab switched', 'violation_count': 2}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get('ignored'))

        attempt.refresh_from_db()
        self.assertFalse(attempt.has_violation)
        self.assertFalse(attempt.is_completed)
        self.assertEqual(attempt.status, 'in_progress')

    def test_11_other_student_cannot_send_event(self):
        """TEST 11 & P: Attempt to send event for another student's attempt returns 404."""
        student2 = User.objects.create_user(
            username='student2',
            first_name='Student',
            last_name='Two',
            role='student',
            password='Student@12345',
            school=self.school
        )
        self.student_class.students.add(student2)

        # Create attempt for student 1
        self.client.login(username='student1', password='Student@12345')
        self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}))
        attempt = ExamAttempt.objects.get(student=self.student, exam=self.exam)

        # Login as student 2 and attempt to send violation for student 1's attempt
        self.client.login(username='student2', password='Student@12345')
        event_url = reverse('api_record_event', kwargs={'attempt_pk': attempt.pk})
        res = self.client.post(
            event_url,
            data=json.dumps({'event_type': 'FULLSCREEN_EXIT', 'reason': 'ESC pressed', 'violation_count': 1}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 404)

    def test_12_completed_attempt_event_rejected(self):
        """TEST 12: Inactive/completed attempt rejects new events with 400."""
        self.client.login(username='student1', password='Student@12345')
        self.client.get(reverse('exam_take', kwargs={'exam_pk': self.exam.pk}))
        attempt = ExamAttempt.objects.get(student=self.student, exam=self.exam)

        # Submit attempt
        submit_url = reverse('exam_submit', kwargs={'attempt_pk': attempt.pk})
        self.client.post(submit_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        # Send event on submitted attempt
        event_url = reverse('api_record_event', kwargs={'attempt_pk': attempt.pk})
        res = self.client.post(
            event_url,
            data=json.dumps({'event_type': 'TAB_SWITCH', 'reason': 'Tab switched', 'violation_count': 1}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 400)



