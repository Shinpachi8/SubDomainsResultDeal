#coding=utf-8

import re
import json
import pprint
import logging
import os
from colorama import *

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s^^%(lineno)d:\t %(message)s')#输出格式

class FormatOutput(object):
    """docstring for FormatOutput"""
    @staticmethod
    def format(pattern, filename):
        url_list = set()
        ip_list = set()
        with open(filename, "r") as f:
            for line in f:
                mat = pattern.match(line)
                if mat:
                    url_list.add(mat.groups()[0])
                    for _ in mat.groups()[1].split(","):
                        ip_list.add(_.strip())
                else:
                    logging.info(Fore.RED + "NOT MATCH THE PATTEN. MAY BE SHOULD CHOOSE ANOTHER PATTERN")
        return list(url_list), list(ip_list)


    @staticmethod
    def net_section(filename, saveall=False, num=15):
        """
        @input filename 传入的IP地址所在文件名，
        @output 如果C段数多于10个，那么保留最多的10个，如果少于10个，那么全部保留
        """
        net = {}
        url_list = []
        if not (os.path.exists(filename) and os.path.isfile(filename)):
            logging.info(Fore.RED + "ip file doesn't exist or it's not a file" + Style.RESET_ALL)
            return
        with open(filename, "r") as f:
            try:
                url_list = json.load(f)
            except Exception as e:
                for line in f:
                    url_list.append(line.strip())

            for line in url_list:
                line = line.strip()
                logging.info(Fore.RED + line + Style.RESET_ALL)
                if line[:line.index(".")] in ["127", "10", "192", "172", "1"]:
                    continue
                else:
                    tmp = line[:line.rindex(".")]
                    if tmp in net:
                        net[tmp] += 1
                    else:
                        net[tmp] = 1

        net = sorted(net.items(), lambda x,y:cmp(x[1], y[1]), reverse=True)
        # print net, len(net)
        # 如果大于10， 取前10， 如果小于10， 取全部
        if len(net) > num:
            result = net[:num]
        else:
            result = net

        suffix = ".1/24"
        #save_file = raw_input("input the filename to save possiable ip_section:\n")
        save_file = filename.split(".")[0] + "most_15_c_frag.txt"
        while os.path.exists(save_file):
            print "This file already exist, please input anthor:\n"
            save_file = raw_input(">>>>")
        with open(save_file, "w") as f:
            for line in result:
                logging.info(Fore.CYAN + line[0] + suffix + "apper {} times in subDomain Brute result".format(line[1]) + Style.RESET_ALL)
                f.write(line[0] + suffix + "\n")
        logging.info(" Done. please ues: " +  Fore.GREEN + "whatweb --input-file={} -v --no-errors --log-xml={}".format(save_file, "your_log_file") + Style.RESET_ALL)
        if saveall:
            with open("ipsection.txt", "wb") as f:
                for line in net:
                    f.write(line[0] + suffix + "\n")
            logging.info("Save all ip section done!")
        # 返回结果处理
        ip_section = []
        for _ in result:
            ip_section.append(_[0] + suffix)
        return ip_section

    @staticmethod
    def save2file(filename, value):
        """
        @input filename  filename to save
        @input value     list of value to save
        @output None
        """
        if os.path.exists(filename):
            pprint("This file already existed. Do u want rewirte it? [Y|y] or [N|n] ")
            pprint("if No, save as {}_2".format(filename))
            awnser = raw_input()
            while awnser not in ["Y", "n", "N", "y"]:
                pprint("This file already existed. Do u want rewirte it? [Y|y] or [N|n]\t: ")
                awnser = raw_input()
            if awnser in ["N", "n"]:
                filename = filename.split(".")[0]+ "_2" + filename.split(".")[1]

        with open(filename, "wb") as f:
            json.dump(value, f)

        logging.info(Fore.GREEN + "JSON FORMAT SAVE DONE!" + Style.RESET_ALL)
