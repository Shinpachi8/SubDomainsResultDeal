#! /usr/bin/env python2
# coding=utf-8

import threading
import re
import urllib2  # can from urllib2 import urlopen. Request
import sqlite3
import urlparse
import logging
import argparse
import sys
import chardet
import Queue

from bs4 import BeautifulSoup
from time import ctime


lock = threading.Lock()
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", help="the url to start")
    parser.add_argument("-d", default=3, help="the deepth want to crawl")
    parser.add_argument("-l", default=3, help=("log level,"
        "the bigger, the more"))
    parser.add_argument("-f", default="spider.log", help="file to save log")
    parser.add_argument("--thread", default=10, help="the thead number, default 10")
    parser.add_argument("--dbfile", help="db file to save result")
    parser.add_argument("--key", default="", help="the keyword that html contain")
    args = parser.parse_args()
    return args


class db_deal(object):
    """
    this class is about deal
    the db operation
    """
    def __init__(self, path, table, logger):
        """
        create the db
        and set the cursor
        """
        try:
            self.conn = sqlite3.connect(path)
            self.cur = self.conn.cursor()
            self.table = table
            self.logger = logger
        except Exception as e:
            self.logger.error(str(e))
            print "connect/cur error for reason {}".format(str(e))

    def create_db(self):
        """
        create table in db
        each crawl has a special table
        """
        try:
            self.cur.execute(("CREATE TABLE IF NOT EXISTS {} (id INTEGER PRIMARY "
                "KEY AUTOINCREMENT,Data VERCHAR(40), "
                "url VARCHAR(50))").format(self.table))
            self.conn.commit()
            self.logger.info("create table Done")
            print "create table done!"
        except Exception as e:
            self.logger.error(str(e))
            print "create table error the reason is {}".format(str(e))

    def insert_data(self, data):
        try:
            self.cur.execute(("insert into {}(Data, url) "
                "values (?, ?)").format(self.table), data)
            self.conn.commit()
            self.logger.info("insert to table Done")
            print "insert Done!"
        except Exception as e:
            self.logger.error(str(e))
            print "insert data error.  the reason is {}".format(str(e))

    def close(self):
        self.conn.close()
        self.logger.info("close the database")

class Crawl(object):
    """ the main project of the spider
    """
    def __init__(self, threadpool, args, table, logger):
        self.tp = threadpool
        self.args = args
        self.url = args.u
        self.domain = urlparse.urlparse(self.url)
        self.deep = args.d
        self.table = table
        self.key = args.key
        self.path = args.dbfile
        self.header = {"User-Agent":("Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36")}
        self.logger = logger
        self.visit = []

    def work(self, url, deep):
        # if url in self.visit:
        #     self.logger.info("the url in the visit list")
        #     return
        # else:

        #     self.visit.append(url)
        #     self.logger.info("append the url to the visited list")

        try:
            # urlopen did not have the headers attr
            request = urllib2.Request(url, headers=self.header)
            _ = urllib2.urlopen(request, timeout=5)
            if "text/html" not in _.headers["Content-Type"]:
                pass
            else:
                html = urllib2.urlopen(request).read()
                code_type = chardet.detect(html)["encoding"]
                if code_type.lower() == "gb2312":
                   code_type = "gbk"
                   html = html.decode(code_type)
                if code_type.lower() != "utf-8":
                   html = html.decode(code_type)

                self._parse_html(url, html, deep)
                self.logger.info("parser the url {}".format(url))
                print "[deep:{}]  [time:{}]  [url: {}]".format(deep, ctime(), url)
        except Exception as e:
            self.logger.error(str(e))
            print "right here lineno: 129"
            print "get {} error. reason is {}".format(url, str(e))

    def complet_url(self, url):
        if url.startswith("/"):
            return self.domain[0] + "://" + self.domain[1] + url
        else:
            return url



    def _parse_html(self, url, html, deep):
        """ parse the html and add the url to database"""

        # db = db_deal(self.path, self.table, self.logger)
        key_find = re.findall(r".*{}.*".format(self.key), html)
        if key_find:
            data = ctime()
            logging.info("findURL:{}".format(url))
            # db.insert_data((data, url))

        # get the list that contains <a>
        soup = BeautifulSoup(html, "html.parser")
        a_list = soup.find_all('a')

        # judge if the last loop
        if deep > 1:
            for i in a_list:
                if i.attrs.has_key("href"):
                    link = i.attrs["href"]
                    # 判断是否是目标网站
                    complet_link = self.complet_url(link.strip())
                    if not complet_link.startswith("java") and \
                        not complet_link.startswith("mailto") and \
                        _homology(domain_rage, complet_link):
                        self.tp.add_job(self.work, complet_link, deep-1)
                # if i["href"]:
                #     temp_url = i["href"]
                #     #print "[time:{}]  [url: {}]".format(ctime(), temp_url)
                #     if not temp_url.startswith("java") and not temp_url.startswith("mailto"):
                #         self.tp.add_job(self.work, temp_url, deep-1)
        else:
            for i in a_list:
                if i.attrs.has_key("href"):
                    link = i.attrs["href"]
                    temp_url = self.complet_url(link.strip())
                    #print "[time:{}]  [url: {}]".format(ctime(), temp_url)

                    # if want to be better ,can define url = i["href"]
                    if _homology(domain_rage, temp_url):
                        try:
                            request = urllib2.Request(temp_url, headers=self.header)
                            last_html = urllib2.urlopen(request).read()
                        except Exception as e:
                            self.logger.error(str(e))
                            print "get html error. the reason is {}".format(str(e))
                            return
                        if re.findall(r".*{}.*".format(self.key), last_html):
                            data = ctime()
                            logger.info("findURL:{}".format(temp_url))
                        # db.insert_data((data, i["href"]))

        # db.close()
    def start(self):
        """ start function"""
        if not self.url.startswith("http://"):
            self.url = "http://" + self.url

        self.tp.add_job(self.work, self.url, self.deep)
        self.tp.wait_for_complete()


