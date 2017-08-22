#!/usr/bin/env python
#coding=utf-8

import requests
import time
import sys
from bs4 import BeautifulSoup as bs
from parseTool import parseTool
from GetTitle2 import GetTitle
from GetIsp import GetIsp
import MySQLdb as mdb
from Queue import Queue
import threading
import json
import re
import nmap
import logging

logging.getLogger("requests").setLevel(logging.WARNING)
requests.packages.urllib3.disable_warnings()

# global config

host = "127.0.0.1"
port = 3307
dbuser = "root"
dbpassword = "root"
db = "myipdb"

help =  """
        Usage:  python xx.py filename

        """



def Save2MySQL(filename, host=host, port=port, dbuser=dbuser, dbpassword=dbpassword, db=db, isp_table="myip", port_table="myport", company=''):
    #db = MysqlTool(host, port, dbuser, dbpassword)
    #db.execute("use myipdb;")
    _result = []
    conn = mdb.connect(host=host, port=port, user=dbuser, passwd=dbpassword, db=db)
    cursor = conn.cursor()
    result = parseTool.parse(filename)

    values = []
    ip_set = set()
    for i in result:
        ip = i[0]
        ip_set.add(ip)
    #print len(ip_set)
    ip_queue = Queue()
    isp_queue = Queue()
    for ip in ip_set:
        ip_queue.put(ip)
    del ip_set
    # get isp infomation, not important but useful maybe.
    threads = []
    for i in xrange(30):
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
        try:
            ip, isp = isp_queue.get(timeout=1)
        except Exception as e:
            continue
        #print "len(value):{0} \t ip:{1} \t isp:{2}".format((isp_queue.qsize()), ip, isp)
        try:
            count = cursor.execute("SELECT * FROM myip WHERE ip = '{0}'".format(ip))
            
            if count:
                tmp = cursor.fetchone()
                if tmp[2] == isp and tmp[3] == company:
                    continue
                else:
                    count = cursor.execute("UPDATE myip set isp = '{0}', company='{1}'  WHERE id={2}".format(isp, company ,tmp[0]))
                    print "[+] UPDATE success!!!"
            else:
                print "[+] [MySqlTool] [Save2MySQL] [ISP] " +  "INSERT myip (ip, isp, company) value (`%s`, `%s`, `%s`)" %(ip, isp, company)
                count = cursor.execute("INSERT myip (ip, isp, company) value ('{0}', '{1}', '{2}')".format(ip, isp, company))
                print "[+] INSERT success!!!"
            conn.commit()
        except Exception as e:
            print "[-] [MySqlTool] [SaveIspToMySQL] " + repr(e)
            conn.rollback()

    # parse port and save it to mysql
    # data: 17-06-19
    data = []
    port_queue = Queue()
    title_queue = Queue()
    sql_insert_port = "insert myport (ip_id, port, name, banner, http_title) value ('{ip_id}', '{port}', {name}, {banner}, {http_title})"

    # did not know why reverse it.
    for i in result[::-1]:
        ip = i[0]
        port = i[1]
        name = i[2].strip()
        banner = i[3].strip()
        #print (ip, port, name, banner)
        port_queue.put((ip, port, name, banner))

    threads = []
    for i in xrange(50):
        thd = GetTitle(port_queue, title_queue)
        threads.append(thd)

    for thd in threads:
        thd.start()

    for thd in threads:
        if thd.is_alive():
            thd.join()


    #default_port = ["21", "22", "445", "1433", "837", "6379", "11211", "27017", "3389", "3306", "2375", "2181", "9200"]
    #default_serv = ["FTP", "SSH", "RPC", "MSSQL", "RSYNC", "REDIS", "memcached", "Mongodb", "REMOTE DESKTOP", "MYSQL", "DOCKER", "zookeeper", "elasticsearch"]
    default_service = {
        "21" : "ftp",
        "22" : "ssh",
        "445" : "rpc",
        "1099" : "rmi",
        "1433" : "mssql",
        "873" : "rsync",
        "6379" : "redis",
        "11211" : "memcached",
        "3306" : "mysql",
        "27017" : "mongodb",
        "3389" : "remote desktop",
        "2375" : "docker",
        "2181" : "zookeeper",
        "9200" : "elasticsearch",
    }
    # get data from queue, and get ip_id, save it to data[]
    while True:
        if title_queue.empty():
            break
        try:
            ip, port, name, banner, title = title_queue.get(timeout=1)
        except Exception as e:
            continue
        _result.append((ip, port, title))
        # 默认判断端口
        if port in default_service:
            banner = default_service[port]
        elif title != '#E':
            banner = "http"
        else:
            # 如果要使用nmap的话，那么只能单个扫了，可能会浪费很多时间
            banner = nmap_banner(ip, port)
            if banner == "":
                banner = "unrecognized"
            # 如果banner不等于http，那么titile为'Na_Http_Service'
            elif banner != "http":
                title = "Na_Http_Service"
        #print "len(title_queue): {0}\t ip:{1}\t port:{2}\t title:{3}".format((title_queue.qsize()), ip, port, title)
        try:
            cursor.execute("SELECT id FROM myip WHERE ip = '{ip}' ORDER BY id DESC".format(ip=ip))
            ip_id = cursor.fetchone()[0]
            count = cursor.execute("SELECT * FROM myport WHERE ip_id = '{ip_id}' AND port = '{port}'".format(ip_id=ip_id, port=port))
            if count:
                cursor.execute("UPDATE myport set name='{name}', banner='{banner}', http_title='{http_title}' WHERE ip_id='{ip_id}' and port='{port}'".format(name=name, banner=banner, http_title=title, ip_id=str(ip_id), port=port))
                print "UPDATE success!!!"
            else:
                cursor.execute("INSERT myport (ip_id, port, name, banner, http_title) value ('{ip_id}','{port}','{name}', '{banner}', '{http_title}')".format(ip_id=str(ip_id), port=port, name=name, banner=banner, http_title=title))
            conn.commit()
        except Exception as e:
            print "[-] [MySqlTool] [Save2MySQL] [Error]" + repr(e)
            # ignore errors
            conn.rollback()
        except KeyboardInterrupt as e:
            # ignore errors
            logging.info("[User Kill] [MySQLTool.Save2MySQL] Ctrl-C Kill Process")
            conn.rollback()

    conn.close()
    return _result



def nmap_banner(ip, port):
    banner = ""
    nm = nmap.PortScanner()
    print "[+] [MySqlTool] [nmap_banner] Namp:  {}:{}".format(ip, port)
    try:
        nm.scan(ip, port)

        if nm[ip] and nm[ip].all_protocols() and "tcp" in nm[ip].all_protocols():
            if nm[ip]["tcp"][int(port)]['state'] == "open":
                banner = nm[ip]["tcp"][int(port)]['name']
                return banner
    except Exception as e:
        print "[-] [MySqlTool] [nmap_banner] [Error] " + repr(e)
    return banner



if __name__ == '__main__':
    #if len(sys.argv) != 2:
    #    print help
    #    sys.exit(0)
    #filename = sys.argv[1]
    #main(host, port, dbuser, dbpassword, db, filename)
    # banner = nmap_banner("180.149.134.63", "9090")
    # print banner
    Save2MySQL("../xScanResult.xml", company="autohome")
