from datetime import datetime, timedelta
from unittest import TestCase

import datetime
import os
import process_submissions

class TestSubmissions(TestCase):
    def setUp(self):
        # save filenames so we can use elsewhere
        self.setup_test_filenames()

        # set up temp filenames so tests don't conflict with production data
        self.submissions_individual = self.setup_test_filenames_on_object(process_submissions.Submissions(is_team=False, should_pull_repo_flag=False))
        self.submissions_team = self.setup_test_filenames_on_object(process_submissions.Submissions(is_team=True, should_pull_repo_flag=False))

    def tearDown(self):
        should_delete_files = True

        if should_delete_files:
            self.delete_test_files()

    def setup_test_filenames(self):
        self.filenames = {}

        self.filenames["info_students"] = "testing/test_students_full.txt"
        self.filenames["info_teams"] = "testing/test_teams_full.txt"

        self.filenames["student_records"] = "testing/test_student_records.json"
        self.filenames["student_aliases"] = "testing/test_student_aliases.json"
        self.filenames["team_records"] = "testing/test_team_records.json"
        self.filenames["team_members"] = "testing/test_team_members.json"

    def setup_test_filenames_on_object(self, temp):
        temp.STUDENT_RECORDS_FILENAME = self.filenames["student_records"]
        temp.STUDENT_ALIAS_FILENAME = self.filenames["student_aliases"]
        temp.TEAM_RECORDS_FILENAME = self.filenames["team_records"]
        temp.TEAM_MEMBERS_FILENAME = self.filenames["team_members"]

        return temp

    def delete_test_files(self, all=True, student_records=False, student_aliases=False, team_records=False, team_members=False):
        if student_records or student_aliases or team_records or team_members:
            all = False  # selective delete only

        if student_records or all:
            try:
                with open(self.filenames["student_records"]) as student_records_file:
                    os.remove(self.filenames["student_records"])
            except IOError:
                pass

        if student_aliases or all:
            try:
                with open(self.filenames["student_aliases"]) as student_aliases_file:
                    os.remove(self.filenames["student_aliases"])
            except IOError:
                pass

        if team_records or all:
            try:
                with open(self.filenames["team_records"]) as team_records_file:
                    os.remove(self.filenames["team_records"])
            except IOError:
                pass

        if team_members or all:
            try:
                with open(self.filenames["team_members"]) as team_members_file:
                    os.remove(self.filenames["team_members"])
            except IOError:
                pass

    def test_create_student_json_missing_file(self):
        bad_filename = ""

        try:
            self.submissions_individual.create_student_json(bad_filename)

            self.fail("create_student_json somehow worked with bad filename %s" % bad_filename)
        except OSError:
            pass

    def test_create_student_json_creates_records_file(self):
        # remove files if they currently exist
        self.delete_test_files(student_records=True)

        self.submissions_individual.create_student_json(self.filenames["info_students"])

        try:
            with open(self.filenames["student_records"]) as records:
                pass # file exists: success
        except IOError:
            self.fail("create_student_json didn't create records file successfully")

    def test_create_student_json_creates_alias_file(self):
        # remove files if they currently exist
        self.delete_test_files(student_aliases=True)

        self.submissions_individual.create_student_json(self.filenames["info_students"])

        try:
            with open(self.filenames["student_aliases"]) as aliases:
                pass # file exists: success
        except IOError:
            self.fail("create_student_json didn't create alias file successfully")

    def test_create_team_json_creates_records_file(self):
        # remove files if they currently exist
        self.delete_test_files(team_records=True)

        self.submissions_individual.create_team_json(self.filenames["info_teams"])

        try:
            with open(self.filenames["team_records"]) as records:
                pass  # file exists: success
        except IOError:
            self.fail("create_team_json didn't create records file successfully")

    def test_create_team_json_creates_members_file(self):
        # remove files if they currently exist
        self.delete_test_files(team_members=True)

        self.submissions_individual.create_team_json(self.filenames["info_teams"])

        try:
            with open(self.filenames["team_members"]) as records:
                pass  # file exists: success
        except IOError:
            self.fail("create_team_json didn't create members file successfully")

    def test_create_team_json_missing_file(self):
        bad_filename = ""

        try:
            self.submissions_individual.create_team_json(bad_filename)

            self.fail("create_tean_json somehow worked with bad filename %s" % bad_filename)
        except OSError:
            pass

class TestTimestamp(TestCase):
    def setUp(self):
        # made a public repo with dummy info here: https://github.com/tjanssen3/6300afakestudent
        git_domain = "github.com"
        git_context = "tjanssen3"
        folder_prefix = "6300"
        test_student = "afakestudent"

        TestSubmissions.setup_test_filenames(self)
        self.submissions = TestSubmissions.setup_test_filenames_on_object(self, process_submissions.Submissions(is_team=False, should_pull_repo_flag=True,
                                                                                                                folder_prefix=folder_prefix, git_context=git_context, git_domain=git_domain))
        self.submissions.create_student_json(self.filenames["info_students"])

        # current assignment
        self.info = {}
        self.info["current_assignment"] = {'Timestamp Submission': 'Ok',
                                           'commitID valid': True,
                                           'commitID': 'f556b4ba7e222de302b367b1dceeff89bd233191'}
        self.info["gt_username"] = 'afakestudent'
        self.info["deadline"] = '2018-02-24 12:00:00'

        assignment_name = "A3"
        student_whitelist = [test_student]

        # see if testing info exists already; if not, pull from public repo
        should_pull = not os.path.isdir("./student_repo/%s%s" % (folder_prefix, test_student))

        self.submissions.process_repos(
            submission_folder_name=('./testing/%s' % assignment_name),
            deadline=self.info["deadline"],
            assignment_code=assignment_name,
            student_whitelist=student_whitelist,
            should_pull=should_pull)

        self.info['deadline'] = self.submissions._get_output_timestamp(test_student, self.info['current_assignment'])


    def tearDown(self):
        pass

    def test_GitHub_on_time(self):
        # case: student committed exactly at deadline
        self.submissions._compare_timestamp_github(self.info["current_assignment"], self.info["gt_username"], self.info["deadline"])

        self.assertEqual(self.info["current_assignment"]['Submission GitHub'], self.submissions.STR_OK, "Timestamp Github should be on time!")

    def test_GitHub_late(self):
        # case: student committed an hour late
        deadline = (datetime.datetime.strptime(self.info["deadline"], self.submissions.DATETIME_PATTERN) - timedelta(hours=1)).strftime(self.submissions.DATETIME_PATTERN)
        self.submissions._compare_timestamp_github(self.info["current_assignment"], self.info["gt_username"], deadline)

        self.assertEqual(self.info["current_assignment"]["Submission GitHub"], self.submissions.STR_LATE, "Timestamp GitHub should be late!")
