#coding=utf-8

"""
Scan class. 
to Scan IP.

111.206.13.65
"""


import masscan
import netaddr
import os
import subprocess

class Scan(object):
    """docstring for Scan"""
    # scan is abandon, Now use xscan
    @staticmethod
    def scan(ip, port=None, argument="--open --rate=2000"):
        """
        this is scan api, in this method, we define scan rate is 3000
        and default port is `port`
        and ip can be 10.10.10.1/24 or 10.10.10.1-124
        return format  {ip: [port,], [ip:[port,]]}

        """
        if port is None:
            #port = "21,22,23,443,445,2375,4098,1433,873,6300,7377,6301,8000-10000,11211,27017,28017,2181,80-100, 6379,9000,8196"
            port = "21,22,23,443,445,2375,4098,1433,873,6300,7377,6301,8000-10000,11211,27017,28017,2181,80-100,6379,9000,8196,5432,1099"
        mas = masscan.PortScanner()
        mas.scan(ip, port, argument)
        scanResult = {}
        #return mas.scan_result
        print mas.all_hosts
        for host in mas.all_hosts:
            scanResult[host] = mas[host]["tcp"].keys()
        return scanResult
    

    @staticmethod
    def xScan(ip, port=None, argument="-oX xScanResult.xml --open --rate=1500"):
        """
        #//todo: 这里还需要再改一下，将结果返回在一个固定的目录里边，这是城暂时先这样，把所有结构完整后再来搞这个

        """
        _= os.path.split(os.path.realpath(__file__))[0]
        macan_path = os.path.join(_, "masscan/bin/masscan")
        if port is None: 
            #port = "21,22,23,443,445,2375,4098,1433,873,6300,7377,6301,8000-10000,11211,27017,28017,2181,80-100,6379,9000,8196"
            #port = "21,22,23,443,445,2375,4098,1433,873,6300,7377,6301,8000-10000,11211,27017,28017,2181,80-100,6379,9000,8196,5432,1099,7001-7002"
            port = '21,22,80-100,389,443-445'\
                    ',873,1099,1334,1352,1417,1433-1434,1443,1455,1461,1494,1500-1501,1503,1521,1524,1533,1556,1580,1583,1594,1600,1641,1658'\
                    ',1666,1687-1688,1700,1717-1721,1723,1755,1761,1782-1783,1801,1805,1812,1839-1840,1862-1864,1875,1900,1914,1935'\
                    ',2375,3017,3030-3031,3052,3071,3077,3128,3168,3211,3221,3260-3261,3268-3269,3283,3300-3301,3306,3322-3325,3389,3351'\
                    ',5432,5987-5989,5998-6007,6009,6025,6059,6100-6101,6106,6112,6123,6129,6156,6346,6379-6380,6389,6502,6510,6543,6547'\
                    ',7001-7002,7025,7070,7100,7103,7106,7200-7201,7402,7435,7443,7496,7512,7625,7627,7676,7741,7777-7778,7800,7911,7920-7921'\
                    ',7937-7938,8000-10004,50070'\
                    ',11110-11111,11211-11212,11967,12000,12174,12265,12345,13456,13722,13782-13783,14000,14238,14441-14442,15000'\
                    ',19101,19283,19315,19350,19780,19801,19842,20000,20005,20031,20221-20222,20828,21571,22939,23502,24444,24800'\
                    ',25734-25735,26214,27000,27017-27018,27352-27353,27355-27356,27715,28201,30000,30718,30951,31038,31337,32768-32785'\
                    ',49163,49165,49167,49175-49176,49400,49999-50003,50006,50300,50389,50500,50636,50800,51103,51493,52673,52822'\


        MASSCAN = "{0} {1} -p{2} {3}".format(macan_path, ip, port, argument)
        # print "[+] Start Masscan: {0}".format(MASSCAN)
        p = subprocess.Popen(MASSCAN, shell=True, stdout=subprocess.PIPE)
        (output, err) = p.communicate()
        # print "[-] Masscan Stop, Go Check xScanResult.xml"
        

if __name__ == '__main__':
    Scan.xScan("60.28.175.1/28")
    #print result
    #print type(result)
    """
    for ip in ["71.5.7.1/24", "60.28.175.1/24"]:
        result = Scan.scan(ip)
        print result
        print "---" * 20
        break
    """

