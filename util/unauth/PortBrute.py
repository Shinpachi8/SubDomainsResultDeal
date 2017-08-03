#!/usr/bin/env python
# -*- coding=utf-8 -*-

__author__ = 'Shinpach8'

import logging
import Queue
import time
import threading
import socket
import paramiko
from ftplib import FTP
import MySQLdb

# for now , keep it. when every thing is done. use only one logging or simply remove it.
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s^^%(lineno)d:\t%(message)s')

class FTPBrute(object):
    """
    FTP Weak Password Brute
    Result Format: [FTP] user:passwd
    Default Threads: 15
    """
    def __init__(self, host=None, ufile=None, pfile=None, timeout=10, resultQueue=None):
        self.host = host
        self.ufile = ufile
        self.is_exit = False
        self.pfile = pfile
        self.timeout = timeout
        self.targetQueue = Queue.Queue()
        self.result = resultQueue # 返回结果
    
    def get_Queue(self):
        _users = []
        _pass = []
        with open(self.ufile, "r") as f:
            _users = f.readlines()
        with open(self.pfile, "r") as f:
            _pass = f.readlines()
        
        for _u in _users:
            for _p in _pass:
                _u = _u.strip()
                _p = _p.strip()
                self.targetQueue.put(_u + ":" + _p)
    
    def thread(self):
        while not self.targetQueue.empty():
            if self.is_exit:
                break
            name,pwd = self.targetQueue.get().split(':')
            try:
                ftp = FTP()
                ftp.connect(self.host, 21, self.timeout)
                ftp.login(name, pwd)
                time.sleep(0.05)
                ftp.quit()
                s = "[FTP unatuh access][%s] %s:%s" % (self.host, name,pwd)
                # todo:// logging
                self.result.put(s)
            except socket.timeout:
                # todo:// logging
                self.targetQueue.put(name + ':' + pwd)
                time.sleep(1)
            except Exception, e:
                error = "[Error] %s:%s" % (name,pwd)
                # todo:// logging
                pass
    def run(self):
        self.get_Queue()
        starttime = time.time()
        
        threads = []
        for x in xrange(15):
            th = threading.Thread(target=self.thread)
            threads.append(th)
            th.setDaemon(True)
            th.start()
        
        try:
            while True:
                if self.targetQueue.empty():
                    break
                else:
                    time.sleep(1)
        except KeyboardInterrupt:
            self.is_exit = True
            # todo://logging
        endTime = time.time()
        print "[FTP Brute] Used timd: %f" %(endTime - starttime)


class SSHBrute(object):
    """
    SSH Weak Password Brute
    Result Format: [SSH] user:passwd
    Default Threads: 15
    """
    def __init__(self, host=None, ufile=None, pfile=None, timeout=10, resultQueue=None):
        self.host = host
        self.ufile = ufile
        self.pfile = pfile
        self.timeout = timeout
        self.targetQueue = Queue.Queue()
        self.result = resultQueue # 返回结果
        self.is_exit = False
    
    def get_Queue(self):
        _users = []
        _pass = []
        with open(self.ufile, "r") as f:
            _users = f.readlines()
        with open(self.pfile, "r") as f:
            _pass = f.readlines()
        
        for _u in _users:
            for _p in _pass:
                _u = _u.strip()
                _p = _p.strip()
                self.targetQueue.put(_u + ":" + _p)
    
    def thread(self):
        while not self.targetQueue.empty():
            if self.is_exit:
                break
            name,pwd = self.targetQueue.get().split(':')
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(hostname=self.host,port=22,username=name,password=pwd,timeout=self.timeout)
                time.sleep(0.05)
                ssh.close()
                s = "[SSH][%s] %s:%s" % (self.host, name,pwd)
                # todo:// logging
                self.result.put(s)
            except socket.timeout:
                # todo:// logging
                self.targetQueue.put(name + ':' + pwd)
                time.sleep(3)
            except Exception, e:
                error = "[Error] %s:%s" % (name,pwd)
                # todo:// logging
                pass
    def run(self):
        self.get_Queue()
        starttime = time.time()
        
        threads = []
        for x in xrange(15):
            th = threading.Thread(target=self.thread)
            threads.append(th)
            th.setDaemon(True)
            th.start()
        
        try:
            while True:
                if self.targetQueue.empty():
                    break
                else:
                    time.sleep(1)
        except KeyboardInterrupt:
            self.is_exit = True
            # todo://logging
        endTime = time.time()
        print "[SSH Brute] Used timd: %f" %(endTime - starttime)

        
class MySQLBrute(object):
    """
    MySQL Weak Password Brute
    Result Format: [MySQL] user:passwd
    Default Threads: 15
    """
    def __init__(self, host=None, ufile=None, pfile=None, timeout=10, resultQueue=None):
        self.host = host
        self.ufile = ufile
        self.pfile = pfile
        self.timeout = timeout
        self.targetQueue = Queue.Queue()
        self.result = resultQueue # 返回结果
        self.is_exit = False
    
    def get_Queue(self):
        _users = []
        _pass = []
        with open(self.ufile, "r") as f:
            _users = f.readlines()
        with open(self.pfile, "r") as f:
            _pass = f.readlines()
        
        for _u in _users:
            for _p in _pass:
                _u = _u.strip()
                _p = _p.strip()
                self.targetQueue.put(_u + ":" + _p)
    
    def thread(self):
        while not self.targetQueue.empty():
            if self.is_exit:
                break
            name,pwd = self.targetQueue.get().split(':')
            try:
                conn = MySQLdb.connect(host=self.host, user=name, passwd=pwd, db='mysql', port=3306)
                if conn:
                    # time.sleep(0.05)
                    conn.close()
                s = "[MySQL][%s] %s:%s" % (self.host, name,pwd)
                logging.info(s)
                # todo:// logging
                self.result.put(s)
            except socket.timeout:
                # todo://logging
                e = "[MySQL Brute]%s\t %s:%s\t TimeOut" % (self.host, name, pwd)
                logging.info(e)
                self.targetQueue.put(name + ':' + pwd)
                time.sleep(3)
            except Exception, e:
                #error = "[MySQL Brute]%s\t %s:%s\t Error" % (self.host, name,pwd)
                #logging.error(error)
                # todo://logging
                pass
    def run(self):
        self.get_Queue()
        starttime = time.time()
        
        threads = []
        for x in xrange(15):
            th = threading.Thread(target=self.thread)
            threads.append(th)
            th.setDaemon(True)
            th.start()
        
        try:
            while True:
                if self.targetQueue.empty():
                    break
                else:
                    time.sleep(1)
        except KeyboardInterrupt:
            self.is_exit = True
            # todo://logging
        endTime = time.time()
        print "[MySQL Brute] Used timd: %f" %(endTime - starttime)        
 

"""
 if __name__ == '__main__':
    ufile = Queue.Queue()
    pfile = Queue.Queue()
    resultQueue = Queue.Queue()


    with open("target.list", "r") as f:
        for ip in f.xreadlines():
            ip = ip.strip()
            _ = MySQLBrute(host=ip, ufile=ufile, pfile=pfile, resultQueue=resultQueue)
"""
