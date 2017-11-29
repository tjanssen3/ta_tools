##!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
For the purposes of this file, we assume that a student is either a student
or a team to make parsing easier, since most of the logic is identical.

"""


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
        self.STR_MISSING = "Missing"
        self.STR_OK = "Ok"
        self.STR_LATE = "Late"
        self.BAD_STR_LIST = [self.STR_INVALID, self.STR_MISSING]

        # Cache results
        self.cached_file_dicts = {}  # Cache dictionary pulls
        self.cached_teams_pulled = set() # Cache pulled teams

        self.OS_TYPE = platform.system()


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

                gt_id_dict, student_dict = {}, {}

                for line in input_file:

                    parsed_line = line.strip().split('\t')

                    name, gt_id, t_square_id = parsed_line[0:3]

                    student_dict[t_square_id] = {'name': name, 'gt_id': gt_id}
                    gt_id_dict[gt_id] = t_square_id

            with open(self.student_records_filename, 'w') as output_file:
                json.dump(student_dict, output_file)
            with open(self.student_alias_filename, 'w') as alias_file:
                json.dump(gt_id_dict, alias_file)

        except IOError:
            raise IOError(
              "%s: Missing file '%s'. Exiting." % (
                inspect.currentframe().f_code.co_name, input_filename))


    def process_repos(self, submission_folder_name,
                      deadline, student_whitelist=None):

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
            team_dict = self.get_file_dict(
              self.team_records_filename, inspect.currentframe().f_code.co_name)

        student_dict = self.get_file_dict(
          self.student_records_filename,
          inspect.currentframe().f_code.co_name,
          "Run create_student_json first.")


        if student_whitelist is None:
            directory_listing = list(
              filter(os.path.isdir, os.listdir(submission_folder_name)))

        else:
            directory_listing = self.get_student_folder_names_from_list(
              student_whitelist)


        for folder in directory_listing:

            parsed = folder.split('(')
            t_square_id = parsed[1].strip(')')

            current_student = student_dict.get(t_square_id, None)

            if current_student is None:
                continue

            gt_student_id = current_student['gt_id']

            if ((not self.is_team and
                    gt_student_id not in student_whitelist) or
                    (self.is_team and
                    team_dict[gt_student_id] not in student_whitelist)
                ):

                continue

            # Checking repeated results on calls to simplify them
            base_directory = os.path.join(submission_folder_name, folder)
            current_assignment = current_student[assignment_alias] = {}
            current_submission_file = (
                '%s(%s)_submissionText.html' % (
                current_student['name'], t_square_id))

            # Update submission text
            self.check_submission_file(
                current_assignment=current_assignment,
                base_directory=base_directory,
                submission_file=current_submission_file)

            # Update t-square timestamp
            self.compare_timestamp_file(
                current_assignment=current_assignment,
                base_directory=base_directory)

            # Clone repo if needed
            # NOTE: You'll need to authenticate with github here and
            # debuggers may not work properly
            self.setup_student_repo(gt_student_id)

            # Only check commit ID validity with GitHub timestamp
            if self.is_commit_present(current_assignment['commitID']):

                # Try to check out commit ID
                self.check_commit_ID(current_assignment, gt_student_id)

                self.compare_timestamp_github(
                    current_assignment, gt_student_id, deadline)

            # Check T-Square timestamp against deadline
            self.compare_timestamp_t_square(current_assignment, deadline)

            # Save Result
            student_dict[t_square_id] = current_student

        if student_dict is not None:

            # Save info
            with open(self.student_records_filename, 'w') as output_file:
                json.dump(student_dict, output_file)

        if self.is_team and student_whitelist:
            self.process_team_repos(assignment_alias, student_whitelist)


    def process_team_repos(self, assignment_alias, student_whitelist):

        aliases = self.get_file_dict(
          self.student_alias_filename,
          inspect.currentframe().f_code.co_name)

        student_dict = self.get_file_dict(
          self.student_records_filename,
          inspect.currentframe().f_code.co_name,
          "Run create_student_json first.")

        team_dict = self.get_file_dict(
          self.team_members_filename,
          inspect.currentframe().f_code.co_name)

        for team in student_whitelist:

            member_list, commit_list = team_dict[team], []

            for student in member_list:

                t_square_id = aliases[student]
                team_assignment = (
                    student_dict[t_square_id][assignment_alias])

                try:
                    commit_time = team_assignment['Timestamp GitHub']
                    commit_ID = team_assignment['commitID']

                except KeyError:
                    continue

                if (self.is_commit_present(commit_ID) and
                        commit_time != 'N/A'):

                    commit_list.append((commit_time, commit_ID))

            # checkout most recent commit here
            if len(commit_list) > 0:

                # Most recent should be first
                commit_list.sort(reverse=True)
                _, most_recent_commit = commit_list[0]

                command_checkout = (
                    'cd %s; git checkout %s;' % (
                    self.gen_prefixed_dir(team), most_recent_commit))

                _ = self.execute_command(command_checkout)

            else:
                print("%s: NO VALID COMMITS FOR %s!" % (
                    inspect.currentframe().f_code.co_name, team))


    def get_correct_reference_id(self, graded_id):
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

            team_dict = self.get_file_dict(
              self.team_records_filename, inspect.currentframe().f_code.co_name)

            try:
                team_id = team_dict[graded_id]

            except IndexError:
                raise IndexError(
                  "%s: Couldn't find team for student with GTID '%s'. Exiting."
                  % (inspect.currentframe().f_code.co_name, graded_id))

            return team_id

        else:

            # This is the student ID
            return graded_id


    def get_file_dict(self, filename, caller_name='', epilog=''):
        r"""
        Attempts to access the file and retrieve the JSON within it.

        Arguments:
          filename:   (str) The name of the file we will open.

          caller_name:   (str) This is the caller's function name when
            printing errors.

          epilog:   (str) This is the epilog error message if one is needed.

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

        #else:

        return file_dict


    def get_student_folder_names_from_list(self, student_whitelist):

        if self.is_team:

            team_dict = self.get_file_dict(
              self.team_members_filename, inspect.currentframe().f_code.co_name)

            # Read data in student_whitelist
            student_whitelist_multi_list = [team_dict[team] for team in student_whitelist]
            # Flatten multilist and store it back
            student_whitelist = list(itertools.chain.from_iterable(student_whitelist_multi_list))

            # student_whitelist now contains student GTIDs instead of just team names

        t_square_aliases = self.get_file_dict(
          self.student_alias_filename, inspect.currentframe().f_code.co_name)
        student_info = self.get_file_dict(
          self.student_records_filename, inspect.currentframe().f_code.co_name)

        folders = []


        for student in student_whitelist:

            try:
                t_square_id = t_square_aliases[student]
                name = student_info[t_square_id]['name']

            except IndexError:
                logger.error(
                  "Couldn't get folder name for student with GTID %s\n",
                  student)

            folders.append('%s(%s)' % (name, t_square_id))

        return folders


    def check_submission_file(self, current_assignment,
                              base_directory, submission_file):

        try:

            with open(os.path.join(base_directory, submission_file), 'r') as submission_info:

                strings = re.findall(r'([0-9A-Za-z]{40})',
                                     submission_info.read())

                commitID = strings[0] if len(strings) else self.STR_INVALID
                current_assignment['commitID'] = commitID

        except IOError:

            current_assignment['commitID'] = self.STR_MISSING


    def compare_timestamp_file(self, current_assignment, base_directory):

        try:

            target_filename = os.path.join(base_directory,
                                           self.timestamp_filename)

            with open(target_filename, 'r') as timestamp_info:

                timestamp = self.fix_timestamp_t_square(timestamp_info.read())
                current_assignment['Timestamp T-Square'] = timestamp

        except IOError:

            current_assignment['Timestamp T-Square'] = "Missing"
            current_assignment['commitID'] = "Missing"


    def setup_student_repo(self, gt_student_id):

        just_cloned_repo = None
        repo_suffix = self.get_correct_reference_id(gt_student_id)

        if not os.path.isdir(self.gen_prefixed_dir(repo_suffix)):

            command = ('cd %s; '
                       'git clone https://github.gatech.edu/%s/%s%s.git; '
                       'cd ..') % (
                         self.MAIN_REPO_DIR, self.GIT_CONTEXT,
                         self.FOLDER_PREFIX, repo_suffix)
            _ = self.execute_command(command)

            self.cached_teams_pulled.add(repo_suffix)

            just_cloned_repo = True

        else:

            just_cloned_repo = False


        # Revert any local changes and pull from remote
        try:

            pull_flag = ''

            if self.should_pull_repo(repo_suffix) or just_cloned_repo:

                pull_flag = 'git pull &&'

            command_setup = (
              'cd %s && git clean -fd && %s git reset --hard HEAD' % (
                self.gen_prefixed_dir(repo_suffix), pull_flag))

            _ = self.execute_command(command_setup)

        except subprocess.CalledProcessError as error:

            try:
                logger.error("%s: student '%s' subprocess.CalledProcessError: "
                             "%s\n",
                             inspect.currentframe().f_code.co_name,
                             gt_student_id, str(error.output))

            except UnicodeDecodeError:
                logger.error("%s: student '%s' subprocess.CalledProcessError: "
                             "UnicodeDecodeError\n",
                             inspect.currentframe().f_code.co_name,
                             gt_student_id)


    def compare_timestamp_github(self, current_assignment,
                                 student_id, deadline):

        if not current_assignment['commitID valid']:

            current_assignment['Submission GitHub'] = 'N/A'
            current_assignment['Timestamp GitHub'] = 'N/A'

        else:

            repo_suffix = self.get_correct_reference_id(student_id)

            # check timestamp of GitHub commit
            command_timestamp = (
              'cd %s; git show -s --format=%%cI %s; cd - &> /dev/null' % (
                self.gen_prefixed_dir(repo_suffix),
                current_assignment['commitID']))

            output_timestamp = self.execute_command(command_timestamp)

            dt_object = self.read_strict_ISO_format(output_timestamp)
            timestamp_github = dt_object.strftime(self.datetime_format)

            # check GitHub timestamp against deadline
            current_assignment['Timestamp GitHub'] = timestamp_github
            msg = self.STR_OK if timestamp_github < deadline else self.STR_LATE
            current_assignment['Submission GitHub'] = msg


    def fix_timestamp_t_square(self, time_str):
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


    def compare_timestamp_t_square(self, current_assignment, deadline):

        if current_assignment['Timestamp T-Square'] != 'Missing':
            final_time = current_assignment['Timestamp T-Square']

            msg = self.STR_OK if final_time <= deadline else self.STR_LATE
            current_assignment['Submission T-Square'] = msg


    def read_strict_ISO_format(self, time_str):
        r"""
        Reads in a strict ISO 8601 format date with the timezone and returns back
        the assocated time object.

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


    def check_commit_ID(self, current_assignment, gt_student_id):

        repo_suffix = self.get_correct_reference_id(graded_id=gt_student_id)

        command_checkout = (
          'cd %s; git checkout %s; '
          'git show --pretty=format:\'%%H\' --no-patch; cd - &> /dev/null' % (
            self.gen_prefixed_dir(repo_suffix),
            current_assignment['commitID']))

        output_checkout = self.execute_command(command_checkout)

            # Windows returns \\ prefix and suffix so strip it

        if self.OS_TYPE == 'Windows':
            commit = output_checkout[1:-1]
        else:
            commit = output_checkout

        valid_commit = commit == current_assignment['commitID']
        current_assignment['commitID valid'] = valid_commit


    def should_pull_repo(self, team_number):
        r"""
        Checks if we should pull a repo or assume it has been pulled already.

        This is only appliaple for team projects as multiple students work
        on the same repo.

        Arguments:
          team_number:   (str or any key)

        Return:
          A boolean saying if the repo should be pulled.

        """


        if not self.should_pull_repo_flag:
            return False

        should_pull = True

        if self.is_team:

            if team_number in self.cached_teams_pulled:

                should_pull = False

            # else:

            self.cached_teams_pulled.add(team_number)

        return should_pull


    def execute_command(self, command):
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


    def generate_report(self, assignment, student_list=None,
                        report_filename=None):
        r"""
        This general the final report that can be used by a grader.

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


        try:

            student_aliases = None
            with open(self.student_alias_filename, 'r') as alias_file:
                student_aliases = json.load(alias_file)

            student_records = None
            with open(self.student_records_filename, 'r') as records_file:
                student_records = json.load(records_file)

        except IOError:

            msg = (("%s: couldn't find %s or %s."
                    "Try running create_student_json first.") % (
                      inspect.currentframe().f_code.co_name,
                      self.student_alias_filename,
                      self.student_records_filename
                      ))
            raise IOError(msg)

        else:

            bad_commit, late_github, late_t_square, missing = [], [], [], []

            init_log(log_filename=report_filename)
            logger.info("Report: %s\n", assignment)

            if self.is_team:

                team_dict = self.get_file_dict(
                  self.team_members_filename,
                  inspect.currentframe().f_code.co_name)

                new_student_list = []

                for team in student_list:

                    members_list = team_dict[team]

                    new_student_list.append(team)
                    new_student_list.extend(members_list)

                student_list = new_student_list

            elif not student_list:

                student_list = student_aliases.keys() # Get all students

            #else:

            # Parse the student list for bad elements
            stripped_list = map(str.strip, map(str, student_list))
            final_list = list(filter(bool, stripped_list))

            bad_student_dict = {
              'Submission GitHub': ('late', late_github),
              'Submission T-Square': ('late', late_t_square),
              'commitID': ('Missing', missing),
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


    def gen_prefixed_dir(self, prefix_str):
        r"""
        This combines a directory prefix onto the valid directory,
        to target a student's directory.

        Arguments:
          prefix_str:   (str) A valid student's prefix (be it a team number
            or a student name) so we can access it.

        Returns:
          A valid directory that can be accessed.

        """


        return os.path.join(self.MAIN_REPO_DIR, "%s%s" %
                            (self.FOLDER_PREFIX, prefix_str))


    def is_commit_present(self, commit_status):
        r"""
        Checks if the commit statue message states it is present.

        Arguments:
          commit_status:   (str) The current commit status.

        Returns:
          True if it's not a bad commit or False if it is.

        """


        return commit_status not in self.BAD_STR_LIST


def init_log(log_filename=None, log_file_mode='w', fmt_str=None):
    r"""
    Initializes the logging for this file.

    This should not be in a class as this is unique per file (source code).

    This could be integrated by moving all logging commands but then all
    log names need to be unique to prevent clobbering. The default action is
    to append but set to overwrite since it is unlikely we need previous run
    info.

    Arguments:
      log_filename:   (str) This is the log file name we are outputting to.
        None will disable this and empty string will use the default name.

      log_file_mode:   (str) This sets the file bit for the output file.

        'w':  Overwrite (aka clobber the file)

        'a':  Append (aka add to the end of the file)

      fmt_str:   (str) This is the format string used for the logger,
        default if set to None or empty string is just the message.

    """


    # Checking for Falsy doesn't work since "" and None are similar.
    # None doesn't have a len
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

