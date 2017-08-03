#!/usr/bin/env python
# -*- coding:utf-8 -*-


import socket


def zooUnauth(ip_list, port=2181, timeout=10):
    # 检测zookeeper的未授权访问，超时间隔为10s，
    # 这个函数我只想安安静静做个单线程 
    # 返回值是一个list,用来和主线程的结果合并
    result = []
    for ip in ip_list:
        try:
            socket.setdefaulttimeout(timeout)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(ip, int(port))
            s.send("envi")
            data = s.recv(1024)
            if "Environment" in data:
                target = "zookeeper://{0}:{1}".format(ip, port)
                type = "unauth"
                info = "zookeeper unauth detect maybe"
                _ = {'target': target, 'type': type, 'info':info}
                result.append(_)

        except Exception as e:
            pass
        finally:
            s.close()
    return result
