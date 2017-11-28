##!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
For the purposes of this file, we assume that a student is either a student
or a team to make parsing easier, since most of the logic is identical.

Created by Travis Janssen and David Tran
"""

from collections import defaultdict

import datetime
import json
import itertools
import os
import platform
import re
import subprocess

import logging
logger = logging.getLogger(__name__)


class Submissions(object):


    def __init__(self, is_team, should_git_pull):
        """
        Defines the variables for the current class.

        We could define static variables but they are not private and
        are publicly accessible in Python.

        Arguments:
          self.is_team:   (boolean) Sets if this submmission is a team project or not>

        """


        self.FOLDER_PREFIX = '6300Fall17'
        self.git_context = 'gt-omscs-se-2017fall'
        self.student_records_filename = 'student_records.json'
        self.student_alias_filename = 'student_aliases.json'
        self.team_records_filename = 'student_records_teams.json'
        self.team_members_filename = 'student_records_team_members.json'
        self.datetime_format = '%Y-%m-%d %H:%M:%S'
        self.should_git_pull = True
        self._dict_cache = {}  # cache some dictionary info here to save on IO operations
        self._pulled_teams = []  # don't pull team repos up to 4x if you can avoid it

        self.is_team = is_team
        self.should_git_pull = should_git_pull

        self.MAIN_REPO_DIR = 'Repos'

        # Stored to be used in later logic, so typos between copies don't exist
        self.STR_INVALID = "Invalid"
        self.STR_MISSING = "Missing"
        self.STR_OK = "Ok"
        self.STR_LATE = "Late"
        self.BAD_STR_LIST = [self.STR_INVALID, self.STR_MISSING]

        # Cache results
        self.OS_TYPE = platform.system()


    def create_student_json(self, input_filename):
        """
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
              "create_student_json: couldn't find file with name %s. Exiting."
              % input_filename)


    def create_team_json(self, input_filename):
        """
        Converts the input file to two useful JSON files specifically
        for team grading.

        Arguments:
          input_filename:   (str) The input filename we will parse into JSON
            files.

        """


        try:
            with open(input_filename, 'r') as input_file:

                student_dict, teams_list = {}, defaultdict(list)

                for line in input_file:

                    parsed = line.strip().split('\t')

                    student = parsed[0]
                    team = parsed[2] if len(parsed) >= 3 else 'None'

                    student_dict[student] = team
                    teams_list[team].append(student)

            with open(self.team_records_filename, 'w') as student_teams_file:
                json.dump(student_dict, student_teams_file)
            with open(self.team_members_filename, 'w') as team_members_file:
                json.dump(teams_list, team_members_file)

        except IOError:
            raise IOError(
              "create_team_json couldn't find file with name %s" %
              input_filename)



    def prep_repos(self, submission_folder_name, deadline, whitelist=None):

        assignment_alias = submission_folder_name.split('/')[-1]

        if not os.path.isdir(self.MAIN_REPO_DIR):
            os.makedirs(self.MAIN_REPO_DIR)

        if not os.path.isdir(submission_folder_name):
            raise IOError("Submission folder name '%s' not found. Exiting." %
                          submission_folder_name)

        if self.is_team:
            teams = self.get_dictionary_from_json_file(
              self.team_records_filename)

        students = None

        try:
            with open(self.student_records_filename, 'r+') as (
              student_records_file):

                students = json.load(student_records_file)

                if whitelist is None:
                    folders = filter(os.path.isdir, os.listdir(submission_folder_name))
                else:
                    folders = self.get_student_folder_names_from_list(
                      whitelist)

                for folder in folders:

                    parsed = folder.split('(')
                    t_square_id = parsed[1].strip(')')

                    current_student = students.get(t_square_id, None)
                    current_student_id = current_student['gt_id']
                    if current_student is None:
                        continue

                    if (whitelist is not None and (
                      (not self.is_team and
                       current_student_id not in whitelist) or
                      (self.is_team and
                       teams[current_student_id] not in whitelist)
                      )):
                        continue

                    # reset info for current assignment
                    current_student[assignment_alias] = {}

                    # get submission text
                    current_student = self.check_submission_file(current_student, t_square_id, submission_folder_name, folder, assignment_alias)

                    # get t-square timestamp
                    current_student = self.check_timestamp_file(current_student, submission_folder_name, folder, assignment_alias)

                    # clone repo if needed - note that you'll need to authenticate with github here; debugger may not work properly
                    self.setup_student_repo(current_student)

                    # only check commit ID validity and GitHub timestamp on valid commits
                    if self.is_commit_present(current_student[assignment_alias]['commitID']):
                        # try to check out commit ID
                        current_student = self.check_commit_ID(current_student, assignment_alias)

                        current_student = self.check_timestamp_github(current_student, assignment_alias, deadline)

                    # check T-Square timestamp against deadline
                    current_student = self.check_timestamp_t_square(current_student, assignment_alias, deadline)

                    # save info
                    students[t_square_id] = current_student

            if students is not None:
                # save info
                with open(self.student_records_filename, 'w') as output_file:
                    json.dump(students, output_file)

            # check out most recent commit
            if self.is_team and whitelist is not None:
                teams = self.get_dictionary_from_json_file(self.team_members_filename)
                aliases = self.get_dictionary_from_json_file(self.student_alias_filename)

                for team in whitelist:
                    members, commits = teams[team], []

                    for student in members:
                        t_square_id = aliases[student]
                        student_info = students[t_square_id]

                        try:
                            commit_time = student_info[assignment_alias]['Timestamp GitHub']
                            commit_ID = student_info[assignment_alias]['commitID']
                        except KeyError:
                            continue

                        if self.is_commit_present(commit_ID) and commit_time != 'N/A':
                            commits.append((commit_time, commit_ID))

                    commits.sort(reverse=True) # most recent should be first

                    try:
                        most_recent_commit_time, most_recent_commit = commits[0]

                    except IndexError:
                        most_recent_commit = most_recent_commit_time = 'None'

                    # checkout most recent commit here
                    if len(commits) > 0:

                        try:
                            command_checkout = (
                              'cd %s; git checkout %s;' % (
                                self.gen_prefixed_dir(team),
                                most_recent_commit))

                            _ = self.execute_command(command_checkout)

                        except subprocess.CalledProcessError:
                            raise subprocess.CalledProcessError

                    else:
                        print("NO VALID COMMITS FOR %s!" % team)

        except IOError:
            raise IOError("prep_repos couldn't find student records file."
                          "Run create_student_json first.")


    def get_student_team(self, student_gt_id):

        teams = self.get_dictionary_from_json_file(self.team_records_filename)

        try:
            team = teams[student_gt_id]
        except IndexError:
            raise IndexError("Couldn't find team for student with GTID %s" %
                             student_gt_id)

        return team


    def get_dictionary_from_json_file(self, file_name):

        info = {}

        if file_name not in self._dict_cache.keys():
            try:
                with open(file_name, 'r') as my_file:
                    info = json.load(my_file)
                    self._dict_cache[file_name] = info

            except IOError:
                logger.error("Couldn't open file with name %s\n", file_name)

        else:
            info = self._dict_cache[file_name]

        return info


    def get_student_folder_names_from_list(self, whitelist):

        if self.is_team:

            team_dict = self.get_dictionary_from_json_file(
              self.team_members_filename)

            # Read data in whitelist
            whitelist_multi_list = [team_dict[team] for team in whitelist]
            # Flatten multilist and store it back
            whitelist = list(itertools.chain.from_iterable(whitelist_multi_list))

            # whitelist now contains student GTIDs instead of just team names

        t_square_aliases = self.get_dictionary_from_json_file(self.student_alias_filename)
        student_info = self.get_dictionary_from_json_file(self.student_records_filename)

        folders = []

        for student in whitelist:

            try:
                t_square_id = t_square_aliases[student]
                name = student_info[t_square_id]['name']

            except IndexError:
                logger.error("Couldn't get folder name for student with GTID %s\n",
                             student)

            folders.append('%s(%s)' % (name, t_square_id))

        return folders

    def check_submission_file(self, current_student, t_square_id,
                              submission_folder_name, folder, assignment_alias):

        try:
            submission_file = '%s(%s)_submissionText.html' % (
              current_student['name'], t_square_id)

            with open(os.path.join(submission_folder_name, folder, submission_file), 'r') as submission_info:

                strings = re.findall(r'([0-9A-Za-z]{40})', submission_info.read())

                if len(strings) == 0:
                    current_student[assignment_alias]['commitID'] = self.STR_INVALID

                else:
                    current_student[assignment_alias]['commitID'] = strings[0]    # tiebreak: use first in list
        except IOError:
            current_student[assignment_alias]['commitID'] = self.STR_MISSING

        return current_student

    def check_timestamp_file(self, current_student, submission_folder_name,
                             folder, assignment_alias):

        try:
            timestamp_file = "timestamp.txt"

            with open(os.path.join(submission_folder_name, folder, timestamp_file), 'r') as timestamp_info:
                timestamp = timestamp_info.read()
                current_student[assignment_alias]['Timestamp T-Square'] = timestamp

        except IOError:
            current_student[assignment_alias]['Timestamp T-Square'] = "Missing"
            current_student[assignment_alias]['commitID'] = "Missing"

        return current_student


    def setup_student_repo(self, current_student):

        if self.is_team:
            repo_suffix = self.get_student_team(current_student['gt_id'])

        else:
            repo_suffix = current_student['gt_id']


        if not os.path.isdir(self.gen_prefixed_dir(repo_suffix)):

            command = 'cd %s; git clone https://github.gatech.edu/%s/%s%s.git; cd ..' % (
              self.MAIN_REPO_DIR, self.git_context,
              self.FOLDER_PREFIX, repo_suffix)
            _ = self.execute_command(command)

            if self.is_team:
                self._pulled_teams.append(repo_suffix)  # just do this once

            just_cloned_repo = True

        else:

            just_cloned_repo = False

        # revert any local changes and pull from remote
        try:
            command_setup = 'cd %s && git clean -fd && git reset --hard HEAD && git checkout .;' % (
              self.gen_prefixed_dir(repo_suffix))

            if self.should_git_pull and (
              not self.has_pulled_repo_for_team(repo_suffix) or
              just_cloned_repo):

                command_setup += "git pull;"

            _ = self.execute_command(command_setup)

        except subprocess.CalledProcessError, e:

            try:
                logger.error("%s subprocess.CalledProcessError: %s\n",
                             current_student['gt_id'], str(e.output))

            except UnicodeDecodeError:
                logger.error("%s subprocess.CalledProcessError: "
                             "UnicodeDecodeError\n", current_student['gt_id'])

    def check_timestamp_github(self, current_student,
                               assignment_alias, deadline):

        if not current_student[assignment_alias]['commitID valid']:
            current_student[assignment_alias]['Submission GitHub'] = 'N/A'
            current_student[assignment_alias]['Timestamp GitHub'] = 'N/A'
        else:
            if self.is_team:
                repo_suffix = self.get_student_team(current_student['gt_id'])
            else:
                repo_suffix = current_student['gt_id']

            # check timestamp of GitHub commit
            command_timestamp = (
              'cd %s; git show -s --format=%%ci %s; cd -' % (
                self.gen_prefixed_dir(repo_suffix),
                current_student[assignment_alias]['commitID']))

            output_timestamp = self.execute_command(command_timestamp)

            timestamp_full = output_timestamp.split('/')[0].split(' ')
            timestamp_github_raw = (timestamp_full[0] + " " + timestamp_full[1])
            timezone_raw = timestamp_full[2].strip()
            timezone = int(int(timezone_raw) * -1) / 100

            dt_object = datetime.datetime.strptime(timestamp_github_raw, self.datetime_format)
            dt_final = dt_object + datetime.timedelta(hours=timezone)
            timestamp_github = dt_final.strftime(self.datetime_format)

            # check GitHub timestamp against deadline
            current_student[assignment_alias]['Timestamp GitHub'] = timestamp_github
            if timestamp_github < deadline:
                current_student[assignment_alias]['Submission GitHub'] = self.STR_OK
            else:
                current_student[assignment_alias]['Submission GitHub'] = self.STR_LATE

        return current_student

    def check_timestamp_t_square(self, current_student, assignment_alias, deadline):

        if current_student[assignment_alias]['Timestamp T-Square'] != 'Missing':
            temp = current_student[assignment_alias]['Timestamp T-Square']
            timestamp_t_square = "%s-%s-%s %s:%s:%s" % (
              temp[0:4], temp[4:6], temp[6:8], temp[8:10], temp[10:12], temp[12:14])
            current_student[assignment_alias]['Timestamp T-Square'] = timestamp_t_square
            if timestamp_t_square <= deadline:
                current_student[assignment_alias]['Submission T-Square'] = self.STR_OK
            else:
                current_student[assignment_alias]['Submission T-Square'] = self.STR_LATE

        return current_student

    # Hashed?
    def check_commit_ID(self, current_student, assignment_alias):

        key = current_student['gt_id']
        repo_suffix = self.get_student_team(key) if self.is_team else key

        # CD First?
        command_checkout = ('cd %s; git checkout %s; git log --pretty=format:\'%%H\' -n 1; cd -' %
                            (self.gen_prefixed_dir(repo_suffix),
                             current_student[assignment_alias]['commitID']))
        output_checkout = self.execute_command(command_checkout)

        if self.OS_TYPE == 'Windows':
            commit = output_checkout[1:len(output_checkout)-1] # windows returns \\ prefix and suffix
        else:
            commit = output_checkout.split('/')[0]

        current_student[assignment_alias]['commitID valid'] = commit == current_student[assignment_alias]['commitID']

        return current_student


    def has_pulled_repo_for_team(self, team_number):

        has_already_pulled = False

        if self.is_team:
            if team_number in self._pulled_teams:
                has_already_pulled = True
            else:
                self._pulled_teams.append(team_number)

        return has_already_pulled


    def execute_command(self, command):
        """
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
            command = command.replace('& cd -', '')

        return subprocess.check_output(command, shell=True)


    def generate_report(self, assignment, student_list=None,
                        report_filename=None):
        """
        This general the final report that can be used by a grader.

        The result is outputted to a file (report_filename) and to stdout.

        Arguments:
          assignment:   (str) This is the name of the assignment we are
            comparing against.

          student_list:   (list of str) This is a list of students that we
            will analyze and prints the results.

          report_filename:   (str) This is the filename of the report will generate,
            in addition to stdout. To disable this feature, pass in None.

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

            bad_commit, late_github, late_t_square, missing = [], [], [], []

            init_log(log_filename=report_filename)
            logger.info("Report: %s\n", assignment)

            if self.is_team:

                teams = self.get_dictionary_from_json_file(
                  self.team_members_filename)

                new_student_list = []

                for team in student_list:

                    members_list = teams[team]

                    new_student_list.append(team)
                    new_student_list.extend(members_list)

                student_list = new_student_list

            elif student_list is None or not student_list:
                student_list = student_aliases.keys() # all student_list!
            else:
                pass # Do nothing


            for student in student_list:

                if not student: # ignore whitespace/blank lines
                    continue

                if self.is_team and "Team" in student:
                    logger.info("\n========== %s ==========", student)
                    continue

                student_info = student_records[student_aliases[student]]

                logger.info(student)

                if assignment not in student_info:

                    logger.info('\tNo records found')
                    missing.append(student)
                    continue

                student_info_assignment = student_info[assignment]
                for key in sorted(student_info_assignment.keys(), reverse=True):

                    student_info_assignment_key = student_info_assignment[key]
                    logger.info('\t%s: %s', key, student_info_assignment_key)

                    for target_key, target_value, target_list in [
                      ('Submission GitHub', 'late', late_github),
                      ('Submission T-Square', 'late', late_t_square),
                      ('commitID', 'Missing', missing),
                      ('commitID valid', False, bad_commit)
                      ]:

                        if (key == target_key and
                            student_info_assignment_key == target_value):

                            target_list.append(student)


            logger.info("\n========== RESULTS ==========")
            str_buffer = []
            str_buffer.append("\nLATE SUBMISSIONS:")
            for fmt_str, data in [("\tT-Square (%d): %s", late_t_square),
                                  ("\tGitHub (%d): %s", late_github),
                                  ("\nMISSING SUBMISSIONS (%s): %s", missing),
                                  ("\nBAD COMMITS (%s):\n\t%s", bad_commit)]:

                str_buffer.append(fmt_str % (len(data), ", ".join(data)))

            logger.info("\n".join(str_buffer))


        except IOError:
            msg = (("generate_report couldn't find %s file."
                    "Try running create_student_json first.") %
                   self.student_alias_filename)
            print(msg)
            raise IOError(msg)


    def gen_prefixed_dir(self, prefix_str):
        """
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
        """
        Checks if the commit statue message states it is present.

        Arguments:
          commit_status:   (str) The current commit status.

        Returns:
          True if it's not a bad commit or False if it is.

        """


        return commit_status not in self.BAD_STR_LIST


def init_log(log_filename=None, log_file_mode='w', fmt_str=None):
    """
    Initializes the logging for this file.

    This should not be in a class as this is unique per file (program file).

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

