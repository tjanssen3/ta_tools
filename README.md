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
2) Download the student info from Google Drive; extract to this folder (git will ignore those files)
3) Optional: you may want to set your GitHub credentials to last longer so you only have to enter them once. Here's a way to do that from the command line (timeout is in seconds): 
```
    git config --global credential.helper "cache --timeout=300"
```

# Workflow
1) Download the 'student submission text' submissions from T-Square in bulk
2) Extract the file to the 'submissions' folder (technically it can go anywhere, but I like to keep these in one place)
3) Set up your assignment for grading with a new function (see Usage section for specifics) 
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

The fastest way to get the students list is to copy all your students from the Gradebook and paste them into a text file, then call get_students_list_from_file(<your_filename>). This will create that list for you.  

Create a new function like this in test_submissions.py:
```
    def test_generate_A3_report_individual(self):
        deadline = "2017-06-03 12:05:00"  # EST + 4 hours = UTC, which is the T-Square deadline
        assignment = "Assignment 3_ Basic Java coding & JUnit"
        report_name = "report_A3_full.txt"
        students = self.get_students_list_from_file('students_A3.txt')

        self.generate_report_for_assignment(assignment, deadline, report_name, students)
```

Run it from the command line like this:
```
    python -m unittest test_submissions.TestSubmissions.test_generate_A3_report_individual
```

# Issues
Open an issue in GitHub, message me on Slack, or raise an issue with the instructors group. Feedback is welcome.
