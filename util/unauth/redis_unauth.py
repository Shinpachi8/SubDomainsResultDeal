#!/usr/bin/env python
# coding=utf-8

import redis

def redisDetect(host, port=6379):
    try:
        r = redis.Redis(host=host, port=6379, socket_timeout=20)
        if "redis_version" not in r.info():
            return False
        else:
            with open("redis_vu1n.txt" ,"a") as f:
                f.write(host + "\n")
            return True
    except Exception as e:
        return False


if __name__ == '__main__':
    with open("tmp2.txt", "r") as f:
        for line in f:
            ip = line.strip()
            if redisDetect(ip):
                print "{} May be vulnerable".format(ip)
            else:
                pass
    print "Done"

