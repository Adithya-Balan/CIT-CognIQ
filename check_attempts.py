from myapp.models import Exam, ExamAttempt, User

# Check exam 25 (Unit 1 - test type)
exam = Exam.objects.get(id=25)
print(f'Exam: {exam.title} ({exam.exam_type})')

# Get students who have taken this exam
student_attempts = ExamAttempt.objects.filter(
    exam=exam,
    is_completed=True
).select_related('student', 'exam').order_by('student_id', '-submitted_at')

if not student_attempts.exists():
    print('No attempts found for this exam')
else:
    # Group by student
    from collections import defaultdict
    attempts_by_student = defaultdict(list)
    for attempt in student_attempts:
        attempts_by_student[attempt.student.username].append(attempt)
    
    for username, attempts in list(attempts_by_student.items())[:5]:  # Show first 5 students
        print(f'\n=== Student: {username} ===')
        
        test_attempts = [a for a in attempts if a.attempt_mode == 'test']
        practice_attempts = [a for a in attempts if a.attempt_mode == 'practice']
        
        print(f'  Total attempts: {len(attempts)}')
        print(f'  Test attempts: {len(test_attempts)}')
        print(f'  Practice attempts: {len(practice_attempts)}')
        
        if test_attempts:
            best_test = max(a.percentage for a in test_attempts)
            print(f'  Best test score: {best_test}%')
            print(f'  All test scores: {[a.percentage for a in test_attempts]}')
            if len(test_attempts) > 1:
                print(f'  WARNING: Multiple test attempts for a pure test exam!')
        
        if practice_attempts:
            print(f'  WARNING: Practice attempts exist for a pure test exam!')
            print(f'  Practice scores: {[a.percentage for a in practice_attempts]}')
