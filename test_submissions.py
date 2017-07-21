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

    def generate_report_for_assignment(self, assignment, deadline, report_name, students=[], submissions=None, pull_from_github=True, is_team_project=False):
        if submissions == None:
            submissions = prep_repos.Submissions()

        submissions.pull_from_github = pull_from_github
        submissions.prep_repos("./submissions/%s" % assignment, deadline, students, is_team_project=is_team_project)
        submissions.generate_report(assignment, students, report_name, is_team_project=is_team_project)

        return submissions

    def test_create_student_json(self):
        submissions = prep_repos.Submissions()
        submissions.create_student_json("students_full.txt")

    def test_create_teams_json(self):
        submissions = prep_repos.Submissions()
        submissions.create_team_json("student_teams.txt")

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
        deadline = "2017-06-03 12:05:00"  # EST + 4 hours = UTC, which is the T-Square deadline
        assignment = "Assignment 3_ Basic Java coding & JUnit"
        report_name = "report_A3_test.txt"
        students = None # removed list of student names for public submission

        self.generate_report_for_assignment(assignment, deadline, report_name, students)

    def test_generate_A3_report_individual(self):
        deadline = "2017-06-03 12:05:00"  # EST + 4 hours = UTC, which is the T-Square deadline
        assignment = "Assignment 3_ Basic Java coding & JUnit"
        report_name = "report_A3_travis_students.txt"
        students = self.get_students_list_from_file('students_A3.txt')

        self.generate_report_for_assignment(assignment, deadline, report_name, students)

    def test_generate_A6_report_individual(self):
        deadline = "2017-07-02 12:05:00"  # EST + 4 hours = UTC, which is the T-Square deadline
        assignment = "Assignment 6_ Category-Partition"
        report_name = "report_A6_travis_students.txt"
        students = self.get_students_list_from_file('students_A6.txt')

        self.generate_report_for_assignment(assignment, deadline, report_name, students)

    def test_generate_A6_report_individual_test(self):
        deadline = "2017-07-02 12:05:00"  # EST + 4 hours = UTC, which is the T-Square deadline
        assignment = "Assignment 6_ Category-Partition"
        report_name = "report_A6_travis_students_test.txt"
        students = self.get_students_list_from_file('students_A6.txt')

        self.generate_report_for_assignment(assignment, deadline, report_name, students, pull_from_github=False)

    def test_generate_A7_individual(self):
        deadline = "2017-07-09 12:05:00"  # EST + 4 hours = UTC, which is the T-Square deadline
        assignment = "Assignment 7_ White-Box Testing"
        report_name = "report_A7_travis_students_updated.txt"
        students = self.get_students_list_from_file('students_A7.txt')

        self.generate_report_for_assignment(assignment, deadline, report_name, students)

    def test_generate_A7_report_individual(self):
        submissions = prep_repos.Submissions()
        assignment = "Assignment 7_ White-Box Testing"
        report_name = "report_A7_travis_students.txt"
        students = self.get_students_list_from_file('students_A7.txt')

        submissions.generate_report(assignment, students, report_name)

    def test_generate_A7_individual_test(self):
        deadline = "2017-07-09 12:05:00"  # EST + 4 hours = UTC, which is the T-Square deadline
        assignment = "Assignment 7_ White-Box Testing"
        report_name = "report_A7_travis_students_test.txt"
        students = self.get_students_list_from_file('students_A7.txt')

        self.generate_report_for_assignment(assignment, deadline, report_name, students, pull_from_github=False)

    def test_generate_D0_report(self):
        deadline = "2017-06-17 12:05:00"  # EST + 4 hours = UTC, which is the T-Square deadline
        assignment = "Group Project, Deliverable 0"
        report_name = "report_group_D0_travis_students.txt"
        students = self.get_students_list_from_file('students_group_project_teams.txt')

        self.generate_report_for_assignment(assignment, deadline, report_name, students, is_team_project=True, pull_from_github=False)

    def test_generate_D0_test(self):
        deadline = "2017-06-17 12:05:00"  # EST + 4 hours = UTC, which is the T-Square deadline
        assignment = "Group Project, Deliverable 0"
        report_name = "report_group_D0_travis_students_test.txt"
        students = self.get_students_list_from_file('students_group_project_teams.txt')

        self.generate_report_for_assignment(assignment, deadline, report_name, students, is_team_project=True, pull_from_github=False)