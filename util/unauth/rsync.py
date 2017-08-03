#!/usr/bin/env python
# coding=utf-8

import pexpect
import logging
import sys
from colorama import *


logging.basicConfig(level=logging.INFO, format="%(funcName)s[^^]%(lineno)d: %(message)s")

def rsyncDetect(ip, port=873):

    rsync_cmd1 = "rsync {0}::".format(ip)
    child = pexpect.spawn(rsync_cmd1)
    first_line = ""
    index = child.expect(["@ERROR","rsync: ", "\S+[a-zA-Z0-9\.\\-_]+", pexpect.EOF, pexpect.TIMEOUT])
    if index <= 1:
        logging.info(Fore.RED + "{0}::{1} unauth detect failed.".format(ip, port) + Style.RESET_ALL)
    elif index == 2:
        first_line = child.after

    elif index == 3:
        logging.info(Fore.RED + "{0}::{1} no content.".format(ip, port) + Style.RESET_ALL)
    else:
        logging.info(Fore.RED + "{0}::{1} timeout.".format(ip, port) + Style.RESET_ALL)

    rsync_cmd2 = "rsync {0}::{1}".format(ip, first_line)
    print rsync_cmd2
    child = pexpect.spawn(rsync_cmd2)
    index = child.expect(["@ERROR", "rsync: ","Password", "\S+[a-zA-Z0-9\.\\-_]+", pexpect.EOF, pexpect.TIMEOUT])
    child.logfile_read = sys.stdout
    if index <= 1:
        logging.info(Fore.RED + "{0}::{1} unauth detect failed. REASON: {2}".format(ip, port, str(child.after)) + Style.RESET_ALL)

    elif index == 2:
        logging.info(Fore.YELLOW + "{0}::{1} found password".format(ip, port) + Style.RESET_ALL)
        child.sendline("rsync")
        with open("rsync_password.txt", "a") as f:
            f.write(ip + ":" + str(port) + "\n")
        index = child.expect(['\s+@ERROR', r"\S+\s+\\n", pexpect.EOF, pexpect.TIMEOUT])
        if index == 1:
            with open("rsync_vu1n.txt", "a") as f:
                f.write(ip + ":" + str(port) + "\n")
            logging.info("find one")
        else:
            logging.info("not found")

    elif index == 3:
        with open("rsync_vu1n.txt", "a") as f:
            f.write(ip + ":" + str(port) + "\n")
        logging.info(Fore.GREEN + "{0}::{1} VULNERABLE!!.".format(ip, port) + Style.RESET_ALL)



if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "python rsync.py filename"
        exit(0)
    filename = sys.argv[1]
    with open(filename, "r") as f:
        for line in f:
            ip = line.strip()
            rsyncDetect(ip)



