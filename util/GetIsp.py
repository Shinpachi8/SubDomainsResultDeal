#! /usr/bin/env python
# coding=utf-8

import threading
import logging
import requests
import Queue
import time
from bs4 import BeautifulSoup as bs

logging.getLogger("requests").setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO,  format='%(asctime)s %(filename)s [line:%(lineno)d] %(message)s')

headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.0; WOW64; rv:24.0) Gecko/20100101 Firefox/24.0",
        "Connection" : "close"
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
                start = time.time()
                ret = []
                a = threading.Thread(target=_getisp, args=(ip, ret))
                a.setDaemon(True)
                a.start()
                while True:
                    if (time.time() - start > 10):
                        print "[-] Time Out"
                        break
                    if a.is_alive():
                        time.sleep(1)
                    else:
                        break
                #print "ret is :" + str(ret)
                if ret:
                    local = ret[0]
                else:
                    local = ""
                    
                #res = requests.get(self.url.format(ip), headers=headers).content
                #soup = bs(res, "html.parser")
                #local = soup.find_all("span", attrs={"class": "Whwtdhalf w50-0"})[1]
                #time.sleep(0.01)
                logging.info("len(ip_queue):{0}\t ip:{1}\t isp:{2}".format(self.ip_queue.qsize(), ip, local.encode("utf-8")))
                self.isp_queue.put((ip, local.encode("utf-8")))
            except Exception as e:
                logging.info(str(e))
                self.isp_queue.put((ip, "Nowhere"))
                # logging.error(str(e))


def _getisp(ip, ret):
    try:
        url = "http://ip.chinaz.com/{0}"
        #print "[-] Parseing " + url
        res = requests.get(url.format(ip), headers=headers, timeout=5).content
        soup = bs(res, "html.parser")
        #local = soup.findall("span", attrs={"class": "Whwtdhalf w50-0"})[1]
        local = soup.find_all("span", attrs={"class": "Whwtdhalf w50-0"})[1]
        #print local.text
        
        ret.append(local.text)
    except Exception as e:
        #print str(e)
        pass


if __name__ == '__main__':
    a = Queue.Queue()
    ap= Queue.Queue()
    for i in range(20, 200):
        a.put("36.82.123.{}".format(i))

    a = GetIsp(a, ap)
    a.run()
