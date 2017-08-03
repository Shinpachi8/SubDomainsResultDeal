#!/usr/bin/env python
# coding=utf-8

from SpiderAndXcsl import *
from urlparse import urlparse as uparse
from tools.BBscanApi import *
import threading

"""
def spider(start_url, threadNum, resultFile, deep):

作为调用的接口，为了内存考虑，将所有的结果临时保存一份到resultFile里，然后返回一个List对象
@start_url 起始URL
@threadNum 线程数
@resultFile 临时保存文件
@return List
"""


def main():
    start_url = []
    with open("target.list", "r") as f:
        for line in f:
            start_url.append(line.strip())

    #start_url = "http://iqiyi.com"
    threadNum = 50
    resultFile = "testSpider.txt"
    deep = 5
    
    for i in start_url:
        spider_urls = spider(i, threadNum, resultFile, deep)
    #host = [uparse(_).netloc for _ in spider_urls]
    #hosts = list(set(host))
    #print len(hosts)
    #print hosts
    #args = Args(host=['mp.iqiyi.com',], network=24)
    #BBscanApi(args)

if __name__ == '__main__':
    main()
    #a = Args(host=["soaiymp3.com",], network=24)
    #print a.host, a.network
