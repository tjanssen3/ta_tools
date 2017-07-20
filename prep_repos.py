import datetime
import json
import os
import re
import subprocess

class Submissions:
    def __init__(self):
        self.folder_prefix = "6300Summer17"
        self.git_context = "gt-omscs-se-2017summer"
        self.student_records_filename = "student_records.json"
        self.student_alias_filename = "student_aliases.json"
        self.datetime_format = "%Y-%m-%d %H:%M:%S"
        self.pull_from_github = True

    def create_student_json(self, input_file_name):
        try:
            with open(input_file_name, 'r') as input_file:
                gt_ids = {}
                students = {}
                for line in input_file:
                    line = line.strip()
                    parsed = line.split('\t')

                    name = parsed[0]
                    gt_id = parsed[1]
                    t_square_id = parsed[2]

                    students[t_square_id] = {}
                    students[t_square_id]['name'] = name
                    students[t_square_id]['gt_id'] = gt_id

                    gt_ids[gt_id] = t_square_id

            # save here
            with open(self.student_records_filename, 'w') as output_file:
                json.dump(students, output_file)
            with open(self.student_alias_filename, 'w') as alias_file:
                json.dump(gt_ids, alias_file)
        except IOError:
            print 'create_student_json: couldn\'t find file with name %s. Exiting.'
            raise IOError

    def prep_repos(self, submission_folder_name, deadline, whitelist=None):
        assignment_alias = submission_folder_name.split('/')[len(submission_folder_name.split('/')) - 1]

        if not os.path.isdir("Repos"):
            os.makedirs("Repos")

        if not os.path.isdir(submission_folder_name):
            print "Submission folder name '%s' not found. Exiting" % submission_folder_name
            return

        try:
            students = None

            with open(self.student_records_filename, 'r+') as student_records_file:
                students = json.load(student_records_file)

                for folder in os.listdir(submission_folder_name):

                    # Check for hidden .DS_Store file in MacOS
                    if str(folder) == ".DS_Store":
                        continue    

                    parsed = folder.split('(')
                    name = parsed[0]
                    t_square_id = parsed[1].strip(')')

                    try:
                        current_student = students[t_square_id]
                    except KeyError:  # also pulls in TAs, who won't be in students records file
                        continue

                    if whitelist != None and current_student['gt_id'] not in whitelist:
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
                    if self.commit_id_present(current_student[assignment_alias]['commitID']):
                        # try to check out commit ID
                        current_student = self.check_commit_ID(current_student, assignment_alias)

                        current_student = self.check_timestamp_github(current_student, assignment_alias, deadline)

                    # check T-Square timestamp against deadline
                    current_student = self.check_timestamp_t_square(current_student, assignment_alias, deadline)

                    # save info
                    students[t_square_id] = current_student

            if students != None:
                # save info
                with open(self.student_records_filename, 'w') as output_file:
                    json.dump(students, output_file)

        except IOError:
            print 'prep_repos couldn\'t find student records file. Run create_student_json first.'
            raise IOError

    def check_submission_file(self, current_student, t_square_id, submission_folder_name, folder, assignment_alias):
        try:
            submission_file = "%s(%s)_submissionText.html" % (current_student['name'], t_square_id)
            with open(os.path.join(submission_folder_name, folder, submission_file), 'r') as submission_info:
                strings = re.findall(r'([0-9A-Za-z]{40})', submission_info.read())
                if len(strings) == 0:
                    current_student[assignment_alias]['commitID'] = "Invalid"
                else:
                    current_student[assignment_alias]['commitID'] = strings[0]  # tiebreak: use first in list
        except IOError:
            current_student[assignment_alias]['commitID'] = "Missing"

        return current_student

    def check_timestamp_file(self, current_student, submission_folder_name, folder, assignment_alias):
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
        if not os.path.isdir("./Repos/%s%s" % (self.folder_prefix, current_student['gt_id'])):
            command = "cd Repos; git clone https://github.gatech.edu/%s/%s%s.git; cd .." % (
            self.git_context, self.folder_prefix, current_student['gt_id'])
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=None, shell=True)
            output = process.communicate()[0]

        # revert any local changes and pull from remote
        try:
                command_setup = "cd Repos/%s%s; git clean -fd; git reset --hard HEAD; git checkout .;" % (
                self.folder_prefix, current_student['gt_id'])

                if self.pull_from_github:
                    command_setup += "git pull;"

                output_clear = subprocess.check_output(command_setup, shell=True)
        except subprocess.CalledProcessError, e:
            print '%s subprocess.CalledProcessError:' % (current_student['gt_id'])
            try:
                print str(e.output)
            except UnicodeDecodeError:
                print 'UnicodeDecodeError'

    def check_timestamp_github(self, current_student, assignment_alias, deadline):
        if not current_student[assignment_alias]['commitID valid']:
            current_student[assignment_alias]['Submission GitHub'] = 'N/A'
            current_student[assignment_alias]['Timestamp GitHub'] = 'N/A'
        else:
            # check timestamp of GitHub commit
            command_timestamp = "cd Repos/" + self.folder_prefix + current_student[
                'gt_id'] + "; git show -s --format=%ci " + current_student[assignment_alias]['commitID'] + "; cd -"
            output_timestamp = subprocess.check_output(command_timestamp, shell=True)

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
                current_student[assignment_alias]['Submission GitHub'] = 'ok'
            else:
                current_student[assignment_alias]['Submission GitHub'] = 'late'

        return current_student

    def check_timestamp_t_square(self, current_student, assignment_alias, deadline):
        if current_student[assignment_alias]['Timestamp T-Square'] != 'Missing':
            temp = current_student[assignment_alias]['Timestamp T-Square']
            timestamp_t_square = temp[0:4] + '-' + temp[4:6] + '-' + temp[6:8] + ' ' \
                                 + temp[8:10] + ':' + temp[10:12] + ':' + temp[12:14]
            current_student[assignment_alias]['Timestamp T-Square'] = timestamp_t_square
            if timestamp_t_square <= deadline:
                current_student[assignment_alias]['Submission T-Square'] = 'ok'
            else:
                current_student[assignment_alias]['Submission T-Square'] = 'late'

        return current_student

    def check_commit_ID(self, current_student, assignment_alias):
        command_checkout = "cd Repos/" + self.folder_prefix + current_student['gt_id'] + ";" + "git checkout " + \
                           current_student[assignment_alias]['commitID'] + "; git log --pretty=format:'%H' -n 1; cd -"
        output_checkout = subprocess.check_output(command_checkout, shell=True)

        commit = output_checkout.split('/')[0]
        current_student[assignment_alias]['commitID valid'] = commit == current_student[assignment_alias]['commitID']

        return current_student

    def generate_report(self, assignment, students=[], report_name=None):
        print 'Report: %s\n' % assignment
        try:
            student_aliases = None  # scope
            with open(self.student_alias_filename, 'r') as alias_file:
                student_aliases = json.load(alias_file)

            student_records = None  # scope
            with open(self.student_records_filename, 'r') as records_file:
                student_records = json.load(records_file)

            if students == None or len(students) == 0:
                students = student_aliases.keys()  # all students!

            late_github = []
            late_t_square = []
            missing = []
            bad_commit = []

            file_object = None
            
            if report_name != None:
                file_object = open(report_name, 'w')

            for student in students:
                t_square_id = student_aliases[student]
                student_info = student_records[t_square_id]

                self.print_to_file_and_console(student, file_object)
                if assignment not in student_info:
                    self.print_to_file_and_console('\tNo records found', file_object)
                    missing.append(student)
                    continue

                for key in reversed(sorted(student_info[assignment].keys())):
                    self.print_to_file_and_console('\t%s: %s' % (key, student_info[assignment][key]), file_object)

                    if key == 'Submission GitHub' and student_info[assignment][key] == 'late':
                        late_github.append(student)

                    if key == 'Submission T-Square' and student_info[assignment][key] == 'late':
                        late_t_square.append(student)

                    if key == 'commitID' and student_info[assignment][key] == 'Missing':
                        missing.append(student)

                    if key == 'commitID valid' and student_info[assignment][key] == False:
                        bad_commit.append(student)

            self.print_to_file_and_console('\nLATE SUBMISSIONS:', file_object)
            self.print_to_file_and_console('\tT-Square (%s): ' % len(late_t_square) + ', '.join(sorted(late_t_square)), file_object)
            self.print_to_file_and_console('\tGitHub (%s): ' % len(late_github) + ', '.join(sorted(late_github)), file_object)
            self.print_to_file_and_console('\nMISSING SUBMISSIONS (%s):' % len(missing), file_object)
            self.print_to_file_and_console('\t' + ', '.join(sorted(missing)), file_object)
            self.print_to_file_and_console('\nBAD COMMITS (%s):\n\t' % len(bad_commit) + ', '.join(sorted(bad_commit)), file_object)

            if file_object != None:
                file_object.close()
        except IOError:
            print 'generate_report couldn\'t find %s file. Try running create_student_json first.' % self.student_alias_filename
            raise IOError

    def print_to_file_and_console(self, text, file_object):
        print text
        if file_object != None:
            file_object.write(text + "\n")

    def commit_id_present(self, commitID_message):
        return commitID_message != 'Invalid' and commitID_message != 'Missing'