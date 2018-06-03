# ta_tools
Use TA tools to automate the downloading of Student Repos, originally created for CS 6300.
This will download GitHub repos for students in bulk, parse through submission text for commit IDs, try to check them out, then get information about timestamps from T-Square and GitHub and compare them against a deadline.

## Info
For the purposes of this project, the assignment code is a two letter code AX or TX where A is an individual assignment and T is a team assignment. The second character is the number of the assignment.

## Dependencies
1. Python 2.7 or 3.X
2. Command line access (Windows/Bash/Zsh)
3. Student data: students_full.txt, student_records.json, student_aliases.json

## Recommend
* Pycharm IDE or any other Python IDE

### Individual Project Additional Dependencies
* The students you are grading in students_XX_.txt where XX is the assignment number.

### Group Project Additional Dependencies
* The teams you are grading in team.txt, student_records_team_members.json, student_record_teams.json

# Initial Setup
1. Clone this repo to your machine
2. Download the student info from Google Drive; extract to this folder
3. Optional: you may want to set your GitHub credentials to last longer so you only have to enter them once. Here's a way to do that from the command line (timeout is in seconds):
  * Most Git confirmations are located at "$HOME/.gitconfig" if you want to view that and edit them.

```
    git config --global credential.helper "cache --timeout=300"
```

# Workflow
1. Download the 'student submission text' submissions from T-Square in bulk.
2. Extract the file to the 'submissions' folder (technically it can go anywhere, but I like to keep these in one place)
3. Set up your assignment for grading by adding/modifying a current entry (see Usage section for specifics)
4. Open the command line and call download_submission.py with the assignment code.
5. Authenticate with GitHub and let the scripts run
6. View output in console or the report file (both have the same output)
7. Start grading!

# Usage
When you set up a new assignment for grading, you'll need these 2 things:
1. Deadline (This is in UTC time (as Python 2.X doesn't handle timezones) and written in ISO format 'YYYY-MM-DD HH:MM:SS')
2. Assignment name (this is the same as the folder you extracted into 'submissions')
3. (Optional) Your list of students to grade. If you don't specify a list, it'll download repos for the whole class.

The fastest way to get the students list is to copy all your students from the Gradebook and paste them into a text file called students_XX.txt.
The students should be their T-Square ID names with newlines between them and nothing else.

Create/modify the python dictionary in download_submission.py
```
        'A2': {
          'deadline' : '2017-09-02 12:05:00',
          'assignment_name' : 'Assignment 2 Git usage'
          },
```
Be mindful of the commas and curly braces so when inserting this code, this remains to be a valid Python dictionary.

Run it from the command line like this:
```
    ./download_submission.py XX where XX is the assignment code.
```

Assignment codes are: A1 to A7 for assignments, I1 to I4 for the Individual Project. Example:
 ```
    ./download_submission.py A3
```

# Group Projects
ta_tools supports group projects, which takes in a list of teams as input, rather than student GT usernames, and will process submissions based on a single repo for each group. No additional configuration is necessary.

Full example, with convenience function:

```
        'D3': {
          'deadline' : '2017-10-14 12:05:00',
          'assignment_name' : 'Group Project, Deliverable 3',
          },
```

Here's an example of what your team.txt file contents might look like (shortened for convenience):
```
Team05
Team19
```

Reports will be separated by team for convenience, and still print late, missing and invalid commit information as well.

# Options
## Toggle pulling from GitHub: -p or --pull
You can opt out of pulling from GitHub, which speeds up processing older assignments. This will use the files already on your system, if they exist. Use the -p or --pull argument to control this (defaults to True).

Here's an example of how to used cached files (NOT pulling from GitHub) for A3:
```
    $ ./download_submission.py A3 -p False
```

## Create JSONs: -j or --json_create
If you need to update your JSON files (this is usually done only once or twice a semester), create a students_full.txt file and run with the -j input option. This will create student JSON files.

Example for individual students:
```
    $ ./download_submission.py A3 -j True
```

Example for teams (you've just got to run it on a team assignment, rather than an individual one):
```
   $ ./download_submission.py T2 -j True
```


# Issues
Open an issue in GitHub, message me on Slack, or raise an issue with the instructors group. Feedback is welcome.
