from unittest import TestCase
import prep_repos

'''
Running from command line (for command line prompts working):

General:
    python -m unittest test_submissions.TestSubmissions.<test_name>

Example:
    python -m unittest test_submissions.TestSubmissions.test_create_student_json
'''

class TestSubmissions(TestCase):
    # student list files should consist of GT IDs, separated by newlines
    def get_students_list_from_file(self, filename='students.txt'):
        students = []
        try:
            with open(filename, 'r') as students_file:
                for line in students_file:
                    students.append(line.strip())
        except IOError:
            print '%s not found' % filename

        return students

    def generate_report_for_assignment(self, assignment, deadline, report_name, students=[], submissions=None):
        if submissions == None:
            submissions = prep_repos.Submissions()

        submissions.prep_repos("./submissions/%s" % assignment, deadline, students)
        submissions.generate_report(assignment, students, report_name)

        return submissions

    def test_create_student_json(self):
        submissions = prep_repos.Submissions()
        submissions.create_student_json("students_full.txt")

    def test_summer_A1_full(self):
        submissions = prep_repos.Submissions()
        submissions.create_student_json('students_full.txt')

        deadline = "2017-05-20 12:05:00"  # EST + 4 hours = UTC, which is the T-Square deadline
        assignment = "Assignment 1_ Team Matching Survey"
        report_name = "report_A1_full.txt"
        students = None  # all

        self.generate_report_for_assignment(assignment, deadline, report_name, students, submissions)

    def test_generate_A1_report(self):
        deadline = "2017-05-20 12:05:00"  # EST + 4 hours = UTC, which is the T-Square deadline
        assignment = "Assignment 1_ Team Matching Survey"
        report_name = "report_A1_full.txt"
        students = None  # all

        self.generate_report_for_assignment(assignment, deadline, report_name, students)

    def test_generate_A2_report(self):
        deadline = "2017-05-27 12:05:00"  # EST + 4 hours = UTC, which is the T-Square deadline
        assignment = "Assignment 2_ Git usage"
        report_name = "report_A2_full.txt"
        students = None  # all

        self.generate_report_for_assignment(assignment, deadline, report_name, students)

    def test_generate_A2_report_problematic(self):
        deadline = "2017-05-27 12:05:00"  # EST + 4 hours = UTC, which is the T-Square deadline
        assignment = "Assignment 2_ Git usage"
        report_name = "report_A2_full_test.txt"
        students = None # removed list of student names for public submission

        self.generate_report_for_assignment(assignment, deadline, report_name, students)

    def test_generate_A3_report(self):
        deadline = "2017-06-03 12:05:00"  # EST + 4 hours = UTC, which is the T-Square deadline
        assignment = "Assignment 3_ Basic Java coding & JUnit"
        report_name = "report_A3_full.txt"
        students = None  # all

        self.generate_report_for_assignment(assignment, deadline, report_name, students)

    def test_generate_A3_report_problematic(self):
        deadline = "2017-05-27 12:05:00"  # EST + 4 hours = UTC, which is the T-Square deadline
        assignment = "Assignment 3_ Basic Java coding & JUnit"
        report_name = "report_A3_test.txt"
        students = None # removed list of student names for public submission

        self.generate_report_for_assignment(assignment, deadline, report_name, students)

    def test_generate_A3_report_individual(self):
        deadline = "2017-05-27 12:05:00"  # EST + 4 hours = UTC, which is the T-Square deadline
        assignment = "Assignment 3_ Basic Java coding & JUnit"
        report_name = "report_A3_travis_students.txt"
        students = self.get_students_list_from_file('students_A3.txt')

        self.generate_report_for_assignment(assignment, deadline, report_name, students)