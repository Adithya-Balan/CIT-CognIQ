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
