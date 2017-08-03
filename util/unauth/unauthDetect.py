#!/usr/bin/env python
# -*- coding=utf-8 -*-

import logging
import threading
import pymongo
import redis
import pexpect
import sys
import socket
import Queue
from colorama import *

# for now keep the logger. when everything is done, use only one logger or simply remove it
logging.basicConfig(format="%(filename)s^^^%(funcName)s:\t%(message)s", level=logging.INFO)
lock = threading.Lock()
socket.setdefaulttimeout(30)

"""
# To Debug, Now It Useless
def writeResult(content):
    lock.acquire()
    with open("vu1n_list.lst", "a") as f:
        f.write(content + "\n")
    lock.release()
"""

class unauthDetect(threading.Thread):
    """docstring for unauthDetect"""
    def __init__(self, inqueue, outqueue):
        threading.Thread.__init__(self)
        self.inqueue = inqueue
        self.outqueue = outqueue

    def run(self):
        while True:
            if self.inqueue.empty():
                break
            # 
            try:
                try:
                    _ = self.inqueue.get(timeout=1)
                except Exception as e:
                    break

                if ":" in _:
                    host, port = _.split(":")[0], _.split(":")[1]
                else:
                    host = _
                    port = "0"
                if str(port) == "6379":
                    self.redisDetect(host, int(port))
                elif str(port) == "27017":
                    self.mongoDetect(host, int(port))
                elif str(port) == "873":
                    self.rsyncDetect(host, int(port))
                else:
                    self.redisDetect(host)
                    self.mongoDetect(host)
                    self.rsyncDetect(host)
            except KeyboardInterrupt as e:
                logging.info("User Keyboard.")
                break
            except Exception as e:
                logging.error(str(e))


    def redisDetect(self, host, port=6379):
        try:
            r = redis.Redis(host=host, port=port, socket_timeout=20)
            if "redis_version" not in r.info():
                logging.info(Fore.RED + "[Failed] [Redis Unath Access]  {0}:{1}".format(host, port) + Style.RESET_ALL)
            else:
                logging.info(Fore.GREEN + "[Successed] [Redis Unath Access]   {0}:{1}".format(host, port) + Style.RESET_ALL)
                # writeResult(host + ":" + port)
                target = "redis://{}:{}".format(host, port)
                type = "unauth"
                info = "Redis Unauth Detect Maybe"
                _ = {'target': target, 'type' : type, 'info' : info}
                self.outqueue.put(_)
        except Exception as e:
            logging.info(Fore.RED + "{0}:{1} Failed Redis Detect".format(host, port) + Style.RESET_ALL)

    def mongoDetect(self, host, port=27017):
        try:
            r = pymongo.MongoClient(host=host, port=port)
            server_info = r.server_info()
            if "version" in server_info:
                logging.info(Fore.GREEN + "[Successed] [Mongo Unath Access]    {0}:{1}".format(host, port) + Style.RESET_ALL)
                # writeResult(host + ":" + port)
                target = 'mongo://{}:{}'.format(host, port)
                type = "unauth"
                info = "Mongodb Unauth Detect Maybe"
                _ = {'target': target, 'type' : type, 'info' : info}
                self.outqueue.put(_)
            else:
                logging.info(Fore.RED + "[Failed] [Mongo Unath Access]    {0}:{1}".format(host, port) + Style.RESET_ALL)
        except Exception as e:
            pass
            # logging.info(Fore.RED + "{0}:{1} Failed Mongo Detect".format(host, port) + Style.RESET_ALL)


    def rsyncDetect(self, ip, port=873):

        rsync_cmd1 = "rsync {0}:: --port={1}".format(ip, port)
        child = pexpect.spawn(rsync_cmd1)
        first_line = ""
        index = child.expect(["@ERROR", "rsync: failed", "\S+\s.", pexpect.EOF, pexpect.TIMEOUT])
        if index == 0 or index == 1:
            logging.info(Fore.RED + "[Failed] [rsync Unath Access] {0}::{1} unauth detect failed.".format(ip, port) + Style.RESET_ALL)
            return
        elif index == 2:
            first_line = child.after

        elif index == 3:
            # logging.info(Fore.RED + "{0}::{1} no content.".format(ip, port) + Style.RESET_ALL)
            return 
        else:
            # logging.info(Fore.RED + "{0}::{1} timeout.".format(ip, port) + Style.RESET_ALL)
            return

        rsync_cmd2 = "rsync {0}::{1} --port={2}".format(ip, first_line, port)
        child = pexpect.spawn(rsync_cmd2)

        index = child.expect(["@ERROR","rsync: failed", "Password", "\S+\s+", pexpect.EOF, pexpect.TIMEOUT])
        child.logfile_read = sys.stdout
        if index == 0 or index == 1:
            logging.info(Fore.RED + "[Failed] [rsync Unath Access] {0}::{1}   REASON: {2}".format(ip, port, str(child.after)) + Style.RESET_ALL)
            return
        elif index == 2:
            # logging.info(Fore.YELLOW + "{0}::{1} found password".format(ip, port) + Style.RESET_ALL)
            child.sendline("admin")
            lock.acquire()
            with open("rsync_password.txt", "a") as f:
                f.write(ip + ":" + str(port) + "\n")
            lock.release()
            index = child.expect(['\s+@ERROR', r"\S+\s+\\n", pexpect.EOF, pexpect.TIMEOUT])
            if index == 1:
                # writeResult(host + ":" + port)
                target = "rsync://{}:{}".format(host, port)
                type = 'unauth'
                info = "Rsync Unauth Detect Maybe"
                _ = {'target' : target, 'type' : type, 'info': info}
                self.outqueue.put(_)
                logging.info(Fore.GREEN + "[Successed] [rsync Unath Access] {0}:{1}".format(ip, port) + Style.RESET_ALL)
            else:
                logging.info(Fore.RED + "[Failed] [rsync Unath Access] {0}:{1}".format(ip, port) + Style.RESET_ALL)

        elif index == 3:
            # writeResult(host + ":" + port)
            target = "rsync://{}:{}".format(host, port)
            type = 'unauth'
            info = "Rsync Unauth Detect Maybe"
            _ = {'target' : target, 'type' : type, 'info': info}
            self.outqueue.put(_)
            logging.info(Fore.GREEN + "[Successed] [rsync Unath Access] {0}:{1}".format(ip, port) + Style.RESET_ALL)
        else:
            logging.info(Fore.RED + "[Failed] [rsync Unath Access] {0}:{1}".format(ip, port) + Style.RESET_ALL)
    

