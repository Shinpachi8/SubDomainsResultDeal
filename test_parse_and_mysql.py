#!/usr/bin/env python
#coding=utf-8

import requests
import time
import sys
from bs4 import BeautifulSoup as bs
from util.parseTool import parseTool
#from util.MysqlTool import MysqlTool
from util.GetTitle2 import GetTitle
from util.GetIsp import GetIsp
import MySQLdb as mdb
from Queue import Queue
from util.MysqlTool import Save2MySQL
from util.plugin.20170904elasticsearch_rce import FuzzES
import threading
import json
import re
import logging

logging.getLogger("requests").setLevel(logging.WARNING)

# global config

host = "127.0.0.1"
port = 3307
dbuser = "root"
dbpassword = ""
db = "myipdb"

help =  """
        Usage:  python xx.py filename

        """




def main(host, port, dbuser, dbpassword, db, filename):
    #db = MysqlTool(host, port, dbuser, dbpassword)
    #db.execute("use myipdb;")
    conn = mdb.connect(host=host, port=port, user=dbuser, passwd=dbpassword, db=db)
    cursor = conn.cursor()
    result = parseTool.parse(filename)
    
    values = []
    ip_set = set()
    for i in result:
        ip = i[0]
        ip_set.add(ip)
    print len(ip_set)
    ip_queue = Queue()
    isp_queue = Queue()
    for ip in ip_set:
        ip_queue.put(ip)
    del ip_set
    # 多线程处理isp
    threads = []
    for i in xrange(60):
        thread = GetIsp(ip_queue, isp_queue)
        threads.append(thread)

    for thd in (threads):
        thd.start()

    for thd in threads:
        if thd.is_alive():
            thd.join()

    # insert or update myip table
    while True:
        if isp_queue.empty():
            break
        ip, isp = isp_queue.get()
        print "len(value):{0} \t ip:{1} \t isp:{2}".format((isp_queue.qsize()), ip, isp)
        try:
            count = cursor.execute("SELECT * FROM myip WHERE ip = '{0}'".format(ip))
            if count:
                tmp = cursor.fetchone()
                if tmp == isp:
                    continue
                else:
                    count = cursor.execute("UPDATE myip set isp = '%s' WHERE id=%d" %(isp, tmp[0]))
                    print "[+] UPDATE success!!!"
            else:
                count = cursor.execute("INSERT myip (ip, isp, company) value (%s, %s, %s)", [ip, isp, 'iqiyi'])
                print "[+] INSERT success!!!"
            conn.commit()
        except Exception as e:
            print str(e)
            conn.rollback()
   
    # parse port and save it to mysql
    data = []
    port_queue = Queue()
    title_queue = Queue()
    sql_insert_port = "insert myport (ip_id, port, name, banner, http_title) value (%s, %s, %s, %s, %s)"
    # 多线程处理title
    for i in result[::-1]:
        ip = i[0]
        port = i[1]
        name = i[2].strip()
        banner = i[3].strip()
        print (ip, port, name, banner)
        port_queue.put((ip, port, name, banner))

    threads = []
    for i in xrange(150):
        thd = GetTitle(port_queue, title_queue)
        threads.append(thd)

    for thd in threads:
        thd.start()

    for thd in threads:
        if thd.is_alive():
            thd.join()


    # get data from queue, and get ip_id, save it to data[]
    while True:
        if title_queue.empty():
            break
        ip, port, name, banner, title = title_queue.get()
        print "len(title_queue): {0}\t ip:{1}\t port:{2}\t title:{3}".format((title_queue.qsize()), ip, port, title)
        try:
            cursor.execute("SELECT id FROM myip WHERE ip = '%s' ORDER BY id DESC" % ip)
            ip_id = cursor.fetchone()[0]
            count = cursor.execute("SELECT * FROM myport WHERE ip_id = %s AND port = %s", [ip_id, port])
            if count:
                cursor.execute("UPDATE myport set name=%s, banner=%s, http_title=%s WHERE ip_id=%s and port=%s", [name, banner, title, (ip_id), port])
                # print "UPDATE success!!!"
            else:
                cursor.execute("INSERT myport (ip_id, port, name, banner, http_title) value (%s,%s,%s,%s,%s)", [str(ip_id), port, name, banner, title])
            conn.commit()
        except Exception as e:
            print "[-]:[Lineno]:193\t\t ", str(e)
            conn.rollback()
        except KeyboardInterrupt as e:
            print "[-] KeyboardInterrupt"
            conn.rollback()

    conn.close()






if __name__ == '__main__':
    if len(sys.argv) != 2:
        print help
        sys.exit(0)
    filename = sys.argv[1]
    main(host, port, dbuser, dbpassword, db, filename)
