##!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=too-many-instance-attributes
r"""
For the purposes of this file, we assume that a student is either a student
or a team to make parsing easier, since most of the logic is identical.

See download_submission.process_assignment to see how to utilize this class
correctly.

TODO: Many of the methods of process_repos should be combined?
"""


__all__ = ["Submissions", ] # Controls what can be imported
__author__ = "David Tran, Travis Janssen"
__credits__ = ["David Tran", "Travis Janssen"]
__status__ = "Production"
__version__ = "1.0.0"


from datetime import datetime, timedelta
import inspect
import json
import itertools
import os
import platform
import re
import subprocess

import logging
logger = logging.getLogger(__name__)


class Submissions(object):
    r"""
    The purpose of this class is to download and process students' submissions.

    This will not grade the submission, rather we automate the process of
    acquiring the student's repos.

    """


    def __init__(self, is_team, should_pull_repo_flag):
        r"""
        Defines the variables for the current class.

        We could define static variables but they are not private and
        are publicly accessible in Python.

        Arguments:
          self.is_team:   (boolean) Sets if this submission is a team project
            or not.

          should_pull_repo_flag:   (boolean) Sets if we should git pull,
            if needed.

        """


        self.FOLDER_PREFIX = '6300Fall17'
        self.GIT_CONTEXT = 'gt-omscs-se-2017fall'

        self.student_records_filename = 'student_records.json'
        self.student_alias_filename = 'student_aliases.json'
        self.team_records_filename = 'student_records_teams.json'
        self.team_members_filename = 'student_records_team_members.json'
        self.timestamp_filename = 'timestamp.txt'

        self.datetime_format = '%Y-%m-%dT%H:%M:%S'
        self.t_square_datetime_format = '%Y%m%d%H%M%S'

        self.is_team = is_team
        self.should_pull_repo_flag = should_pull_repo_flag

        self.MAIN_REPO_DIR = 'student_repo'

        # Stored to be used in later logic, so typos between copies don't exist
        self.STR_INVALID = "Invalid"
        self.STR_LATE = "Late"
        self.STR_MISSING = "Missing"
        self.STR_NA = "N/A"
        self.STR_OK = "Ok"
        self.BAD_STR_LIST = [self.STR_INVALID, self.STR_MISSING]

        # Cache results
        self.cached_file_dicts = {}  # Cache dictionary pulls
        self.cached_teams_pulled = set() # Cache pulled teams

        self.OS_TYPE = platform.system()


    def process_repos(self, submission_folder_name,
                      deadline, student_whitelist=None):
        """
        This is the core function that will automate the download of
        student submissions.

        There is a sister function called _process_team_repos that focuses
        on teams that is executed after this code. The logic contained
        here mostly applies to both set of submissions.

        Arguments:
          submission_folder_name:   (str) This is the directory for all
            submissions that we will download. This must exist and will throw
            an IOError if it does not exist.

          deadline:   (str) This is the deadline of the assignment if it is
            late. The input must be in strict ISO 8601 format
            'YYYY-MM-DDTHH:MM:SS'. As python 2 does NOT natively support
            different timezones, this must be in UTC timezone to be correctly
            comparable.

          student_whitelist:   (list of str) This is the list of student
            username IDs that we will whitelist. That is to say all students
            in the list will not be ignored. If set to None or empty list,
            we will grab all students.

        """


        assignment_alias = submission_folder_name.split('/')[-1]

        if student_whitelist is None:
            student_whitelist = []

        if not os.path.isdir(self.MAIN_REPO_DIR):
            os.makedirs(self.MAIN_REPO_DIR)

        if not os.path.isdir(submission_folder_name):
            raise IOError(
              "%s: Submission folder name '%s' not found. Exiting." % (
                inspect.currentframe().f_code.co_name, submission_folder_name))

        if self.is_team:
            team_records = self._get_file_dict(
              filename=self.team_records_filename,
              caller_name=inspect.currentframe().f_code.co_name)

        student_records = self._get_file_dict(
          filename=self.student_records_filename,
          caller_name=inspect.currentframe().f_code.co_name,
          epilog="Run create_student_json first.")


        directory_listing = self._get_student_folders(
          submission_folder_name=submission_folder_name,
          student_whitelist=student_whitelist)

        for folder in directory_listing:

            t_square_id = folder.split('(')[1].strip(')')

            current_student = student_records.get(t_square_id, {})

            if not current_student:
                continue

            gt_student_id = current_student['gt_id']

            if ((not self.is_team and
                 gt_student_id not in student_whitelist) or
                  (self.is_team and
                   team_records[gt_student_id] not in student_whitelist)
               ):

                continue

            # Checking repeated results on calls to simplify them
            base_directory = os.path.join(submission_folder_name, folder)
            current_assignment = current_student[assignment_alias] = {}
            current_submission_file = (
              '%s(%s)_submissionText.html' % (
                current_student['name'], t_square_id))

            # TODO: These methods below should be combined together?

            # Update submission text
            self._check_submission_file(
              current_assignment=current_assignment,
              base_directory=base_directory,
              submission_file=current_submission_file)

            # Update t-square timestamp
            self._set_timestamp_t_square(
              current_assignment=current_assignment,
              base_directory=base_directory)

            # Clone repo if needed
            # NOTE: You'll need to authenticate with Github here and
            # debuggers may not work properly
            self._setup_student_repo(gt_student_id=gt_student_id)

            # Only check commit ID validity with GitHub timestamp
            if self._is_commit_present(
              commit_status=current_assignment['commitID']):

                # Try to check out commit ID
                self._check_commitID(
                  current_assignment=current_assignment,
                  gt_student_id=gt_student_id)

                self._compare_timestamp_github(
                  current_assignment=current_assignment,
                  gt_student_id=gt_student_id, deadline=deadline)

            # Check T-Square timestamp against deadline
            self._compare_timestamp_t_square(
              current_assignment=current_assignment,
              deadline=deadline)

            # Save Result
            student_records[t_square_id] = current_student


        if student_records is not None:

            # Save info
            with open(self.student_records_filename, 'w') as output_file:
                json.dump(student_records, output_file)

        if self.is_team and student_whitelist:
            self._process_team_repos(
              assignment_alias=assignment_alias,
              student_whitelist=student_whitelist)


    def _process_team_repos(self, assignment_alias, student_whitelist):
        """
        This is the extension process_repos that focuses only on teams.
        As such this should only be called on team repos.

        Arguments:
          assignment_alias:   (str) This is the name of the assignment, i.e.
            the submission name.

          student_whitelist:   (list of str) This is the list of student
            username IDs that we will whitelist. That is to say all students
            in the list will not be ignored. If set to None or empty list,
            we will grab all students.

        """


        student_aliases = self._get_file_dict(
          filename=self.student_alias_filename,
          caller_name=inspect.currentframe().f_code.co_name)

        student_records = self._get_file_dict(
          filename=self.student_records_filename,
          caller_name=inspect.currentframe().f_code.co_name,
          epilog="Run create_student_json first.")

        team_records = self._get_file_dict(
          filename=self.team_members_filename,
          caller_name=inspect.currentframe().f_code.co_name)


        for team in student_whitelist:

            member_list, commit_list = team_records[team], []

            for student in member_list:

                t_square_id = student_aliases[student]
                team_assignment = (
                  student_records[t_square_id][assignment_alias])

                try:
                    commit_time = team_assignment['Timestamp GitHub']
                    commitID = team_assignment['commitID']

                except KeyError:
                    continue

                if (self._is_commit_present(commit_status=commitID) and
                      commit_time != self.STR_NA):

                    commit_list.append((commit_time, commitID))


            # checkout most recent commit here
            if len(commit_list) > 0:

                # Most recent should be first
                commit_list.sort(reverse=True)
                _, most_recent_commit = commit_list[0]

                command = (
                  'cd %s; git checkout %s;' % (
                    self._gen_prefixed_dir(team), most_recent_commit))

                _ = self._execute_command(command=command)

            else:
                print("%s: No valid commeit for team '%s'!" % (
                  inspect.currentframe().f_code.co_name, team))


    def _setup_student_repo(self, gt_student_id):
        r"""
        Checks if the student Git repo is downloaded and cleans it up for the
        grader.

        Assignment:
          gt_student_id:   (str) The student ID we will use download the repo.

        """


        just_cloned_repo = None
        repo_suffix = self._get_correct_reference_id(graded_id=gt_student_id)

        if not os.path.isdir(self._gen_prefixed_dir(prefix_str=repo_suffix)):

            command = ('cd %s; '
                       'git clone https://github.gatech.edu/%s/%s%s.git; '
                       'cd ..') % (
                         self.MAIN_REPO_DIR, self.GIT_CONTEXT,
                         self.FOLDER_PREFIX, repo_suffix)
            _ = self._execute_command(command=command)

            self.cached_teams_pulled.add(repo_suffix)
            just_cloned_repo = True

        else:

            just_cloned_repo = False


        # Revert any local changes and pull from remote
        try:

            pull_flag = ''

            if self._should_pull_repo(repo_suffix) or just_cloned_repo:

                pull_flag = 'git pull &&'

            command = (
              'cd %s && git clean -fd && %s git reset --hard HEAD' % (
                self._gen_prefixed_dir(prefix_str=repo_suffix), pull_flag))

            _ = self._execute_command(command=command)


        # TODO: Unneeded?
        except subprocess.CalledProcessError as error:

            try:
                print("%s: student '%s' subprocess.CalledProcessError: %s\n",
                      inspect.currentframe().f_code.co_name,
                      gt_student_id, str(error.output))

            except UnicodeDecodeError:
                print("%s: student '%s' subprocess.CalledProcessError: "
                      "UnicodeDecodeError\n",
                      inspect.currentframe().f_code.co_name, gt_student_id)


    def generate_report(self, assignment, student_list=None,
                        report_filename=None):
        r"""
        This generates the final report that can be used by a grader.

        The result is outputted to a file (report_filename) and to stdout.

        Arguments:
          assignment:   (str) This is the name of the assignment we are
            comparing against.

          student_list:   (list of str) This is a list of students that we
            will analyze and prints the results.

          report_filename:   (str) This is the filename of the report will
            generate, in addition to stdout. To disable this feature, pass in
            None.

        Returns:
        A file, if set, with the results and the output to stdout.
        """


        student_aliases = self._get_file_dict(
          filename=self.student_alias_filename,
          caller_name=inspect.currentframe().f_code.co_name)

        student_records = self._get_file_dict(
          filename=self.student_records_filename,
          caller_name=inspect.currentframe().f_code.co_name,
          epilog="Run create_student_json first.")


        bad_commit, late_github, late_t_square, missing = [], [], [], []

        _init_log(log_filename=report_filename)
        logger.info("Report: %s\n", assignment)

        if self.is_team:

            team_records = self._get_file_dict(
              filename=self.team_members_filename,
              caller_name=inspect.currentframe().f_code.co_name)

            new_student_list = []

            for team in student_list:

                members_list = team_records[team]

                new_student_list.append(team)
                new_student_list.extend(members_list)

            student_list = new_student_list

        elif not student_list:

            student_list = student_aliases.keys() # Get all students

        #else:
          # We are passed a fixed set of students and this is not a team.

        # Parse the student list for bad elements
        stripped_list = map(str.strip, map(str, student_list))
        final_list = list(filter(bool, stripped_list))

        # This is a filter to get bad students in different spots
        bad_student_dict = {
          'Submission GitHub': ('late', late_github),
          'Submission T-Square': ('late', late_t_square),
          'commitID': (self.STR_MISSING, missing),
          'commitID valid': (False, bad_commit)
        }


        for student in final_list:

            if self.is_team and 'Team' in student:
                logger.info("\n========== %s ==========", student)
                continue
            else:
                logger.info(student)

            student_info = student_records[student_aliases[student]]

            if assignment not in student_info:

                logger.info('\tNo records found')
                missing.append(student)
                continue

            student_info_assignment = student_info[assignment]

            for key in sorted(student_info_assignment.keys(), reverse=True):

                student_info_assignment_value = student_info_assignment[key]
                logger.info('\t%s: %s', key, student_info_assignment_value)

                try:
                    target_value, target_list = bad_student_dict[key]
                    if target_value == student_info_assignment_value:
                        target_list.append(student)

                except KeyError:
                    pass


        logger.info("\n========== RESULTS ==========")
        str_buffer = ["\nLATE SUBMISSIONS:"]
        for fmt_str, data in [("\tT-Square (%d): %s", late_t_square),
                              ("\tGitHub (%d): %s", late_github),
                              ("\nMISSING SUBMISSIONS (%s): %s", missing),
                              ("\nBAD COMMITS (%s):\n\t%s", bad_commit)]:

            str_buffer.append(fmt_str % (len(data), ", ".join(data)))

        logger.info("\n".join(str_buffer))


    def _execute_command(self, command):
        r"""
        Parses the command, if it is executed on Windows and returns the output.

        Arguments:
          command:   (str) The command we will execute and return the result.

        Return:
        The command's output.
        """


        if self.OS_TYPE == 'Windows':

            # Windows chains commands with &, *nix with ;
            command = command.replace(';', '&')

            # Windows doesn't support 'go back to last directory'
            command = command[:command.index('& cd -')]

        return subprocess.check_output(command, shell=True).strip()


    def create_student_json(self, input_filename):
        r"""
        Converts the input file to two useful JSON files specifically
        for student grading.

        Arguments:
          input_filename:   (str) The input filename we will parse into JSON
            files.

        """


        try:

            with open(input_filename, 'r') as input_file:

                gt_id_dict, student_records = {}, {}

                for line in input_file:

                    parsed_line = line.strip().split('\t')

                    name, gt_id, t_square_id = parsed_line[0:3]

                    student_records[t_square_id] = {
                      'name': name, 'gt_id': gt_id}
                    gt_id_dict[gt_id] = t_square_id

        except IOError:
            raise IOError(
              "%s: Missing file '%s'. Exiting." % (
                inspect.currentframe().f_code.co_name, input_filename))


        with open(self.student_records_filename, 'w') as output_file:
            json.dump(student_records, output_file)
        with open(self.student_alias_filename, 'w') as alias_file:
            json.dump(gt_id_dict, alias_file)


    def _get_correct_reference_id(self, graded_id):
        r"""
        Depending on which submission type, converts it to the correct ID
        instance so we can access the appropriate repo.

        For non-team projects, the ID is the correct student ID.
        For team projects, we convert said student into the correct team ID>

        Arguments:
          graded_id:   (str) The ID we will convert depending on the mode.

        Return:
        The corrected ID.
        """


        if self.is_team:

            team_records = self._get_file_dict(
              filename=self.team_records_filename,
              caller_name=inspect.currentframe().f_code.co_name)

            try:
                team_id = team_records[graded_id]

            except IndexError:
                raise IndexError(
                  "%s: Couldn't find team for student with GTID '%s'. Exiting."
                  % (inspect.currentframe().f_code.co_name, graded_id))

            return team_id

        else:

            # This is the student ID
            return graded_id


    def _get_file_dict(self, filename, caller_name='', epilog=''):
        r"""
        Attempts to access the file and retrieve the JSON within it.

        Arguments:
          filename:   (str) The name of the file we will open.

          caller_name:   (str) This is the caller's function name when
            printing errors.

          epilog:   (str) This is the epilogue error message if one is needed.

        NOTE:
          For Python, JSON and the native Python dictionary are one and the
          same as they have matching calls and very similar syntax.

        Returns:
        The associated JSON (Python Dict) at the file or an IOError.
        """


        file_dict = self.cached_file_dicts.get(filename, None)

        if file_dict is None:

            try:
                with open(filename, 'r') as my_file:
                    file_dict = self.cached_file_dicts[filename] = json.load(my_file)

            except IOError:
                raise IOError(
                  "%s: Missing file '%s'%s Exiting." % (
                    caller_name, filename, epilog))

        return file_dict


    def _get_student_folders(self, submission_folder_name, student_whitelist):
        r"""
        Get a list of student repos that we will grade.

        If student_whitelist is not set, we will grab all student repos.

        Arguments:
          submission_folder_name:   (str) This is the directory for all
            submissions that we will download. This must exist and will throw
            an IOError if it does not exist.

          student_whitelist:   (list of str) This is the list of student
            username IDs that we will whitelist. That is to say all students
            in the list will not be ignored. If set to None or empty list,
            we will grab all students.

        Return:
        A list of all student submissions we will process.
        """


        if not student_whitelist:
            return list(filter(
              os.path.isdir, os.listdir(submission_folder_name)))


        if self.is_team:

            team_records = self._get_file_dict(
              filename=self.team_members_filename,
              caller_name=inspect.currentframe().f_code.co_name)

            # Read data in student_whitelist
            student_whitelist_multi_list = [
              team_records[team] for team in student_whitelist]
            # Flatten multi list to be a single list and store it back
            student_whitelist = list(
              itertools.chain.from_iterable(student_whitelist_multi_list))

            # student_whitelist now contains student GTIDs instead of team names

        student_aliases = self._get_file_dict(
          filename=self.student_alias_filename,
          caller_name=inspect.currentframe().f_code.co_name)

        student_records = self._get_file_dict(
          filename=self.student_records_filename,
          caller_name=inspect.currentframe().f_code.co_name,
          epilog="Run create_student_json first.")

        folders = []


        for student in student_whitelist:

            try:
                t_square_id = student_aliases[student]
                name = student_records[t_square_id]['name']

            except IndexError:
                logger.error(
                  "Couldn't get folder name for student with GTID %s\n",
                  student)

            folders.append('%s(%s)' % (name, t_square_id))

        return folders


    def _gen_prefixed_dir(self, prefix_str):
        r"""
        Combines a directory prefix into the valid directory, to target a
        student's directory.

        Arguments:
          prefix_str:   (str) A valid student's prefix (be it a team number
            or a student name) so we can access it.

        Returns:
        A valid directory that can be accessed.
        """


        return os.path.join(self.MAIN_REPO_DIR, "%s%s" %
                            (self.FOLDER_PREFIX, prefix_str))


    def _check_commitID(self, current_assignment, gt_student_id):
        r"""
        Checks if the current commit is a valid comment in the Repo.

        Some students may submit commits that are invalid.

        The result is stored in current_assignment.

        Arguments:
          current_assignment:   (dict) This is the current assignment we are
          checking the commit of.

          gt_student_id:   (str) This is a student's ID what we will grab
          the info of.

        """


        repo_suffix = self._get_correct_reference_id(graded_id=gt_student_id)

        command = (
          'cd %s; git checkout %s; '
          'git show --pretty=format:\'%%H\' --no-patch; cd - &> /dev/null' % (
            self._gen_prefixed_dir(prefix_str=repo_suffix),
            current_assignment['commitID']))

        output_checkout = self._execute_command(command=command)

        if self.OS_TYPE == 'Windows':
            # Windows returns \\ prefix and suffix so strip it
            commit = output_checkout[1:-1]
        else:
            commit = output_checkout

        valid_commit = commit == current_assignment['commitID']
        current_assignment['commitID valid'] = valid_commit


    def _check_submission_file(self, current_assignment,
                               base_directory, submission_file):
        r"""
        This checks the submission file and see there is a valid commit.

        Arguments:
          current_assignment:   (dict) This is the current assignment we are
            checking the submission of.

          base_directory:   (str) This is the base directory we will read the
            file from.

          submission_file:   (str) This is the submission file we are reading
            from.

        NOTE:
          We not check if the commit exists in the repo or is valid, only if
          there is one. This is left to a different method.
        """


        try:

            with open(os.path.join(base_directory, submission_file), 'r') as submission_info:

                strings = re.findall(r'([0-9A-Za-z]{40})',
                                     submission_info.read())

                commitID = strings[0] if len(strings) else self.STR_INVALID
                current_assignment['commitID'] = commitID

        except IOError:

            current_assignment['commitID'] = self.STR_MISSING


    def _set_timestamp_t_square(self, current_assignment, base_directory):
        r"""
        This gets the timestamp and sets it in the current assignment.

        The result is stored in current_assignment.

        Arguments:
          current_assignment:   (dict) This is the current assignment we are
            checking the timestamp of.

          base_directory:   (str) This is the base directory we will read the
            file from.

        """


        try:

            target_filename = os.path.join(base_directory,
                                           self.timestamp_filename)

            with open(target_filename, 'r') as timestamp_info:

                timestamp = self._fix_timestamp_t_square(
                  time_str=timestamp_info.read())
                current_assignment['Timestamp T-Square'] = timestamp

        except IOError:

            current_assignment['Timestamp T-Square'] = self.STR_MISSING
            current_assignment['commitID'] = self.STR_MISSING


    def _compare_timestamp_github(self, current_assignment,
                                  gt_student_id, deadline):
        r"""
        This parses the timestamp on Github and compares it to see if the commit
        is late.

        The result is stored in current_assignment.

        Arguments:
          current_assignment:   (dict) This is the current assignment we are
            checking the timestamp of.

          gt_student_id:   (str) The student ID we will use to get the
            timestamp.

          deadline:   (str) This is the deadline of the assignment if it is
            late. The input must be in strict ISO 8601 format
            'YYYY-MM-DDTHH:MM:SS'. As python 2 does NOT natively support
            different timezones, this must be in UTC timezone to be correctly
            comparable.

        """


        if not current_assignment['commitID valid']:

            current_assignment['Submission GitHub'] = self.STR_NA
            current_assignment['Timestamp GitHub'] = self.STR_NA

        else:

            repo_suffix = self._get_correct_reference_id(
              graded_id=gt_student_id)

            # check timestamp of GitHub commit
            command = (
              'cd %s; git show -s --format=%%cI %s; cd - &> /dev/null' % (
                self._gen_prefixed_dir(prefix_str=repo_suffix),
                current_assignment['commitID']))

            output_timestamp = self._execute_command(command=command)

            dt_object = self._read_strict_ISO_format(time_str=output_timestamp)
            timestamp_github = dt_object.strftime(self.datetime_format)

            # check GitHub timestamp against deadline
            current_assignment['Timestamp GitHub'] = timestamp_github
            msg = self.STR_OK if timestamp_github < deadline else self.STR_LATE
            current_assignment['Submission GitHub'] = msg


    def _compare_timestamp_t_square(self, current_assignment, deadline):
        """
        Compares the T-Square timestamp to see if the commit is late.

        The result is stored in current_assignment.

        Arguments:
          current_assignment:   (dict) This is the current assignment we are
            checking the timestamp of.

          gt_student_id:   (str) The student ID we will use to get the
            timestamp.

          deadline:   (str) This is the deadline of the assignment if it is
            late. The input must be in strict ISO 8601 format
            'YYYY-MM-DDTHH:MM:SS'. As python 2 does NOT natively support
            different timezones, this must be in UTC timezone to be correctly
            comparable.

        """


        if current_assignment['Timestamp T-Square'] != self.STR_MISSING:
            final_time = current_assignment['Timestamp T-Square']

            msg = self.STR_OK if final_time <= deadline else self.STR_LATE
            current_assignment['Submission T-Square'] = msg


    def _fix_timestamp_t_square(self, time_str):
        r"""
        This function guarantees that converting t_square time is done exactly
        one so multiple calls won't accidentally convert it twice.

        Arguments:
          time_str:   (str) The input string that may or may not be correct.

        Returns:
        The date formatted in strict ISO 8601 format as a string.

        NOTE:
          T-square time is one long "int" formatted as:
            > 20171006031150569
              YYYYMMDDHHMMSSSSS
          We want to convert to strict ISO 8601 for easier comparision.
            > 2017-10-06T03:11:50 569
              YYYY-MM-DDTHH:MM:SS ---

        """


        new_time_str = None

        try:
            _ = int(time_str)

        except ValueError:
            new_time_str = time_str

        else:
            new_time_str = (
              datetime.strptime(time_str[:14],
                                self.t_square_datetime_format).isoformat())

        return new_time_str


    def _is_commit_present(self, commit_status):
        r"""
        Checks if the commit statue message states it is present.

        Arguments:
          commit_status:   (str) The current commit status.

        Returns:
        True if it's not a bad commit or False if it is.
        """


        return commit_status not in self.BAD_STR_LIST


    def _read_strict_ISO_format(self, time_str):
        r"""
        Reads in a strict ISO 8601 format date with the timezone and returns
        back the assocated time object.

        This matches GIT's "%cI" date format.

        Arguments:
        time_str:   (str) The ISO 8601 strict date format as a string.

        Returns:
        A correct datetime object with the date
        """


        time_obj = datetime.strptime(time_str[:19], self.datetime_format)
        positive_sign = hour = minute = 0

        try:
            positive_sign = 0 if time_str[20] == '-' else 1
            hour, minute = map(int, time_str[21:].split(':'))

        except IndexError:
            pass

        if positive_sign:
            return time_obj + timedelta(hours=hour, minutes=minute)
        else:
            return time_obj - timedelta(hours=hour, minutes=minute)


    def _should_pull_repo(self, team_number):
        r"""
        Checks if we should pull a repo or assume it has been pulled already.

        This is only applicable for team projects as multiple students work
        on the same repo.

        Arguments:
          team_number:   (str or any key) This is the team number we will
          check to see if we pull a repo. For non-teams, we should always pull.

        Return:
        A boolean saying if the repo should be pulled.
        """


        if not self.should_pull_repo_flag:
            return False

        should_pull = True

        if self.is_team:

            if team_number in self.cached_teams_pulled:
                should_pull = False

            self.cached_teams_pulled.add(team_number)

        return should_pull