def runUnauthDetect(inqueue, outqueue, thread_num=50):
    # data: 17-06-23 update
    # 先写成阻塞的，下次版本再改成守护模式+while循环的
    try:
        threads = []
        for i in range(thread_num):
            thd = unauthDetect(inqueue, outqueue)
            threads.append(thd)
        for thd in threads:
            thd.start()

        for thd in threads:
            if thd.is_alive():
                thd.join()
    except KeyboardInterrupt as e:
        # 如果不改成设置守护线程，这里没有用
        # logging.info("[-] User KeyboradInterrup Here..")
        try:
            while True:
                inqueue.get_nowait()
        except Exception as e:
            pass
    except Exception as e:
        logging.info("[-] Error Happend:\t Reason: {0}".format(str(e)))

    # turn queue into list, for extend with main process
    result = []
    while not outqueue.empty():
        _ = outqueue.get()
        result.append(_)
    return result

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "python {0} filename".format(sys.argv[0])
        sys.exit(-1)

    inqueue = Queue.Queue()
    outqueue = Queue.Queue()
    with open(sys.argv[1], "r") as f:
        for line in f:
            ip = line.strip()
            inqueue.put(ip)

    # 多线程处理此例
    try:
        threads = []
        for i in range(50):
            thd = unauthDetect(inqueue, outqueue)
            threads.append(thd)

        for thd in threads:
            thd.start()

        for thd in threads:
            if thd.is_alive():
                thd.join()
        print "--------------------------"
    except KeyboardInterrupt as e:
        logging.info("User Keyboard Main Thread")
        try:
            while True:
                inqueue.get_nowait()
        except:
            pass

    while True:
        if outqueue.empty():
            break
        _ = outqueue.get()
        logging.info(Fore.GREEN + "{0[2]}^^{0[0]}:{0[1]}\t May Vulnerable".format(_) + Style.RESET_ALL)

    print "Done"
