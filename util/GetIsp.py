#! /usr/bin/env python
# coding=utf-8

import threading
import logging
import requests
import time
from bs4 import BeautifulSoup as bs

logging.getLogger("requests").setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO,  format='%(asctime)s %(filename)s [line:%(lineno)d] %(message)s')

headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.0; WOW64; rv:24.0) Gecko/20100101 Firefox/24.0"
    }


class GetIsp(threading.Thread):
    """docstring for GetTitle"""
    def __init__(self, ip_queue, isp_queue):
        threading.Thread.__init__(self)
        self.ip_queue = ip_queue
        self.isp_queue = isp_queue
        self.url = "http://ip.chinaz.com/{0}"

    def run(self):
        while True:
            if self.ip_queue.empty():
                break
            ip = self.ip_queue.get(timeout=3)
            try:

                res = requests.get(self.url.format(ip), headers=headers).content
                soup = bs(res, "html.parser")
                local = soup.find_all("span", attrs={"class": "Whwtdhalf w50-0"})[1]
                time.sleep(0.01)
                logging.info("len(ip_queue):{0}\t ip:{1}\t isp:{2}".format(self.ip_queue.qsize(), ip, local.text.encode("utf-8")))
                self.isp_queue.put((ip, local.text.encode("utf-8")))
            except Exception as e:
                logging.info(str(e))
                self.isp_queue.put((ip, "Nowhere"))
                # logging.error(str(e))

