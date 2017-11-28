#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=star-args

r"""
Download student submssion so that this can be tested by graders.

This is the front end tool to automate downloading student repos.
We read in the user input, parse it and call the back library correctly.

"""


__author__ = ["David Tran", "Travis Janssen"]
__status__ = "Production"
__version__ = "1.0.0"


import argparse

import prep_repos

def process_submission(
  assignment_name, deadline, report_filename, student_whitelist=None,
  should_git_pull=True, is_team=False):
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

      should_git_pull:   (boolean) Tells the backend if a git repo should be
        pulled.

      is_team:   (boolean) States if the assignment is a group one.

    """


    submissions = prep_repos.Submissions(
      is_team_project=is_team, should_git_pull=should_git_pull)

    submissions.prep_repos(
      submission_folder_name=('./submissions/%s' % assignment_name),
      deadline=deadline,
      whitelist=student_whitelist,
      is_team_project=is_team)

    submissions.generate_report(
      assignment=assignment_name,
      student_list=student_whitelist,
      report_filename=report_filename,
      is_team_project=is_team)


    if is_team:
        submissions.create_team_json('student_teams.txt')
    else:
        submissions.create_student_json('students_full.txt')


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
            return [line.strip() for line in open(filename)]
        except IOError:
            print("WARNING: We will grab repos from all students")
            return None


    # Remember in Python, range starts from the first value but ends in
    # the penultimate value (not the last value!)
    possible_argument_list = (['A%d' % i for i in range(1, 9)] +
                              ['D%d' % i for i in range(0, 5)])

    # The list of repos we will not preform a git pull
    no_git_pull_list = ['D%d' % i for i in range(1, 5)]

    # Deadline info EST + 4 hours = UTC, which is the T-Square deadline

    assignment_dict = {
      'A1': {
        'deadline' : '2017-08-28 12:05:00',
        'assignment_name' : 'Assignment 1 Team Matching Survey',
        },
      'A2': {
        'deadline' : '2017-09-02 12:05:00',
        'assignment_name' : 'Assignment 2 Git usage'
        },
      'A3': {
        'deadline' : '2017-09-09 12:05:00',
        'assignment_name' : 'Assignment 3 Basic Java coding and JUnit',
        },
      'A4': {
        'deadline' : '2017-09-16 12:05:00',
        'assignment_name' : 'Assignment 4 Simple Android App',
        },
      'A5': {
        'deadline' : '2017-09-23 12:05:00',
        'assignment_name' : 'Assignment 5 Software Design',
        },
      'A6': {
        'deadline' : '2017-10-28 12:05:00',
        'assignment_name' : 'Assignment 6 Category partition',
        },
      'A7': {
        'deadline' : '2017-11-04 12:05:00',
        'assignment_name' : 'Assignment 7 White-Box Testing',
        },
      'D0': {
        'deadline' : '2017-09-23 12:05:00',
        'assignment_name' : 'Group Project, Deliverable 0',
        },
      'D1': {
        'deadline' : '2017-09-30 12:05:00',
        'assignment_name' : 'Group Project, Deliverable 1',
        },
      'D2': {
        'deadline' : '2017-10-07 12:05:00',
        'assignment_name' : 'Group Project, Deliverable 2',
        },
      'D3': {
        'deadline' : '2017-10-14 12:05:00',
        'assignment_name' : 'Group Project, Deliverable 3',
        },
      'D4': {
        'deadline' : '2017-10-21 12:05:00',
        'assignment_name' : 'Group Project, Deliverable 4',
        },
      }


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


    if assignment_name not in possible_argument_list:
        print("ERROR: Assignment %2s is not a valid assignment" %
              assignment_name)
        return -1

    assignment_info = assignment_dict.get(assignment_name, None)

    if assignment_info is None:
        print("ERROR: No assignment for %2s set!")
        return -1


    #new_assignment_name = assignment_info['assignment_name'].replace(' ', '_')
    #assignment_info['assignment_name'] = new_assignment_name

    # Parse the assignment info and add more arguments

    # This is the python Ternary operator
    is_team = False if assignment_name.startswith('A') else True

    prefix = 'team' if is_team else 'student'
    report_filename = 'report_%s_%s.txt' % (assignment_name, prefix)

    student_filename = ('team.txt' if is_team else
                        'student_%s.txt' % assignment_name)
    student_whitelist = get_students_list_from_file(filename=student_filename)

    assignment_info['is_team'] = is_team
    assignment_info['report_filename'] = report_filename
    assignment_info['should_git_pull'] = (
      False if assignment_name in no_git_pull_list else True)
    assignment_info['student_whitelist'] = student_whitelist


    process_submission(**assignment_info)


if __name__ == "__main__":
    parse_main(submission_target=None)
