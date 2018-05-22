from unittest import TestCase

import os
import process_submissions

class TestSubmissions(TestCase):
    def setUp(self):
        # save filenames so we can use elsewhere
        self.setup_test_filenames()

        # TODO: set up github.gatech.edu/tjanssen3/6300ta_tools_test public projects with fake data in them
        temp_individual = process_submissions.Submissions(is_team=False, should_pull_repo_flag=False)
        temp_team = process_submissions.Submissions(is_team=True, should_pull_repo_flag=False)

        # set up temp filenames so tests don't conflict with production data
        self.submissions_individual = self.setup_test_filenames_on_object(temp_individual)
        self.submissions_team = self.setup_test_filenames_on_object(temp_team)

    def tearDown(self):
        should_delete_files = True

        if should_delete_files:
            self.delete_test_files()

    def setup_test_filenames(self):
        self.filenames = {}

        self.filenames["info_students"] = "test_students_full.txt"
        self.filenames["info_teams"] = "test_teams_full.txt"

        self.filenames["student_records"] = "test_student_records.json"
        self.filenames["student_aliases"] = "test_student_aliases.json"
        self.filenames["team_records"] = "test_team_records.json"
        self.filenames["team_members"] = "test_team_members.json"

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
            self.submissions_individual.create_student_json(bad_filename, should_create_json_files=True)

            self.fail("create_student_json somehow worked with bad filename %s" % bad_filename)
        except OSError:
            pass

    def test_create_student_json_creates_records_file(self):
        # remove files if they currently exist
        self.delete_test_files(student_records=True)

        self.submissions_individual.create_student_json(self.filenames["info_students"], should_create_json_files=True)

        try:
            with open(self.filenames["student_records"]) as records:
                pass # file exists: success
        except IOError:
            self.fail("create_student_json didn't create records file successfully")

    def test_create_student_json_creates_alias_file(self):
        # remove files if they currently exist
        self.delete_test_files(student_aliases=True)

        self.submissions_individual.create_student_json(self.filenames["info_students"], should_create_json_files=True)

        try:
            with open(self.filenames["student_aliases"]) as aliases:
                pass # file exists: success
        except IOError:
            self.fail("create_student_json didn't create alias file successfully")

    def test_create_team_json_creates_records_file(self):
        # remove files if they currently exist
        self.delete_test_files(team_records=True)

        self.submissions_individual.create_team_json(self.filenames["info_teams"], should_create_json_files=True)

        try:
            with open(self.filenames["team_records"]) as records:
                pass  # file exists: success
        except IOError:
            self.fail("create_team_json didn't create records file successfully")

    def test_create_team_json_creates_members_file(self):
        # remove files if they currently exist
        self.delete_test_files(team_members=True)

        self.submissions_individual.create_team_json(self.filenames["info_teams"], should_create_json_files=True)

        try:
            with open(self.filenames["team_members"]) as records:
                pass  # file exists: success
        except IOError:
            self.fail("create_team_json didn't create members file successfully")

    def test_create_team_json_missing_file(self):
        bad_filename = ""

        try:
            self.submissions_individual.create_team_json(bad_filename, should_create_json_files=True)

            self.fail("create_tean_json somehow worked with bad filename %s" % bad_filename)
        except OSError:
            pass