#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=star-args

r"""
Download student submssion so that this can be tested by graders.

This is the front end tool to automate downloading student repos.
We read in the user input, parse it and call the back library correctly.

Execute this program with the -h for help or the two letter code for the
assignment to download it.

"""


__author__ = "David Tran, Travis Janssen"
__credits__ = ["David Tran", "Travis Janssen"]
__status__ = "Production"
__version__ = "1.0.0"


import argparse


import process_repos


def process_submission(
  assignment_name, deadline, report_filename, student_whitelist=None,
  should_pull_repo_flag=True, is_team=False):
    r"""
    Calls the backend to do the processing.

    Arguments:
      assignment_name:   (str) This is the name of the assignment,
        which will be used to create the directory.

      deadline:   (str) This is the deadline for the assignment, to
        check if this late. The format is: 'YYYY-MM-DD HH:MM:SS'

      student_whitelist:   (list of str) This is a list of strings of
        stdents what we will whitelist. That is to say all students not
        in the list will be ignored.

      should_pull_repo_flag:   (boolean) Tells the backend if a git repo
        should be pulled.

      is_team:   (boolean) States if the assignment is a group one.

    """


    submissions = process_repos.Submissions(
      is_team=is_team, should_pull_repo_flag=should_pull_repo_flag)

    submissions.process_repos(
      submission_folder_name=('./submissions/%s' % assignment_name),
      deadline=deadline,
      student_whitelist=student_whitelist)

    submissions.generate_report(
      assignment=assignment_name,
      student_list=student_whitelist,
      report_filename=report_filename)


    submissions.create_student_json('students_full.txt')


def get_assignment_info(assignment_name):
    r"""
    Converts the parser input into a complete Python dictionary to call the
    backend.

    Arguments:
      assignment_name:   (str) The two letter assignment code for submission.

    Returns:
      A dictionary with keys
    """


    def get_students_list_from_file(filename='students.txt'):
        r"""
        For some assignments, we only want to grade a select set of students.

        This function finds the list of students, if one exists, and get
        the stored value from a file.

        Arguments:
          filename:   (str) The filename we will open.  This should consist
            of GT IDs, separated by newlines.
        """


        try:

            # The input may be in unicode so we filter that and strip it
            return list(map(str.strip, map(str, open(filename))))

        except IOError:

            print("WARNING: We will process repos from all students")
            return None


    # Deadline info EST + 4 hours = UTC, which is the T-Square deadline

    assignment_dict = {
      'A1': {
        'deadline' : '2017-08-28T12:05:00',
        'assignment_name' : 'Assignment 1 Team Matching Survey',
        },
      'A2': {
        'deadline' : '2017-09-02T12:05:00',
        'assignment_name' : 'Assignment 2 Git usage'
        },
      'A3': {
        'deadline' : '2017-09-09T12:05:00',
        'assignment_name' : 'Assignment 3 Basic Java coding and JUnit',
        },
      'A4': {
        'deadline' : '2017-09-16T12:05:00',
        'assignment_name' : 'Assignment 4 Simple Android App',
        },
      'A5': {
        'deadline' : '2017-09-23T12:05:00',
        'assignment_name' : 'Assignment 5 Software Design',
        },
      'A6': {
        'deadline' : '2017-10-28T12:05:00',
        'assignment_name' : 'Assignment 6 Category partition',
        },
      'A7': {
        'deadline' : '2017-11-04T12:05:00',
        'assignment_name' : 'Assignment 7 White-Box Testing',
        },
      'D0': {
        'deadline' : '2017-09-23T12:05:00',
        'assignment_name' : 'Group Project, Deliverable 0',
        },
      'D1': {
        'deadline' : '2017-09-30T12:05:00',
        'assignment_name' : 'Group Project, Deliverable 1',
        },
      'D2': {
        'deadline' : '2017-10-07T12:05:00',
        'assignment_name' : 'Group Project, Deliverable 2',
        },
      'D3': {
        'deadline' : '2017-10-14T12:05:00',
        'assignment_name' : 'Group Project, Deliverable 3',
        },
      'D4': {
        'deadline' : '2017-10-21T12:05:00',
        'assignment_name' : 'Group Project, Deliverable 4',
        },
      }

    # The list of possible assignment we can grab
    possible_argument_list = assignment_dict.keys()

    # The list of repos we will not preform a git pull
    no_git_pull_list = ['D%d' % i for i in range(1, 5)]

    if assignment_name not in possible_argument_list:
        print("ERROR: Assignment %2s is not a valid assignment" %
              assignment_name)
        return {}

    assignment_info = assignment_dict.get(assignment_name, None)

    if assignment_info is None:
        print("ERROR: No assignment info for %2s set!")
        return {}


    #new_assignment_name = assignment_info['assignment_name'].replace(' ', '_')
    #assignment_info['assignment_name'] = new_assignment_name


    # This is the python Ternary operator
    is_team = False if assignment_name.startswith('A') else True

    prefix = 'team' if is_team else 'student'
    report_filename = 'report_%s_%s.txt' % (assignment_name, prefix)

    student_filename = ('team.txt' if is_team else
                        'student_%s.txt' % assignment_name)
    student_whitelist = get_students_list_from_file(filename=student_filename)

    assignment_info['is_team'] = is_team
    assignment_info['report_filename'] = report_filename
    assignment_info['should_pull_repo_flag'] = (
      False if assignment_name in no_git_pull_list else True)
    assignment_info['student_whitelist'] = student_whitelist


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


    # Remember in Python, range starts from the first value but ends in
    # the penultimate value (not the last value!)

    # This is a list of ALL possible assignments allowed by the parser.
    possible_argument_list = (['A%d' % i for i in range(1, 9)] +
                              ['D%d' % i for i in range(0, 5)])


    # Parse user input if not overriden
    if submission_target is None:

        parser = argparse.ArgumentParser(
          description="TA Download Automation Tool",
          epilog=("Change submission_target in the code to manually override "
                  "this arg pargser and allow remote execution"))

        parser.add_argument(
          'assignment_name', choices=possible_argument_list,
          help="Select the assignment to download, formatted at A# or D#")

        args = parser.parse_args()
        assignment_name = args.assignment_name

    else:
        assignment_name = submission_target

    assignment_info = get_assignment_info(assignment_name=assignment_name)

    if not assignment_info:
        return -1

    process_submission(**assignment_info)


if __name__ == "__main__":
    parse_main(submission_target=None)

