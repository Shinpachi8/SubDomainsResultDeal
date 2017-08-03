#!/usr/bin/env python
# coding=utf-8

from threading import Thread, Lock
from threading import Condition
from Queue import Queue as queue
from bs4 import BeautifulSoup as bs
from util.SpiderUtil import SpiderUtil
import logging
import requests
import urlparse
import time
import sys
import re
import json


reload(sys)
sys.setdefaultencoding('utf-8')

logging.basicConfig(format="[%(asctime)s]^^[%(funcName)s]^^[%(lineno)d]\t%(message)s",
                    level = logging.INFO)
logging.getLogger("requests").setLevel(logging.WARNING)


"""
以下为自己的爬虫部分，
现在用的是猪猪侠的爬虫
发现并不合适呀

"""
# 未爬取url
unSpider = queue()

# 已爬取URL
spidered = queue()

# 待解析content
parseQueue = queue()
condition = Condition()
lock = Lock()
global repeat
repeat = set()
headers = {
    "User-Agent" : "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36",
    "Connention" : "Close"
}


def _homology(domain, url):
    if domain in url:
        return True
    else:
        return False

class Crawl(Thread):
    """this class is for crawl the url."""
    def __init__(self, unSpider, spidered, resultFile, deepest):
        Thread.__init__(self)
        self.unSpider = unSpider
        self.spidered = spidered
        self.resultFile = resultFile
        self.deepest = deepest

    def run(self):
        while True:
            # if self.unSpider.empty():
            #     break
            if spidered.qsize() > 1000000:
                lock.acquire()
                SpiderUtil.writeResult(self.resultFile, spidered)
                lock.release()

            try:
                host, deep, target = self.unSpider.get(timeout=3)

                logging.info("deep:{}\tSpiding: {}".format(deep, host))
                # 深度
                domain = urlparse.urlparse(host)
                response = requests.get(host, headers=headers, timeout=5, verify=False)

                self.spidered.put(response.url)
                # 只爬取TEXT/HTML的

                if "text/html" in response.headers["Content-Type"]:
                    # logging.info("put {} into parseQueue".format(response.url))
                    self.parseHtml(response.text, deep, domain, target)
                if deep > (self.deepest - 1) or self.unSpider.empty():
                    break

            except Exception as e:
                logging.info(str(e))
                #break


    def parseHtml(self, html, deep, domain, target):
        # 只解析<a> 标签
        soup = bs(html, "lxml")
        for tag in soup.find_all('a'):
            if tag.attrs.has_key('href'):
                link = tag.attrs['href']
                # link = urlparse.urldefrag(tag.attrs['href'])[0] # 处理掉#tag标签信息
                if link.startswith("javascript") or link.startswith("mailto"):
                    continue
                complet_link = self.complet_url(link.strip(), domain)
                # logging.info("Get A Link:\t{}".format(complet_link))
                if complet_link and _homology(target, complet_link):
                    # //TODO: 去重
                    _ = SpiderUtil.urlIdMd5(complet_link)
                    global repeat
                    if _ in repeat:
                        continue
                    else:
                        repeat.add(_)
                    self.unSpider.put((complet_link, deep+1, target))

    def complet_url(self, link, domain):
        if link.startswith("http://") or link.startswith("https://"):
            return link
        if link.startswith("//"):
            return domain.scheme + ":" + link
        elif link.startswith("/"):
            return domain.scheme + "://" + domain.netloc + link
        else:
            return domain.scheme + "://" + domain.netloc + "/" + link




def spider(urls, threadNum, resultFile, deepest):
    """
    作为调用的接口，为了内存考虑，将所有的结果临时保存一份到resultFile里，然后返回一个List对象
    @start_url 起始URL
    @threadNum 线程数
    @resultFile 临时保存文件
    @return List
    """
    spider_num = threadNum
    spider_threads = []
    for start_url in urls:
        start_url = start_url if start_url.startswith("http://") else "http://"+start_url
    #global target
        _ = urlparse.urlparse(start_url).netloc
        target = "".join(_.split(".")[1:]) if "www" in _.split(".")[0] else _
        # 将target，即用来匹配是否相同域名的字段放入unSpider中，这个字段不变，仅为了保持方便判断
        unSpider.put((start_url, 1, target))

    try:
        #logging.info("put start url in to queue")
        #unSpider.put((start_url, 1))
        logging.info("unspider.qsize(): {}".format(unSpider.qsize()))

        for _ in xrange(spider_num):
            thd = Crawl(unSpider, spidered, resultFile, deepest)
            thd.setDaemon(True)
            spider_threads.append(thd)
        for thd in spider_threads:
            thd.start()
        while True:
            live_count = 0
            for thd in spider_threads:
                if thd.is_alive():
                    time.sleep(1)
                else:
                    live_count += 1
            if live_count == len(spider_threads):
                break

    except KeyboardInterrupt:
        while not unSpider.empty():
            unSpider.get_nowait()
    except Exception as e:
        logging.error(str(e))



    while not unSpider.empty():
        tmp = unSpider.get()[0]
        _ = SpiderUtil.urlIdMd5(tmp)
        if _ in repeat:
            continue
        else:
            spidered.put(tmp)
    
    spiderResult = []
    while not spidered.empty():
        _ = spidered.get()
        spiderResult.append(_)


    #SpiderUtil.writeResult(resultFile, spidered)
    """
    with open(resultFile, "r") as f:
        _ = f.readlines()
        logging.info("Total {} lines".format(len(_)))
        logging.info('''\n===================================
                        \nResult Spider {}
                        \n==================================='''.format("Test"))
        for line in _:
            print "{}".format(line.strip())
            spiderResult.append(line.strip())
    """
    return spiderResult


if __name__ == '__main__':
    urls = []
    with open(sys.argv[1], "r") as f:
        for line in f:
            _ = line.split(" ")[0]
            urls.append(_)
    a = spider(urls, 40, "spiderResult.txt", 4)
    with open("spiderResult.txt", "w") as f:
        for i in a:
            f.write(i + "\n")

    # 判断是否以.html, .htm, .shtml, 结尾，如果是，认为是静态页面，pass
    # 判断是否以 action 结尾，如果有，后续放入struts 插件扫描
    # 判断是否有参数，如果有参数， 文件包含，XSS和sqlmapapi扫描， 如果没有，只做文件包含
    # 如果参数是有URL，IMAGE 关键字， ssrf (还没做, 可以在VPS中建立一个锚点) 

    action_end = []
    param = []
    ssrf_url = []
    for url in a:
        o = urlparse.urlparse(url)
        # 取出参数来, 保留非查询URL以便后边处理
        if o.query == '':
            pass
        else:
            param.append(url)
            query = "".join(urlparse.parse_qs(o.query).keys())
            for _ in ['url', 'src', 'target', 'image', 'wap', 'link', 'share']:
                # 有一符合即可
                if _ in query.lower():
                    ssrf_url.append(url)
                    break

    
        # action 结尾
        if ".action" in o.path:
            action_end.append(url)
        
            










