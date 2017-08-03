# coding=utf-8

"""
format out the subdomains result, for now : support layer and subDomainsBruet

"""

import re
import threading
import json
import sys
import argparse
import logging
import time
import Queue
from util.FormatOutput import FormatOutput
from util.MySqlTool import Save2MySQL
from util.parseTool import parseTool
from util.ZookeeperUnauth import zooUnauth
from colorama import *
from requests import head
from lib.mascan.Scan import Scan
from lib.BBscanApi import *
from util.unauth.PortBrute import *
from util.unauth.unauthDetect import * 

logging.basicConfig(level=logging.INFO,
                    format='[%(threadname)s^^%(lineno)d]:\t %(message)s')#输出格式
logging.getLogger("requests").setLevel(logging.WARNING)

"""
新版本已经不再需要dealSubDomainBrust 与check_url这两个函数了
而是用BBScan的内容来处理这些内容

暂定：
除了BBScan的Report外，将结果都保存成这样
{
    'target': target,
    'type'  : type,
    'info'  : info
}
一条一条的按批次来，存入list中，最后再json.dump到文件中。


update 17-06-12
现在流程是这样的，首先传入的subDomainBrute的结果，解析完后之后，
url 传给BBScan去扫描，
ip 会保存下来，并取出前15个最多的C段
然后对C段进行扫描，将21,22,3306分别去暴破，
                    873,6379,27017 送去未授权访问模块验证

剩下的都当作是HTTP的服务，送给BBScan去扫描

todo::  将子域名推到爬虫里去， 在爬虫里将XSSDetect集成进去
        并对文件包含也做测试

"""


class dealSubDomainBrust(threading.Thread):
    """docstring for ClassName"""
    def __init__(self, url_queue, queue_out):
        threading.Thread.__init__(self)
        self.queue = url_queue # 队列
        self.queue_out = queue_out

    def run(self):
        while True:
            if self.queue.empty():
                break
            try:
                url = self.queue.get_nowait()
                if not url.startswith("http"):
                    url = "http://" + url
                url_valid = check_url(url)
                if url_valid:
                    self.queue_out.put(url)
            except Exception as e:
                logging.warn(Fore.RED + str(e) + Style.RESET_ALL)
                break


def parseArg():

    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs='+', help="file export from subDomainsBrute or Layer")
    parser.add_argument("--dnsdb", help="dnsdb export file, json format")
    parser.add_argument("-ou", "--outurl", help=("Output file to save url,"
                                "if use same file, output will append at the end. default: out_{date}_url.txt"))
    parser.add_argument("-oi", "--outip", help="Output file to save ip, dafult: out_{date}_ip.txt")
    parser.add_argument("-t", "--thread", type=int, default=100, help="thread number, default 100")
    parser.add_argument("--company", help="the company name or host this scan")
    parser.add_argument("--num", type=int, default=5, help="the C count to scan default 5")
    parser.add_argument("--skip", type=int, default=0, help="in scan, skip top n ips to scan, must lt num")
    parser.add_argument("--bbscan", default=True, action='store_true', help='start bbscan')
    parser.add_argument("--cs", default=False, action='store_true', help='crack ssh weak passwd')
    parser.add_argument("--cf", default=False, action='store_true', help='crack ftp weak passwd')
    parser.add_argument("--cm", default=False, action='store_true', help='crack mysql weak passwd')
    
    args = parser.parse_args()
    return args


