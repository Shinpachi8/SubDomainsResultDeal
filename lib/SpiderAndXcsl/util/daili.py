#!/usr/bin/env python
# coding=utf-8

import requests
import urllib2
import time


class daili(object):
    """docstring for daili"""
    @staticmethod
    def getDaili():
        """爬取代理"""
        of = open('proxy.txt' , 'w')
 
        for page in range(1, 160):
            html_doc = urllib2.urlopen('http://www.xici.net.co/nn/' + str(page) ).read()
            soup = BeautifulSoup(html_doc)
            trs = soup.find('table', id='ip_list').find_all('tr')
            for tr in trs[1:]:
                tds = tr.find_all('td')
                ip = tds[1].text.strip()
                port = tds[2].text.strip()
                protocol = tds[5].text.strip()
                if protocol == 'HTTP' or protocol == 'HTTPS':
                    of.write('%s=%s:%s\n' % (protocol, ip, port) )
                    print '%s=%s:%s' % (protocol, ip, port)
            time.sleep(1)
        of.close()


    @staticmethod
    def validTest(filename):
        """验证代理是否确"""
        with open(filename, "r") as f:
            for proxy_line in f:
                proxy_line = proxy_line.strip()
                protocol, proxy = proxy_line.split("=")
                pr = {protocol.lower(): protocol.lower() + "://" + proxy.strip(),}
                # print pr
                try:
                    # 延时5s
                    res = requests.get("http://1212.ip138.com/ic.asp", headers=headers, timeout=5.0, proxies=pr)
                    if proxy.split(":")[0] in res.content:
                    # lock.acquire()
                        print proxy + "[ok!]"
                        with open("validProxies.txt", "a") as fo:
                            fo.write(proxy_line)
                    # lock.release()
                except Exception, e:
                    pass
            