#!/usr/bin/env python
# coding=utf-8

import urlparse
from hashlib import md5
import re
import threading

class SpiderUtil(object):
    """docstring for SpiderUtil"""
    @staticmethod
    def urlIdMd5(url):
        """
        URL id 指的是 协议+域名+路径+参数值
        其中对于路径来说，将路径中数据替换为{int}
        即：http://wwww.iqiyi.com/u/12342/?id=123&passwd=123
        的urlid为 md5(httpwww.iqiyi.comu{int}idpasswd)
        """
        try:
            domains = urlparse.urlparse(url)
            scheme = domains.scheme
            netloc = domains.netloc
            path = domains.path
            _ = domains.query
            query = []


            path = re.sub(r"\d+", "{int}", path)
            path = re.sub(r"\S+_\S+", "{@_@}", path)
            path = re.sub(r"\S+-\S+", "{#-#}", path)
            params = urlparse.parse_qsl(_)
            for i in params:
                query.append(i[0])
            query = "".join(sorted(query))
            # print scheme
            # print netloc
            # print path
            # print query
            return md5(scheme + netloc + path + query).hexdigest()
        except Exception as e:
            print "Error:{}\t ErrorURL:{}".format(str(e), url)
            return md5(url[0]).hexdigest()

    @staticmethod
    def writeResult(filename, queue):
        """
        # input filename  文件名
        # input queue     一个队列
        """
        with open(filename, "a") as f:
            while not queue.empty():
                f.write(queue.get() + "\n")



if __name__ == '__main__':
    print SpiderUtil.urlIdMd5("http://wenxue.iqiyi.com/book/detail-18l2gzcz7h.html")



