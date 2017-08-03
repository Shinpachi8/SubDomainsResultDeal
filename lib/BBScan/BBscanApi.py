#!/usr/bin/env python
# coding=utf-8

from tmp import *

class Args(object):
    # 现在默认一下
    def __init__(self, args):
        self.f = ""
        self.d = ""
        self.crawler = ""
        # host是一个列表
        self.host = args
        # 默认的为True
        self.full_scan = True
        self.timeout = 20
        # 默认爬取C段
        self.network = 24
        # 默认为8进程
        self.p = 8

        # 每个进程有5个线程
        self.t = 5
        # 默认不启用Markdown格式
        self.md = False
        self.no_check404 = False
        self.no_crawl = False
        self.browser = False

def save_report_thread(q_results, file, lock):
    start_time = time.time()
    a_template = template['html']
    # if args.md:
    #     a_template = template['markdown']
    # else:
    #     a_template = template['html']

    t_general = Template(a_template['general'])
    t_host = Template(a_template['host'])
    t_list_item = Template(a_template['list_item'])
    output_file_suffix = a_template['suffix']

    all_results = []
    report_name = os.path.basename(file).lower().replace('.txt', '') \
        + '_' + time.strftime('%Y%m%d_%H%M%S',
                              time.localtime()) + output_file_suffix

    global STOP_ME
    try:
        while not STOP_ME:
            if q_results.qsize() == 0:
                time.sleep(0.1)
                continue

            html_doc = ""
            while q_results.qsize() > 0:
                all_results.append(q_results.get())

            for item in all_results:
                host, results = item
                _str = ""
                for key in results.keys():
                    for _ in results[key]:
                        _str += t_list_item.substitute(
                            {'status': _['status'], 'url': _[
                                'url'], 'title': _['title']}
                        )
                _str = t_host.substitute({'host': host, 'list': _str})
                html_doc += _str

            cost_time = time.time() - start_time
            cost_min = int(cost_time / 60)
            cost_seconds = '%.2f' % (cost_time % 60)
            html_doc = t_general.substitute(
                {'cost_min': cost_min, 'cost_seconds': cost_seconds, 'content': html_doc}
            )

            with codecs.open('report/%s' % report_name, 'w', encoding='utf-8') as outFile:
                outFile.write(html_doc)

        if all_results:
            print '[%s] Scan report saved to report/%s' % (get_time(), report_name)
            if args.browser:
                webbrowser.open_new_tab(
                    os.path.abspath('report/%s' % report_name))
        else:
            lock.acquire()
            print '[%s] No vulnerabilities found on sites in %s.' % (get_time(), file)
            lock.release()

    except Exception, e:
        print '[save_report_thread Exception] %s %s' % (type(e), str(e))
        sys.exit(-1)


def BBscanApi(args):
    # 都放在这应该没有什么问题，主要是使用host这一个参数
    # 但是args应该有这几个参数，默认为""
    if args.f:
        input_files = [args.f]
    elif args.d:
        input_files = glob.glob(args.d + '/*.txt')
    elif args.crawler:
        input_files = ['crawler']
    elif args.host:
        input_files = ['hosts']    # several hosts on command line

    print "f:{}\nd:{}\ncrawler:{}\nhost:{}\t".format(args.f, args.d, args.crawler, args.host)
    ips_to_scan = []    # all IPs to be scanned during current scan

    for file in input_files:
        if args.host:
            lines = [' '.join(args.host)]
            print "lines=>{}".format(lines)
        elif args.f or args.d:
            with open(file) as inFile:
                lines = inFile.readlines()
        try:
            print '[%s] Batch web scan start.' % get_time()
            q_results = multiprocessing.Manager().Queue()
            q_targets = multiprocessing.Manager().Queue()
            lock = multiprocessing.Manager().Lock()
            global STOP_ME
            STOP_ME = False

            threading.Thread(target=save_report_thread,
                             args=(q_results, file, lock)).start()
            print '[%s] Report thread created, prepare target Queue...' % get_time()

            if args.crawler:
                _input_files = glob.glob(args.crawler + '/*.log')
                for _file in _input_files:
                    q_targets.put({'file': _file, 'url': ''})

            if args.host or args.f or args.d:
                q_hosts = Queue.Queue()
                for line in lines:
                    if line.strip():
                        # Works with https://github.com/lijiejie/subDomainsBrute
                        # delimiter "," is acceptable
                        hosts = line.replace(',', ' ').strip().split()
                        for host in hosts:
                            q_hosts.put(host)

                all_threads = []
                for _ in range(20):
                    t = threading.Thread(target=domain_lookup, args=(q_targets, q_hosts, lock))
                    all_threads.append(t)
                    t.start()
                for t in all_threads:
                    t.join()

                if args.network != 32:
                    for ip in ips_to_scan:
                        if ip.find('/') > 0:
                            continue
                        _network = u'%s/%s' % ('.'.join(ip.split('.')
                                                        [:3]), args.network)
                        if _network in ips_to_scan:
                            continue
                        ips_to_scan.append(_network)
                        _ips = ipaddress.IPv4Network(
                            u'%s/%s' % (ip, args.network), strict=False).hosts()
                        for _ip in _ips:
                            _ip = str(_ip)
                            if _ip not in ips_to_scan:
                                ips_to_scan.append(_ip)
                                q_targets.put({'file': '', 'url': _ip})

            print '[%s] %s targets entered Queue.' % (get_time(), q_targets.qsize())
            print '[%s] Create %s sub Processes...' % (get_time(), args.p)
            scan_process = []
            for _ in range(args.p):
                p = multiprocessing.Process(
                    target=batch_scan, args=(q_targets, q_results, lock, args))
                p.daemon = True
                p.start()
                scan_process.append(p)
            print '[%s] %s sub process successfully created.' % (get_time(), args.p)
            for p in scan_process:
                p.join()

        except KeyboardInterrupt, e:
            print '[+] [%s] User aborted, running tasks crashed.' % get_time()
            try:
                while True:
                    q_targets.get_nowait()
            except:
                pass

        except Exception, e:
            print '[__main__.exception] %s %s' % (type(e), str(e))
            traceback.print_exc()

        STOP_ME = True

if __name__ == '__main__':
    args = Args(["s222.dmbj.g.pps.tv", "s305.dmbj.g.pps.tv", "s311.dmbj.g.pps.tv"])
    print args.host
    BBscanApi(args)