def _init_log(log_filename=None, log_file_mode='w', fmt_str=None):
    r"""
    Initializes the logging for this module.

    This should not be in a class as this is unique per file (module) nor
    should be this imported.

    This could be integrated by moving all logging commands but then all
    log names need to be unique to prevent clobbering. The default action is
    to append but set to overwrite since it is unlikely we need the previous
    run info. Assume we have unique names, we will generate a lot of log
    files which is also undesirable.

    Arguments:
      log_filename:   (str) This is the log filename we are outputting to.
        None will disable this and empty string will use the default name,
        "submission_runner.txt".

      log_file_mode:   (str) This sets the file bit for the output file.

        'w':  Overwrite (aka clobber the file)

        'a':  Append (aka add to the end of the file)

        Other commands may exist as this is similar to the second argument
          in open.

      fmt_str:   (str) This is the format string used for the logger,
        default if set to None or empty string is just the message.

        Be mindful that this shows up in very message printed.
        An example is included to showcase what can be done.

    WARNING:
      If this is called multiple times, stdout will get multiple copies of any
      logger call, which will create repeating lines.

    """


    # Checking for Falsy doesn't work since "" and None are similar.
    if log_filename == "":
        log_filename = 'submission_runner.txt'

    if fmt_str is None or not fmt_str:
        fmt_str = "%(message)s"
        # Enable for more timing info
        #fmt_str="%(asctime)s - %(name)30s - %(levelname)10s: %(message)s"

    fmt_str = logging.Formatter(fmt_str)
    logger.setLevel(logging.DEBUG)


    stdout = logging.StreamHandler()
    stdout.setFormatter(fmt_str)
    stdout.setLevel(logging.INFO)
    logger.addHandler(stdout)

    if log_filename is not None:
        fout = logging.FileHandler(filename=log_filename, mode=log_file_mode)
        fout.setFormatter(fmt_str)
        fout.setLevel(logging.DEBUG)
        logger.addHandler(fout)

