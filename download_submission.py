#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=star-args

r"""
Download student submission so that this can be tested by graders.

This is the front end tool to automate downloading student repos.
We read in the user input, parse it and call the back library correctly.

Execute this program with the -h for help or the two letter code for the
assignment to download it.

NOTE:
Correct UTC time is 'YYYY-MM-DDTHH:MM:SS±HH:SS'
Python 2.X does not natively support timezones, %Z for datetime module.
There are external modules that exist but for the purpose of this project,
we will assume all times are fed in as UTC and time values from Git commits
are normalized correctly.

Do not forget about datetime's isoformat to get this result!

"""


__all__ = ["get_assignment_info", "process_assignment", ]
__author__ = "Travis Janssen, David Tran"
__credits__ = ["Travis Janssen", "David Tran"]
__status__ = "Production"
__version__ = "1.0.0"


import argparse
import inspect
from itertools import product

from process_submissions import Submissions


def process_assignment(
  assignment_name, assignment_code, deadline, report_filename, student_whitelist=None,
  should_pull_repo_flag=True, is_team=False, should_create_json_files=False):
    r"""
    Calls the backend to do the processing.

    Arguments:
      assignment_name:   (str) This is the name of the assignment,
        which will be used to create the directory.

      assignment_code:   (str) This is the two letter name for the assignment.

      deadline:   (str) This is the deadline for the assignment, to
        check if this late. The format is: 'YYYY-MM-DDTHH:MM:SS'

      student_whitelist:   (list of str) This is a list of strings of
        students what we will whitelist. That is to say all students
        in the list will not be ignored.

      should_pull_repo_flag:   (boolean) Tells the backend if a git repo
        should be pulled.

      is_team:   (boolean) States if the assignment is a group one.

    """


    submissions = Submissions(is_team=is_team,
                              should_pull_repo_flag=should_pull_repo_flag)

    # Optionally create JSON files, otherwise skip. Access this with -j input argument.
    if should_create_json_files:
        submissions.create_student_json('students_full.txt')

    if should_create_json_files and is_team:
        submissions.create_team_json('teams_full.txt')  # don't try to create team JSONs at the beginning; teams are not normally available at semester start

    submissions.process_repos(
      submission_folder_name=('./submissions/%s' % assignment_name),
      deadline=deadline,
      assignment_code=assignment_code,
      student_whitelist=student_whitelist,
      should_pull=should_pull_repo_flag)

    submissions.generate_report(
      assignment=assignment_name,
      student_list=student_whitelist,
      report_filename=report_filename)


