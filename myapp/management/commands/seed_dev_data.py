from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from myapp.models import (
    School, User, StudentClass, Question, Choice,
    Exam, ExamQuestion, ExamAttempt, StudentAnswer, ExamAssignmentDate
)


class Command(BaseCommand):
    help = 'Idempotently seed small development dataset for CIT-CognIQ application'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- Seeding Development Data ---'))
        
        with transaction.atomic():
            school = self.seed_school()
            admin_user, teacher_user, students = self.seed_users(school)
            csbs_class = self.seed_class(school, teacher_user, students)
            questions = self.seed_questions(school, teacher_user)
            exams = self.seed_exams(school, teacher_user, questions, csbs_class)
            attempt = self.seed_student2_attempt(students[1], exams[0], csbs_class)

        self.stdout.write(self.style.SUCCESS('\n=== DEVELOPMENT DATA CREATED SUCCESSFULLY ===\n'))
        self.print_summary(school, admin_user, teacher_user, students, csbs_class, exams, questions)

    def seed_school(self):
        school = School.objects.filter(slug='chennai-institute-of-technology').first()
        if not school:
            default_school = School.objects.filter(slug='default-school').first()
            if default_school:
                school = default_school
                school.name = 'Chennai Institute of Technology'
                school.slug = 'chennai-institute-of-technology'
                school.address = 'Sarathy Nagar, Kundrathur, Chennai, Tamil Nadu 600069'
                school.phone = '044-71119111'
                school.email = 'info@cit.edu.in'
                school.is_active = True
                school.save()
            else:
                school = School.objects.create(
                    name='Chennai Institute of Technology',
                    slug='chennai-institute-of-technology',
                    address='Sarathy Nagar, Kundrathur, Chennai, Tamil Nadu 600069',
                    phone='044-71119111',
                    email='info@cit.edu.in',
                    is_active=True
                )
        return school

    def seed_users(self, school):
        # 1. Admin
        admin_user = User.objects.filter(username='admin_test').first()
        if not admin_user:
            admin_user = User.objects.create_superuser(
                username='admin_test',
                first_name='System',
                last_name='Admin',
                role='admin',
                email='admin_test@cit.edu',
                password='Admin@12345',
                school=school
            )
        else:
            admin_user.first_name = 'System'
            admin_user.last_name = 'Admin'
            admin_user.email = 'admin_test@cit.edu'
            admin_user.school = school
            admin_user.set_password('Admin@12345')
            admin_user.save()

        # 2. Teacher
        teacher_user = User.objects.filter(username='teacher_test').first()
        if not teacher_user:
            teacher_user = User.objects.create_user(
                username='teacher_test',
                first_name='Faculty',
                last_name='Member',
                role='teacher',
                email='teacher_test@cit.edu',
                password='Teacher@12345',
                school=school
            )
        else:
            teacher_user.first_name = 'Faculty'
            teacher_user.last_name = 'Member'
            teacher_user.email = 'teacher_test@cit.edu'
            teacher_user.school = school
            teacher_user.set_password('Teacher@12345')
            teacher_user.save()

        # 3. Students (student1, student2, student3)
        student_data = [
            ('student1', 'Student', 'One', 'student1@cit.edu'),
            ('student2', 'Student', 'Two', 'student2@cit.edu'),
            ('student3', 'Student', 'Three', 'student3@cit.edu'),
        ]
        students = []
        for uname, fname, lname, email in student_data:
            st = User.objects.filter(username=uname).first()
            if not st:
                st = User.objects.create_user(
                    username=uname,
                    first_name=fname,
                    last_name=lname,
                    role='student',
                    email=email,
                    password='Student@12345',
                    school=school,
                    batch='2024-2028'
                )
            else:
                st.first_name = fname
                st.last_name = lname
                st.email = email
                st.school = school
                st.batch = '2024-2028'
                st.set_password('Student@12345')
                st.save()
            students.append(st)

        return admin_user, teacher_user, students

    def seed_class(self, school, teacher_user, students):
        csbs_class, created = StudentClass.objects.get_or_create(
            name='CSBS 2024-2028',
            batch='2024-2028',
            created_by=teacher_user,
            school=school,
            defaults={
                'department': 'Computer Science & Business Systems',
                'description': 'Computer Science & Business Systems Batch 2024-2028',
                'is_active': True,
                'allow_self_enrollment': True,
            }
        )
        if not csbs_class.enrollment_code:
            csbs_class.generate_enrollment_code()
        csbs_class.students.set(students)
        return csbs_class

    def seed_questions(self, school, teacher_user):
        raw_questions = [
            # 1. Quant
            {
                'chapter': 'Percentages',
                'text': 'What is 20% of 200?',
                'choices': [('20', False), ('30', False), ('40', True), ('50', False)],
                'explanation': '20% of 200 = (20 / 100) * 200 = 40.',
            },
            # 2. Quant
            {
                'chapter': 'Algebra',
                'text': 'If x + 5 = 12, what is x?',
                'choices': [('5', False), ('6', False), ('7', True), ('8', False)],
                'explanation': 'x = 12 - 5 = 7.',
            },
            # 3. Logical
            {
                'chapter': 'Number Series',
                'text': 'What comes next in the sequence: 2, 4, 6, 8, ?',
                'choices': [('9', False), ('10', True), ('11', False), ('12', False)],
                'explanation': 'Even number sequence increasing by +2. Next number is 10.',
            },
            # 4. Logical
            {
                'chapter': 'Deductive Logic',
                'text': 'If all cats are animals and Tom is a cat, Tom is:',
                'choices': [('A plant', False), ('An animal', True), ('A vehicle', False), ('None', False)],
                'explanation': 'Tom belongs to the category of cats, which are all animals.',
            },
            # 5. Verbal
            {
                'chapter': 'Vocabulary',
                'text': 'Choose the synonym of "rapid".',
                'choices': [('Slow', False), ('Fast', True), ('Weak', False), ('Small', False)],
                'explanation': '"Rapid" means happening in a short time or moving quickly; synonym is "Fast".',
            },
            # 6. Verbal
            {
                'chapter': 'Vocabulary',
                'text': 'Choose the antonym of "ancient".',
                'choices': [('Old', False), ('Historic', False), ('Modern', True), ('Traditional', False)],
                'explanation': '"Ancient" means very old; its opposite is "Modern".',
            },
            # 7. Quant
            {
                'chapter': 'Basic Arithmetic',
                'text': 'What is 15 + 27?',
                'choices': [('32', False), ('42', True), ('52', False), ('62', False)],
                'explanation': '15 + 27 = 42.',
            },
            # 8. Logical
            {
                'chapter': 'Calendar Logic',
                'text': 'If Monday is day 1, what is day 5?',
                'choices': [('Wednesday', False), ('Thursday', False), ('Friday', True), ('Saturday', False)],
                'explanation': 'Day 1: Mon, Day 2: Tue, Day 3: Wed, Day 4: Thu, Day 5: Fri.',
            },
            # 9. Quant
            {
                'chapter': 'Profit and Loss',
                'text': 'A product costs ₹100 and is discounted by 10%. What is the final price?',
                'choices': [('₹80', False), ('₹85', False), ('₹90', True), ('₹95', False)],
                'explanation': 'Discount = 10% of 100 = ₹10. Final price = 100 - 10 = ₹90.',
            },
            # 10. Verbal
            {
                'chapter': 'Spelling',
                'text': 'Choose the correctly spelled word.',
                'choices': [('Recieve', False), ('Receive', True), ('Receeve', False), ('Receve', False)],
                'explanation': 'The correct spelling is "Receive" (i before e except after c).',
            },
            # 11. Quant
            {
                'chapter': 'Geometry',
                'text': 'What is the area of a square with a side length of 5 cm?',
                'choices': [('20 sq cm', False), ('25 sq cm', True), ('30 sq cm', False), ('10 sq cm', False)],
                'explanation': 'Area of square = side * side = 5 * 5 = 25 sq cm.',
            },
            # 12. Logical
            {
                'chapter': 'Classification',
                'text': 'Find the odd one out: Circle, Square, Triangle, Cube.',
                'choices': [('Circle', False), ('Square', False), ('Triangle', False), ('Cube', True)],
                'explanation': 'Cube is a 3D geometric shape, whereas Circle, Square, and Triangle are 2D shapes.',
            },
            # 13. Verbal
            {
                'chapter': 'Prepositions',
                'text': 'Fill in the blank: "She is good ___ playing chess."',
                'choices': [('in', False), ('at', True), ('with', False), ('on', False)],
                'explanation': 'The adjective "good" takes the preposition "at" when referring to ability or skill.',
            },
            {
                'chapter': 'Computer Science',
                'text': 'Which computer component is commonly referred to as the brain of the computer?',
                'choices': [('RAM', False), ('Hard Drive', False), ('CPU', True), ('GPU', False)],
                'explanation': 'The CPU (Central Processing Unit) performs instructions and calculations.',
            },
            {
                'chapter': 'Web Technologies',
                'text': 'What does HTML stand for?',
                'choices': [
                    ('HyperText Markup Language', True),
                    ('HighText Machine Language', False),
                    ('HyperText Markdown Language', False),
                    ('HyperTransfer Markup Language', False)
                ],
                'explanation': 'HTML stands for HyperText Markup Language.',
            },
        ]

        created_questions = []
        for q_data in raw_questions:
            q_obj, created = Question.objects.get_or_create(
                school=school,
                question_text=q_data['text'],
                defaults={
                    'created_by': teacher_user,
                    'subject': 'Aptitude',
                    'department': 'Computer Science & Business Systems',
                    'chapter': q_data['chapter'],
                    'marks': 1,
                    'explanation': q_data['explanation'],
                }
            )

            for idx, (c_text, is_corr) in enumerate(q_data['choices'], start=1):
                Choice.objects.get_or_create(
                    question=q_obj,
                    choice_text=c_text,
                    defaults={
                        'is_correct': is_corr,
                        'order': idx,
                    }
                )
            created_questions.append(q_obj)

        return created_questions

    def seed_exams(self, school, teacher_user, questions, csbs_class):
        # Exam 1: Aptitude Mock Test 01 (10 questions)
        exam1_questions = questions[0:10]

        # Exam 2: Aptitude Practice Test 02 (5 questions)
        exam2_questions = questions[10:15]

        exams_config = [
            {
                'title': 'Aptitude Mock Test 01',
                'subject': 'Aptitude',
                'department': 'Computer Science & Business Systems',
                'chapter': 'General Aptitude',
                'exam_type': 'practice_test',
                'duration_minutes': 30,
                'pass_percentage': 40,
                'created_by': teacher_user,
                'questions': exam1_questions,
                'assigned_classes': [csbs_class],
            },
            {
                'title': 'Aptitude Practice Test 02',
                'subject': 'Aptitude',
                'department': 'Computer Science & Business Systems',
                'chapter': 'Quantitative & Verbal',
                'exam_type': 'test',
                'duration_minutes': 15,
                'pass_percentage': 40,
                'created_by': teacher_user,
                'questions': exam2_questions,
                'assigned_classes': [csbs_class],
            },
        ]

        created_exams = []
        for e_info in exams_config:
            exam, created = Exam.objects.get_or_create(
                school=school,
                title=e_info['title'],
                defaults={
                    'subject': e_info['subject'],
                    'department': e_info['department'],
                    'chapter': e_info['chapter'],
                    'exam_type': e_info['exam_type'],
                    'duration_minutes': e_info['duration_minutes'],
                    'pass_percentage': e_info['pass_percentage'],
                    'created_by': e_info['created_by'],
                    'description': f"Official test: {e_info['title']}",
                }
            )

            # Sync questions via ExamQuestion
            ExamQuestion.objects.filter(exam=exam).delete()
            for idx, q_obj in enumerate(e_info['questions'], start=1):
                ExamQuestion.objects.create(exam=exam, question=q_obj, order=idx)

            exam.update_total_marks()

            # Sync class assignment
            exam.assigned_classes.set(e_info['assigned_classes'])
            for sc in e_info['assigned_classes']:
                ExamAssignmentDate.objects.get_or_create(exam=exam, student_class=sc)

            created_exams.append(exam)

        return created_exams

    def seed_student2_attempt(self, student2, exam1, csbs_class):
        attempt, created = ExamAttempt.objects.get_or_create(
            student=student2,
            exam=exam1,
            student_class=csbs_class,
            attempt_mode='test',
            defaults={
                'total_marks': exam1.total_marks,
                'is_completed': True,
                'submitted_at': timezone.now(),
            }
        )

        if created or not attempt.answers.exists():
            attempt.is_completed = True
            attempt.submitted_at = timezone.now()
            attempt.question_order = [q.id for q in exam1.questions.all()]
            attempt.save()

            questions = list(exam1.questions.all().order_by('examquestion__order'))
            # Answer student2's questions (8 correct out of 10)
            for idx, question in enumerate(questions):
                choices = list(question.choices.all())
                correct_choice = next((c for c in choices if c.is_correct), choices[0])
                wrong_choice = next((c for c in choices if not c.is_correct), choices[0])
                selected = correct_choice if idx < 8 else wrong_choice

                StudentAnswer.objects.get_or_create(
                    attempt=attempt,
                    question=question,
                    defaults={'selected_choice': selected}
                )
            attempt.calculate_score()

        return attempt

    def print_summary(self, school, admin_user, teacher_user, students, csbs_class, exams, questions):
        self.stdout.write("Users:")
        self.stdout.write("  admin_test / Admin@12345 (Admin)")
        self.stdout.write("  teacher_test / Teacher@12345 (Faculty/Teacher)")
        for st in students:
            self.stdout.write(f"  {st.username} / Student@12345 (Student)")

        self.stdout.write("\nClass:")
        self.stdout.write(f"  {csbs_class.name} ({csbs_class.students.count()} students assigned)")

        self.stdout.write("\nTests:")
        for e in exams:
            self.stdout.write(f"  {e.title} ({e.questions.count()} questions, duration {e.duration_minutes} mins)")

        self.stdout.write(f"\nQuestions:")
        self.stdout.write(f"  {len(questions)} MCQ questions loaded into bank")
        self.stdout.write(f"  ({Choice.objects.count()} choices created)")
