#! /usr/bin/env python
# coding=utf-8

import threading
import re
import socket
import logging
import urllib2
import requests
import time

#logging.getLogger("requests").setLevel(logging.ERROR)
logging.basicConfig(level=logging.INFO,  format='%(asctime)s %(filename)s [line:%(lineno)d] %(message)s')
#socket.setdefaulttimeout(10)
requests.packages.urllib3.disable_warnings()

headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.0; WOW64; rv:24.0) Gecko/20100101 Firefox/24.0",
        "Connection": "Close"
    }
pattern = re.compile(r".*<title>(.*)</title>.*", re.I)
pattern2 = re.compile(r".*<h1>(.*)</h1>.*", re.I)

lock = threading.Lock()

class GetTitle(threading.Thread):
    """docstring for GetTitle"""
    def __init__(self, port_queue, title_queue):
        threading.Thread.__init__(self)
        self.port_queue = port_queue
        self.title_queue = title_queue

    def run(self):
        while True:
            if self.port_queue.empty():
                #print "break............."
                break
            ip, port, name, banner = self.port_queue.get(timeout=3)
            if port in ["21", "22", "23","53" , "445","3306", "873", "6379", "11211", "27017", "1433", "2375", "2181", "1099"]:
                continue
            if str(port) == '443':
                url = "https://{0}:{1}".format(ip, port)
            else:
                url = "http://{0}:{1}".format(ip, port)

            try:
                #print url
                # and a new thread to check http, incase there is no "\r\n\r\n" return and the requests hanging there.
                #title = self.check(url)
                title = self._check(url) 
                title = decode_response_text(title)
                self.title_queue.put((ip, port,name, banner, title))
                if not ("#E" in title):
                    logging.info("[Info] [GetTitle] Remain:{0}\t Url:{1}\t Title:{2}".format(self.port_queue.qsize(), url, title))
            except Exception as e:
                # ignore errors
                pass
                # logging.error(str(e))

    def _check(self, url):
        try:
            ret = []
            a = threading.Thread(target=check, args=(url, ret))
            a.setDaemon(True)
            starttime = time.time()
            a.start()
            while a.is_alive():
                if time.time() - starttime > 15:
                    return "#E"
                else:
                    time.sleep(1)
            
            if not ret:
                return "#E"
            resp = ret[0]
            m = pattern.findall(resp.text)
            if m:
                title = m[0]
            else:
                title = resp.text.replace("\n", "").replace(" ", "")[0:200]
            return title
        except Exception as e:
            return "#E"


def decode_response_text(text):
    for _ in ['UTF-8', 'GB2312', 'GBK', 'iso-8859-1', 'big5']:
        try:
            result = text.encode(_)
            return result
        except Exception as e:
            pass
    # if cannot encode the title . return it.
    return text


def check(url, ret):
    title = ""
    try:
        ret.append(requests.get(url, timeout=10, headers=headers, verify=False))
    except Exception as e:
        #print str(e)
        return "#E"

