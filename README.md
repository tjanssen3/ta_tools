# ta_tools
Tools for use by OMSCS TAs; originally created for CS 6300.
This will download GitHub repos for students in bulk, parse through submission text for commit IDs, try to check them out, then get information about timestamps from T-Square and GitHub and compare them against a deadline.

## Dependencies
1) Python 2.7
2) Command line access
3) Student data from Google Drive: students_full.txt, student_records.json, student_aliases.json
4) Recommended: Pycharm IDE

# Initial Setup
1) Clone this repo to your machine
2) Download the student info from Google Drive; extract to this folder (git should ignore those files)

# Workflow
1) Download the 'student submission text' submissions from T-Square in bulk
2) Extract the file to the 'submissions' folder (technically it can go anywhere, but I like to keep these in one place)
3) Set up your assignment for grading (see Usage section for specifics) with a new function
4) Open the command line and run the new function you just wrote
5) Authenticate with GitHub and let the scripts run
6) View output in console and the report file
7) Start grading!

# Usage
When you set up a new assignment for grading, you'll need 4 things:
1) Deadline (I wrote this for EST; let me know if this is problematic for you)
2) Assignment name (this is the same as the folder you extracted into 'submissions')
3) The output file name you want to create
4) Your list of students to grade. If you don't specify a list, it'll download repos for the whole class.

Create a new function like this in test_submissions.py:
```
    def test_generate_A3_report(self):
        deadline = "2017-06-03 12:05:00"  # EST + 4 hours = UTC, which is the T-Square deadline
        assignment = "Assignment 3_ Basic Java coding & JUnit"
        report_name = "report_A3_full.txt"
        students = ['student_gtID1', 'student_gtID2', 'student_gtID3']

        self.generate_report_for_assignment(assignment, deadline, report_name, students)
```

Run it from the command line like this:
```
python -m unittest test_submissions.TestSubmissions.test_generate_A3_report
```

# Issues
Open an issue in GitHub, DM me on Slack, or raise an issue with the instructors group. Feedback is welcome.