def main():
    # default match layer and subDomainsBrute
    pattern_subDomains = re.compile(r"(\S+)\s+(.*)")
    pattern_layer = re.compile(r"(\S+)\t(\S+).*")

    url_list = []
    ip_list = []

    # parse params
    args = parseArg()
    if args.skip >= args.num:
        logging.info("[Error] [main] the value of skip must lower than num")
        sys.exit(-1)
    
    date = time.strftime("%Y-%m-%d-%H-%M", time.localtime())
    for file in args.file:
        with open(file, "r") as f:
            line = f.readline()
        if pattern_layer.match(line):
            tmp_url_list, tmp_ip_list = FormatOutput.format(pattern_layer, file)
        else:
            tmp_url_list, tmp_ip_list = FormatOutput.format(pattern_subDomains, file)
        url_list.extend(tmp_url_list)
        ip_list.extend(tmp_ip_list)
    
    if args.dnsdb:
        try:
            # only match ip if type == a
            # update 17/08/01 add dnsdb.io cname json format file
            dnsdb_pattern = re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")
            with open(args.dnsdb, 'r') as f:
                for record in f:
                    _ = json.loads(record.strip())
                    if _['type'] == 'a' and dnsdb_pattern.match(_['value']):
                        url_list.append(_['host'])
                        ip_list.append(_['value'])
                    elif _["type"] == "cname":
                        url_list.append(_["host"])
        except Exception as e:
            logging.error("[-] Parse DnsDb Error, Maybe Not Json Format..")
            sys.exit(-1)

    # deal with company
    if args.company:
        company = args.company
    else:
        company = ""

    # output ip txt
    if args.outip is None:
        out_ip_fn = company + date + "_ip.txt"
    else:
        out_ip_fn = args.outip
    
    # output url txt
    if args.outurl is None:
        out_url_fn = company + date + "_url.txt"
    else:
        out_url_fn = args.outurl

    # save ip, json format
    ip_list = list(set(ip_list))
    FormatOutput.save2file(out_ip_fn, ip_list)
    # found the most num host in mask 24
    C_section = FormatOutput.net_section(out_ip_fn, num=args.num)

    print C_section
    #sys.exit(-1)
    all_host = {}
    # vulnearble host
    vulnearble = []
    # zookeeper IP list
    zookeeper_host = []
    # error ip when scanning
    bad_host = []
    # ip with ftp, ssh or mysql
    ftp_host = []
    ssh_host = []
    mysql_host = []
    # ip queue which open 873, 6379, 27017
    unauth_host = Queue.Queue()
    # 保存至file中，调用 BBscan中的-f参数
    hosts = []
    for c_s in C_section[args.skip:]:
        print c_s
        try:
            logging.info("[Info] [main] Scan {}st ip with mask 24".format(C_section.index(c_s)))
            Scan.xScan(c_s)
            logging.info("[Info] [main] Scan Finished. Go Parse XML And Save It To MySQL")
            _ = Save2MySQL("xScanResult.xml", company=company)
            # item in _ like [(ip, port, title),()]

            for line in _:
                ip = line[0]
                port = line[1]
                title = line[2]
                # dict replace it
                if port == '21':
                    ftp_host.append(ip)
                elif port == '22':
                    ssh_host.append(ip)
                elif port == '3306':
                    mysql_host.append(ip)
                elif port in ['873', '6379', '27017']:
                    unauth_host.put(ip+":"+port)
                elif port == "2181":
                    zookeeper_host.append(ip)
                elif port == "9000":
                    # fastcgi scan
                    pass
                elif port == "9200":
                    # es scan
                    pass
                elif port == "1099":
                    # rmi deSerializable
                    pass
                # 分别为ftp, ssh, telnet, smb, docker, rsync, mssql, mongodb, mongodb, redis
                if port not in ["21", "22", "445", "2375", "873", "1433", "27017", "6379", "11211", "3306", "3389", "2181", "1099"] and title not in ["", "#E"]:
                    hosts.append("{0}:{1}".format(ip, port))
                
        except Exception, e:
            bad_host.append(c_s)
    
    # scan unauth access
    tmp = Queue.Queue()
    unauthResult = runUnauthDetect(unauth_host, tmp)
    
    vulnearble.extend(unauthResult)
    
    # scan zookeeper
    tmp = zooUnauth(zookeeper_host)
    vulnearble.extend(tmp)

    # bbscan api to scan sensitive file
    with open("toBBscan.txt", "w") as f:
        for i in hosts:
            f.write(i + "\n")

    if args.bbscan:
        absPath = os.path.abspath("toBBscan.txt")
        _args = Args(f=absPath, host=url_list)
        BBscanApi(_args)


    ufile = "./dict/username.lst"
    pfile = "./dict/password.lst"
    resultQueue = Queue.Queue()
    
    if args.cf:
    # brute ftp service
        for ip in ftp_host:
            _ = FTPBrute(host=ip, ufile=ufile, pfile=pfile, resultQueue=resultQueue)
            _.run()

    # brute ssh service
    if args.cs:
        for ip in ssh_host:
            _ = SSHBrute(host=ip, ufile=ufile, pfile=pfile, resultQueue=resultQueue)
            _.run()
   
    # brute mysql service
    if args.cm:
        for ip in mysql_host:
            _ = MySQLBrute(host=ip, ufile=ufile, pfile=pfile, resultQueue=resultQueue)
            _.run()
    
    # output brute result
    if resultQueue.empty():
        logging.info("NOT FOUND ftp/ssh/mysql Weak Password.")
    else:
        with open("FSMBruteResult.txt", "a") as f:
            while not resultQueue.empty():
                _ = (resultQueue.get())
                logging.info(_)
                f.write(_ + "\n")
        
        logging.info("[Info] [main] Brute Result Write Into FSMBruteResult.txt")


    # save the vulnerable ip
    if vulnearble:
        FormatOutput.save2file(date + "vuln.json", vulnearble)
        logging.info("[Info] [main] Save Unauth Result Into {}vuln.json".format(date))
    

    for i in vulnearble:
        print Fore.Red + i + Style.RESET_ALL


if __name__ == '__main__':
    main()