class MyThread(threading.Thread):
    """ work thread"""
    def __init__(self, workQueue, timeout=3):
        threading.Thread.__init__(self)
        self.workQueue = workQueue
        self.timeout = timeout
        self.setDaemon(True)
        self.start()

    def run(self):
        while True:
            try:
                # TODO  线程锁定
                # lock.acquire()
                callable, args = self.workQueue.get(timeout=self.timeout)
                res = callable(*args)
                self.workQueue.task_done()
                # lock.release()
            # 队列空了就退出
            except Queue.Empty:
                break
            except Exception as e:
                print "callable error. the reason is {}".format(str(e))


class ThreadPool:
    """ write our own threadpool
    STEP1   首先确定线程数或固定或可变
    STEP2   初始化一个执行线程，包括队列，与线程列表
    STEP3   创建线程池，将每一个执行线程实例添加至列表中
    STEP4   判断是否所有线程都完成了。 ls_alive与Join函数
    STEP5   添加函数，将可执行的函数与其参数添加到工作队列中。


    """
    def __init__(self, num_of_thread):
        self.workQueue = Queue.Queue()
        self.threads = []
        self._createThreadPool(num_of_thread)

    def _createThreadPool(self, num_of_thread):
        for i in range(num_of_thread):
            thread = MyThread(self.workQueue)
            self.threads.append(thread)

    def wait_for_complete(self):
        while(len(self.threads)):
            thread = self.threads.pop()
            if thread.is_alive():
                thread.join()

    def add_job(self, callable, *args):
        self.workQueue.put((callable, args))



def my_log(level_num, filename):
    """
    create a logger case
    that can be use in anywhere
    """
    level_dict = {"1": "CRITICAL",
        "2": "ERROR",
        "3": "WARNING",
        "4": "INFO",
        "5": "DEBUG"}
    level = level_dict[level_num]
    log_format = ("%(filename)s [line:%(lineno)d] [time:%(asctime)s]"
        "[level:%(levelname)s] msg: %(message)s")
    logging.basicConfig(filename=filename,
        format = log_format, level = level)
    # logger_name = "example"
    logger = logging.getLogger()
    return logger


def _homology(domain, url):
    if domain in url:
        return True
    else:
        return False


if __name__ == '__main__':
    a = {"a":"test1", "b":"test2"}
    class args(object):
        """docstring for args"""
        def __init__(self, a):
            self.url = a["a"]
            self.full_scan = a["b"]

    print args(a).url


    # args = parse_args()
    # table = "test_table"
    # if not args.dbfile or not args.u :
    #     print "param error  usage: python knowsec-spider.py -h"
    #     exit(-1)
    # if not args.u.startswith("http"):
    #     print "i.e python {} -u http://www.iqiyi.com \n -u Must start with http://".format(sys.argv[0])
    #     exit(-1)
    # dbfile = args.dbfile
    # num_of_thread = args.thread
    # # 数据库不能在一个线程创建再另外一个线程进行插入和删除操作
    # # 同样的
    # logger = my_log(str(args.l), args.f)

    # db = db_deal(dbfile, table, logger)
    # db.create_db()
    # db.close()
    # # 得到URL的域名关键字
    # global domain_rage
    # netloc = urlparse.urlparse(args.u).netloc
    # domain_rage = netloc.split(".")[1] if "www" in netloc.split(".")[0] else netloc.split(".")[0]



    # threadpool = ThreadPool(num_of_thread)
    # Crawl(threadpool, args, table, logger).start()





    #logger.debug("test debug")
    # db = db_deal("test1.db", "test_table")
    # db.create_db()
    # db.insert_data(("10-14","http://www.baidu.com"))