def get_assignment_info(assignment_name, should_pull_repo_flag=None,
                        is_batch_run=False):
    r"""
    Converts the parser input into a complete Python dictionary to call the
    backend.

    Arguments:
      assignment_name:   (str) The two letter assignment code for submission.

      should_pull_repo_flag:   (boolean) This is an override specifying
      if we should download the repos from Git or not. By default this is None.
      Here are the possible options:

      None:  Default auto settings which is download repos for all individual
            assignments and the first part of a team assignment.

        True (or anything Truthy): Always download repos from Github.

        False (or anything Falsy but not None): Never download repos from
        Github.

      is_batch_run:   (boolean) States if this is a batch run. Prints are
        suppressed if they are.

    Returns:
      A dictionary with keys that can be used for the backside.
      The keys include:

      deadline:   (str) This is the deadline of the assignment if it is
        late. The input must be in strict ISO 8601 format
        'YYYY-MM-DDTHH:MM:SS'. As python 2 does NOT natively support
        different timezones, this must be in UTC timezone to be correctly
        comparable.

      assignment_name:   (str) This is the name of assignment that is
        used to store student submissions.

      is_team:  (boolean) This states if the submission is a team based or
        individual based one.

      report_filename:   (str) This is the name of the report that is
        generated. The output is sent to both stdout as well as this file.

      should_pull_repo_flag:   (boolean) This sets a flag if a repo should be
        pulled. Setting this to True does not guarantee it since we may
        cache the results.

      student_whitelist:   (list of str) This is the list of student username
        IDs that we will whitelist. That is to say all students in the list
        will not be ignored.

    """


    def get_students_list_from_file(filename='students.txt'):
        r"""
        For some assignments, we only want to grade a select set of students.

        This function finds the list of students, if one exists, and get
        the stored value from a file.

        Arguments:
          filename:   (str) The filename we will open.  This should consist
            of GT IDs, separated by newlines.

        Return:
        A list of students that should be whitelisted.
        """


        try:

            # The input may be in unicode so we filter that and strip it
            student_whitelist = list(map(str.strip, map(str, open(filename))))

            while "" in student_whitelist:
                student_whitelist.remove("")

            return student_whitelist

        except IOError:

            if not is_batch_run:
                print("WARNING: We will process repos from all students")

            return None


    # Deadline info is EST + 4 hours = UTC, which is the T-Square deadline
    # Anywhere on Earth time is UTC-12. Worst case: UTC+12 (like Wake Island) --> midnight AoE = +2 days at midnight, so 1/26/2018 midnight = 1/28/2018 midnight
    assignment_dict = {
      'A1': {
        'deadline' : '2018-08-28 03:59:00',
        'assignment_name' : 'A1',
        },
      'A2': {
        'deadline' : '2018-09-02 00:00:00',
        'assignment_name' : 'A2',
        },
      'A3': {
        'deadline' : '2018-09-09 00:00:00',
        'assignment_name' : 'A3',
        },
      'A4': {
        'deadline' : '2018-09-16 00:00:00',
        'assignment_name' : 'A4',
        },
      'A5': {
        'deadline' : '2018-09-23 00:00:00',
        'assignment_name' : 'A5',
        },
      'A6': {
        'deadline' : '2018-10-28 00:00:00',
        'assignment_name' : 'A6',
        },
      'A7': {
        'deadline' : '2018-11-04 00:00:00',
        'assignment_name' : 'A7',
        },
      'I1': {
        'deadline' : '2018-11-11 00:00:00',
        'assignment_name' : 'I_D1',
        },
      'I2': {
        'deadline' : '2018-11-18 00:00:00',
        'assignment_name' : 'I_D2',
        },
      'I3': {
        'deadline' : '2018-12-02 00:00:00',  # note: summer doesn't use I3
        'assignment_name' : 'I_D3',
        },
      'T0': {
        'deadline' : '2018-10-23 00:00:00',
        'assignment_name' : 'T_D0',
        },
      'T1': {
        'deadline' : '2018-10-30 00:00:00',
        'assignment_name' : 'T_D1',
        },
      'T2': {
        'deadline' : '2018-10-07 00:00:00',
        'assignment_name' : 'T_D2',
        },
      'T3': {
        'deadline' : '2018-10-14 00:00:00',
        'assignment_name' : 'T_D3',
        },
      'T4': {
        'deadline' : '2018-10-19 00:00:00',
        'assignment_name' : 'T_D4',
        },
      }

    # The list of possible assignments we can grab
    possible_argument_list = assignment_dict.keys()

    # Remember in Python, range starts from the first value but ends in
    # the penultimate value (not the last value!)

    # The list of repos we will not preform a git pull
    no_git_pull_list = (['I%d' % i for i in range(2, 5)] +
                        ['T%d' % i for i in range(1, 5)])

    if assignment_name not in possible_argument_list:
        if not is_batch_run:
            print("ERROR: Assignment %s is not a valid assignment" %
                  assignment_name)
        return {}

    assignment_info = assignment_dict.get(assignment_name, None)

    if assignment_info is None:
        if not is_batch_run:
            print("ERROR: No assignment info for %s set!")
        return {}


    # This corresponds to the T-Square output so don't change it
    # assignment_info['assignment_name']


    # This is the Python Ternary operator
    is_team = True if assignment_name.startswith('T') else False
    is_multi_assignment = True if not assignment_name.startswith('A') else False

    prefix = 'team' if is_team else 'student'
    report_filename = 'report_%s_%s.txt' % (assignment_name, prefix)

    student_filename = None
    if is_team:
        student_filename = 'team.txt'
    elif is_multi_assignment:
        student_filename = 'individual.txt'
    else:
        student_filename = 'students_%s.txt' % assignment_name

    student_whitelist = get_students_list_from_file(filename=student_filename)

    assignment_info['is_team'] = is_team
    assignment_info['report_filename'] = report_filename
    assignment_info['student_whitelist'] = student_whitelist

    if should_pull_repo_flag is None:
        assignment_info['should_pull_repo_flag'] = (
          False if assignment_name in no_git_pull_list else True)
    else:
        assignment_info['should_pull_repo_flag'] = bool(should_pull_repo_flag)

    assignment_info['assignment_code'] = assignment_name

    return assignment_info


