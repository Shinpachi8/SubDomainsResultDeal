本工具严禁用于非法用途，否则后果自负

# 说明
1. 依赖包
```
MySQL-python 1.2.5
requests
以及BBScan的依赖包
```

2. 使用

输入Layer子域名挖掘机/subDomainsBrute的子域名文件，也可以使用dnsdb.io导出json的文件

利用masscan来进行扫描，根据自己的带宽设置扫描速度， 在 lib/mscan/Scan/xscan函数里编辑

如果masscan失败，可以自己编译一下

解析结果保存至MySQL, MySQL的配置在其自己的函数文件中：  util/MySqlTool中编辑

需要首先创建MySQL的数据库, 默认库名为myipdb， 表名为myip, myport， 在ipdb.sql中

剩下的可以用python subDomainsResultFormat.py -h 来查看



# update: 2017-0802
- 基本工作已经完成，这里包含以下几种功能：

    1. 接收SubDomainsBrute和Layer子域名挖掘机的结果， 同时可以加载dnsdb.io导出的json文件, 支持cname/ type a 
    
    2. 对文件做处理，拿到URL，并对排序最高的几个C段进行扫描，扫描工具用的masscan

    3. 处理masscan的结果，并判断isp与端口是否为HTTP服务，存入数据库
    
    4. 对常见的服务FTP,SSH,MYSQL进行弱口令暴破

    5. 对于常见的服务RSYNC, REDIS, MEMCACHE, MONGODB,ZOOKEEPER 做未授权访问
    
    6. 对除这些之外的端口，默认为HTTP，并请求查看返回的title，也存入数据库

    7. 对于返回title的端口，与IP一起使用BBSCAN扫描，结果存在report/目录下

- 待更新：
    1. spider一下子域名`./lib/SpiderAndXcsl/`，(已做，LowBee爬虫，可自行替换， 尚未合并)
    
    2. 将其中的包含参数的URL，推入XSSDETECT(已完成), 进行反射XSS, 本地文件包含 (未完成)

    3. 对于包含参数的URL，推入sqlmapapi去自动扫描(sqlmapapi工作已完成，并未合并到工具中)

    4. 对于以action,do结尾的URL， 推到struts去扫描，(strtus插件未做)

    5. 对于包含`url`,`wap`,`image`等字段的URL，探测ssrf漏洞，即在vps开放一个HTTP服务，加入有可识别锚点的文件，去替换为参数的请求，(未做)

    6. 一个简陋的WEB界面(无限期推吧...)

    7. 把主函数改个名字

    8. 添加指纹库
