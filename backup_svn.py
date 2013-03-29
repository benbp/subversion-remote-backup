#!/usr/bin/env python
"""
This script uses hot-backup.py (from the svn trunk) to locally back up all repos within
a subversion directory, and then transfers backups to a remote server via sftp

TODO:
    -- Create a logging object and handler so that a maximum log file size
        can be set, double check to make sure that this works with paramiko logging
    -- Figure out error handling for these remote operations,
    e.g., getting a socket.error, etc.
"""

import re, logging, paramiko
from os import listdir
from subprocess import check_output

backup_server = '<server_ssh_address>'
backup_usr = '<username>'
backup_pwd = '<password>'

# Make sure path variables end in '/', so that they form proper
# file paths when concatenated with os.listdir() list items
repo_dir = "<dir_of_repos_to_back_up>"
backup_dir = "<local_dir_to_place_backups>"
remote_backup_dir = "/home/%s/" % backup_usr
log_path = "<path_to_log_file>"

# hot-backup.py will store X backups
num_backups = "3"
# available archive formats: bz2, gz, zip, zip64 (for files > 2gb)
archive_type = "gz"

logging.basicConfig(level=logging.DEBUG, filename=log_path, filemode='a',
        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
        datafmt='%H:%M:%S')

current_backup_repos = []
deleted_backup_repos = []

# hot backup all repos within the repo directory
for dir in listdir(repo_dir):
    if dir[0] != ".":
        try:
            msg = check_output(["hot-backup.py",
            "--archive-type=%s" % archive_type,
                    "--num-backups=%s" % num_backups,
            repo_dir + dir, backup_dir])
            logging.info(msg)
            repo = re.search("\'(.*\.%s)\'" % archive_type, msg)
            # Store 2 item tuples in current_backup_repos, item 0 is the full
            # file path and item 1 is just the filename, this enables proper
            # sftp put below
            current_backup_repos.append((repo.group(1), repo.group(1).split('/')[-1]))
            del_repos = re.findall("Removing.*\/(.*%s)" % archive_type, msg)
            for deleted in del_repos:
                deleted_backup_repos.append(deleted)
        except Exception, e:
            logging.exception(e)

ssh = paramiko.SSHClient()
# Auto add public key. Remove this if connecting to unknown servers
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(backup_server, username=backup_usr, password=backup_pwd)
sftp = ssh.open_sftp()
for to_backup in current_backup_repos:
    try:
        sftp.put(to_backup[0], remote_backup_dir + to_backup[1])
    except Exception, e:
        logging.exception(e)
for to_delete in deleted_backup_repos:
    try:
        # return variables captured for expandibility
        stdin, stdout, stderr = ssh.exec_command("rm %s" % remote_backup_dir + to_delete)
    except:
        logging.exception(e)
sftp.close()
ssh.close()