def parse_main(submission_target=None):
    r"""
    Reads the user input, via an argument passed in and selects the right
    submission to process.

    Arguments:
      submission_target:   (str) This is the submission we want to target.
        This overrides the default option which is to process via the
        user argument and instead uses this as the submission we will
        process.

    """


    # Cache Results
    func_name = inspect.currentframe().f_code.co_name

    # States if we will always pull from the Repo
    # None is auto, True is always, False is never
    pull_from_github = None
    create_json_files = None


    # Remember in Python, range starts from the first value but ends in
    # the penultimate value (not the last value!)

    # This is a list of ALL possible assignments allowed by the parser.
    # These will include more options than actual assignments so it is
    # easier or remove assignments as needed but change the ranges as needed.
    possible_argument_list = (['A%d' % i for i in range(1, 10)] +
                              ['I%d' % i for i in range(1, 5)] +
                              ['T%d' % i for i in range(0, 6)] +
                              ['I', 'T'])

    # Make sure this matches with the above list so users know which values
    # are correct

    # This is created to shorten the list above
    printable_arg_list = "{A1..A9,I,I1..I4,T,T0..T5}"

    # Parse user input if not overridden
    if submission_target is None:

        parser = argparse.ArgumentParser(
          description="TA Download Automation Tool",
          epilog=("Change submission_target in the code to manually override "
                  "this arg parser and allow remote execution"))

        parser.add_argument(
          'assignment_name', choices=possible_argument_list, nargs='+',
          help=(
            "select the assignment to download, formatted at A# or I# or T#\n"
            "Entering only I or T will grab all commits together for "
            "said projects"),
          metavar=printable_arg_list,
          )

        parser.add_argument(
          '-p', '--pull', #action='store_true',
            choices=['True', 'False'],
          default=None,
         # type=bool,
          dest='pull_from_github',
          help="overrides the default settings and always pull the repo",
          )

        parser.add_argument(
          '-v', '--version', action='version',
          version="%%(prog)s Version: %s" % __version__,
          )

        parser.add_argument(
            '-j', '--json_create', action='store_const',
            const=True,
            default=None,
            dest='create_json_files',
            help='create the json files required for storing student semester data. Requires students_full.txt'
        )

        args = parser.parse_args()
        assignment_name = args.assignment_name

        if len(assignment_name) == 1:
            assignment_name = assignment_name[0]

        # Sanitize inputs
        pull_from_github = args.pull_from_github

        # is_team = True if assignment_name.startswith('T') else False
        if pull_from_github == "False":
            pull_from_github = False
        elif pull_from_github == 'True':
            pull_from_github = True
        else:
            pull_from_github = None

        create_json_files = args.create_json_files

        if create_json_files not in [True, None, False]:
            create_json_files = bool(create_json_files)

    else:

        assignment_name = submission_target # Removed unicode input

        if not isinstance(assignment_name, (list, str)):
            print("%s: assignment_name is not a string: '%s'" %
                  (func_name, str(submission_target)))


    if len(assignment_name) == 2 and isinstance(assignment_name, str):

        print("%s: Analyzing assignment '%s'" % (func_name, assignment_name))

        assignment_info = get_assignment_info(
          assignment_name=assignment_name,
          should_pull_repo_flag=pull_from_github
          )

        if not assignment_info:
            return -1

        assignment_info['should_create_json_files'] = create_json_files

        # ** Converts a dictionary to match all keywords in a function
        # declaration.
        process_assignment(**assignment_info)

    elif isinstance(assignment_name, list) or assignment_name[0] in ['I', 'T']:

        if assignment_name[0] in ['I', 'T']:
            letter = assignment_name[0]
            input_list = ["%s%d" % (letter, i) for i in range(5)]
        else:
            input_list = assignment_name

        print("%s: Batch processing..." % func_name)

        for assignment_code in input_list:

            print("%s: Analyzing assignment '%s'" % (
              func_name, assignment_code))

            assignment_info = get_assignment_info(
              assignment_name=assignment_code,
              should_pull_repo_flag=pull_from_github,
              is_batch_run=True)

            if assignment_info:

                print("\n\n%s: Starting run for '%s'" % (
                  func_name, assignment_code))
                process_assignment(**assignment_info)

            else:

                print("\n\n%s: Invalid assignment '%s'" % (
                  func_name, assignment_code))

    else:

        print("%s:Invalid Assignment code entered '%s'" %
              (inspect.currentframe().f_code.co_name, assignment_name))


if __name__ == "__main__":
    parse_main(submission_target=None)

