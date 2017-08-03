#!/usr/bin/env python
#coding=utf-8

"""
to parse nmap/masscan xml result,
next step to save to sql database

"""
import sys
# import pprint
from pprint import pprint
import chardet
from lxml import etree
from bs4 import BeautifulSoup as bs


reload(sys)
sys.setdefaultencoding('utf8')
class parseTool(object):
    """docstring for parseTool
    type:
        1=>nmap
        2=>masscan
        3=>whatweb

    return:
        [(ip, port, name, banner),]


    """
    # global scanner
    # scanner = {
    #     "nmap" : False,
    #     "masscan" : False,
    #     "whatweb" : False
    # }

    @staticmethod
    def parse(filename):
        with open(filename, "r") as f:
            _ = f.read()
        if len(_) == 0:
            return []
        if parseTool.identify_scanner(filename) == "nmap":
            return parseTool.parse_nmap(filename)
        elif parseTool.identify_scanner(filename) == "masscan":
            return parseTool.parse_masscan(filename)

    # for now , only identity nmap/masscan
    @staticmethod
    def identify_scanner(filename):
        tree = etree.parse(filename)
        root = tree.getroot()
        scanner_type = root.get("scanner")

        if scanner_type == "nmap":
            return "nmap"
        if scanner_type == "masscan":
            return "masscan"
        # for element in root:
        #     for field in element:
        #         # if field == "scanner":
        #         print field.tag
    @staticmethod
    def parse_masscan(filename):
        result = {}
        with open(filename, "r") as f:
            content = f.read()
        soup = bs(content, "lxml")
        hosts = soup.find_all("host")
        for host in hosts:
            addr = host.find("address")["addr"]
            # print addr["addr"]
            port = host.find("port")
            # print port
            state = port.find("state")["reason"]
            if state == "response":
                name = port.find("service")["name"]
                banner = port.find("service")["banner"]
            else:
                name = ""
                banner = ""
            if (addr, port["portid"]) in result:
                name1, banner1 = result[(addr, port["portid"])]
                if name1 in ["title", ""]:
                    result[(addr, port["portid"])] = (name, banner.split("\\x0a")[0])

            else:
                result[(addr, port["portid"])] = (name, banner.split("\\x0a")[0])
        items = result.items()
        tmp = [(item[0][0], item[0][1], item[1][0], item[1][1]) for item in items]
        return tmp

    @staticmethod
    def parse_nmap(filename):
        with open(filename, "r") as f:
            content = f.read()
        soup = bs(content, "lxml")
        hosts = soup.find_all("host")
        result = []
        for host in hosts:
            address = host.find("address")["addr"]
            port_open = host.find_all("port")
            service_name = ""
            product = ""
            if port_open:
                for p in port_open:
                    # pprint(address + ":" + p["portid"] + " "  + p.find("state")["state"])
                    if p.find("state")["state"] == "open":
                        if p.find("service"):

                            service_name = p.find("service")["name"]
                            if p.find("service").has_attr("product"):
                                product = p.find("service")["product"]
                            # if p.find("service").has_attr("servicefp"):
                            #     product = p.find("service")["servicefp"]
                    output_format = "addr: {} \t port: {}\t sevice: {}\t product: {}".format(address, p["portid"], service_name, product)
                    result.append((address, p["portid"], service_name, product))
                    # print p["portid"], p["state"]
        return result


if __name__ == '__main__':
    # filename = "nmap_test2.xml"
    masscan = "/Users/jiaxiaoyan/Desktop/tmp/tmp_rsync.xml"
    pprint(parseTool.parse_masscan(masscan))
    # pprint(parseTool.parse_nmap(filename))




