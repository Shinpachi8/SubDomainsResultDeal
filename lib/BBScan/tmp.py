#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# A tiny Batch weB vulnerability Scanner
# my[at]lijiejie.com    http://www.lijiejie.com


import urlparse
import requests
import logging
import re
import threading
import Queue
from bs4 import BeautifulSoup
import multiprocessing
import time
from string import Template
import glob
import ipaddress
import os
import webbrowser
import socket
import sys
import ssl
import codecs
import traceback
from dns.resolver import Resolver
from lib.common import get_time, parse_url, decode_response_text
from lib.cmdline import parse_args
from lib.report import template


# SSL error ignored
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context


socket.setdefaulttimeout(None)


class InfoDisScanner(object):
    def __init__(self, timeout=240, args=None):
        self.START_TIME = time.time()
        self.TIME_OUT = timeout
        self.args = args
        self.LINKS_LIMIT = 100      # max number of Folders to scan

        self.full_scan = args.full_scan
        self._init_rules()

        self.url_queue = Queue.Queue()     # all urls to scan
        self.urls_processed = set()        # processed urls
        self.urls_enqueued = set()         # entered queue urls

        self.lock = threading.Lock()

    # reset scanner
    def init_reset(self):
        self.START_TIME = time.time()
        self.url_queue.queue.clear()
        self.urls_processed = set()
        self.urls_enqueued = set()
        self.results = {}
        self.log_file = None
        self._404_status = -1

    # scan from a given URL
    def init_from_url(self, url):
        self.init_reset()
        if not url.find('://') > 0:
            self.url = 'http://' + url
        else:
            self.url = url
        self.schema, self.host, self.path = parse_url(url)
        self.init_final()

    def init_from_log_file(self, log_file):
        self.init_reset()
        self.log_file = log_file
        self.schema, self.host, self.path = self._parse_url_from_file()
        self.load_all_urls_from_file()
        self.init_final()

    #
    def init_final(self):
        if not self.is_port_open():
            return
        self.base_url = '%s://%s' % (self.schema, self.host)
        self.max_depth = self._cal_depth(self.path)[1] + 5
        self.session = requests.session()
        if self.args.no_check404:
            self._404_status = 404
            self.has_404 = True
        else:
            self.check_404()           # check existence of HTTP 404
        if not self.has_404:
            print '[%s] [Warning] %s has no HTTP 404.' % (get_time(), self.host)
        _path, _depth = self._cal_depth(self.path)
        self._enqueue('/')
        self._enqueue(_path)
        if not self.args.no_crawl and not self.log_file:
            self.crawl_index(_path)

    def is_port_open(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(4.0)
            default_port = 443 if self.schema.lower() == 'https' else 80
            host, port = self.host.split(':') if self.host.find(':') > 0 else (self.host, default_port)
            if s.connect_ex((host, int(port))) == 0:
                print '[%s] Scan %s' % (get_time(), self.host)
                return True
            else:
                print '[%s] Fail to connect to %s' % (get_time(), self.host)
                return False
            s.close()
        except Exception, e:
            return False
        finally:
            s.close()

    #
    def _parse_url_from_file(self):
        url = ''
        with open(self.log_file) as infile:
            for line in infile.xreadlines():
                line = line.strip()
                if line and len(line.split()) >= 2:
                    url = line.split()[1]
                    break
        return parse_url(url)

    # calculate depth of a given URL, return tuple (url, depth)
    def _cal_depth(self, url):
        if url.find('#') >= 0:
            url = url[:url.find('#')]    # cut off fragment
        if url.find('?') >= 0:
            url = url[:url.find('?')]    # cut off query string

        if url.startswith('//'):
            return '', 10000    # //www.baidu.com/index.php

        if not urlparse.urlparse(url, 'http').scheme.startswith('http'):
            return '', 10000    # no HTTP protocol

        if url.lower().startswith('http'):
            _ = urlparse.urlparse(url, 'http')
            if _.netloc == self.host:    # same hostname
                url = _.path
            else:
                return '', 10000         # not the same hostname

        while url.find('//') >= 0:
            url = url.replace('//', '/')

        if not url:
            return '/', 1         # http://www.example.com

        if url[0] != '/':
            url = '/' + url

        url = url[: url.rfind('/')+1]

        if url.split('/')[-2].find('.') > 0:
            url = '/'.join(url.split('/')[:-2]) + '/'

        depth = url.count('/')
        return url, depth

    #
    # load urls from rules/*.txt
    def _init_rules(self):
        print "######################################"
        print os.path.abspath(__file__)
        self.text_to_find = []
        self.regex_to_find = []
        self.text_to_exclude = []
        self.regex_to_exclude = []
        self.rules_set = set()

        p_tag = re.compile('{tag="([^"]+)"}')
        p_status = re.compile('{status=(\d{3})}')
        p_content_type = re.compile('{type="([^"]+)"}')
        p_content_type_no = re.compile('{type_no="([^"]+)"}')

        # add by shinpach8
        # find the rules
        _abspath = os.path.split(os.path.abspath(__file__))[0]
        _rule_path = os.path.join(_abspath, 'rules/*.txt')
        #for rule_file in glob.glob('rules/*.txt'):
        for rule_file in glob.glob(_rule_path):
            #print "[init_rules] rule_file\t" + rule_file
            with open(rule_file, 'r') as infile:
                for url in infile.xreadlines():
                    url = url.strip()
            #        print "[init_rules]:\t" +url
                    if url.startswith('/'):
                        _ = p_tag.search(url)
                        tag = _.group(1).replace("{quote}", '"') if _ else ''

                        _ = p_status.search(url)
                        status = int(_.group(1)) if _ else 0

                        _ = p_content_type.search(url)
                        content_type = _.group(1) if _ else ''

                        _ = p_content_type_no.search(url)
                        content_type_no = _.group(1) if _ else ''

                        rule = (url.split()[0], tag, status, content_type, content_type_no)
                        if rule not in self.rules_set:
                            self.rules_set.add(rule)

        re_text = re.compile('{text="(.*)"}')
        re_regex_text = re.compile('{regex_text="(.*)"}')

        _file_path = os.path.join(_abspath,'rules/white.list')
        if not os.path.exists(_file_path):
            return
        for line in open(_file_path):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            _m = re_text.search(line)
            if _m:
                self.text_to_find.append(
                    _m.group(1).decode('utf-8', 'ignore')
                )
            else:
                _m = re_regex_text.search(line)
                if _m:
                    self.regex_to_find.append(
                        re.compile(_m.group(1).decode('utf-8', 'ignore'))
                    )

        _file_path = os.path.join(_abspath, 'rules/black.list')
        if not os.path.exists(_file_path):
            return
        for line in open(_file_path):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            _m = re_text.search(line)
            if _m:
                self.text_to_exclude.append(
                    _m.group(1).decode('utf-8', 'ignore')
                )
            else:
                _m = re_regex_text.search(line)
                if _m:
                    self.regex_to_exclude.append(
                        re.compile(_m.group(1).decode('utf-8', 'ignore'))
                    )

    #
    def _http_request(self, url, timeout=20):
        try:
            if not url:
                url = '/'
            url = self.base_url + url
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 '
                                     '(KHTML, like Gecko) Chrome/38.0.2125.111 Safari/537.36 BBScan/1.2',
                       'Range': 'bytes=0-10240',
                       'Connection': 'keep-alive'
                       }
            resp = self.session.get(url, headers=headers, timeout=(3.0, timeout))
            resp_headers = resp.headers
            status = resp.status_code
            if resp_headers.get('content-type', '').find('text') >= 0 \
                    or resp_headers.get('content-type', '').find('html') >= 0 \
                    or int(resp_headers.get('content-length', '0')) <= 10240:
                html_doc = decode_response_text(resp.content)
            else:
                html_doc = ''
            return status, resp_headers, html_doc
        except:
            return -1, {}, ''

    #
    def check_404(self):
        try:
            try:
                self._404_status, headers, html_doc = self._http_request('/BBScan-404-existence-check')
            except:
                self._404_status, headers, html_doc = -1, {}, ''

            self.has_404 = (self._404_status == 404)
            if not self.has_404:
                self.len_404_doc = len(html_doc)
            return self.has_404
        except Exception, e:
            logging.error('[Check_404] Exception %s' % str(e))

    #
    def _enqueue(self, url):
        url = str(url)
        url_pattern = re.sub('\d+', '{num}', url)
        if url_pattern in self.urls_processed or len(self.urls_processed) >= self.LINKS_LIMIT:
            return False
        else:
            self.urls_processed.add(url_pattern)
        # print url
        for _ in self.rules_set:
            try:
                full_url = url.rstrip('/') + _[0]
            except:
                continue
            if full_url in self.urls_enqueued:
                continue
            url_description = {'prefix': url.rstrip('/'), 'full_url': full_url}
            item = (url_description, _[1], _[2], _[3], _[4])
            self.url_queue.put(item)
            self.urls_enqueued.add(full_url)

        if self.full_scan and url.count('/') >= 3:
            self._enqueue('/'.join(url.split('/')[:-2]) + '/')    # sub folder enqueue

        return True

    #
    def crawl_index(self, path):
        try:
            status, headers, html_doc = self._http_request(path)
            if status != 200:
                try:
                    html_doc = self.session.get(self.url, headers={'Connection': 'close'}).text
                except Exception, e:
                    pass
            soup = BeautifulSoup(html_doc, "html.parser")
            for link in soup.find_all('a'):
                url = link.get('href', '').strip()
                url, depth = self._cal_depth(url)
                if depth <= self.max_depth:
                    self._enqueue(url)
            if self.find_text(html_doc):
                    self.results['/'] = []
                    m = re.search('<title>(.*?)</title>', html_doc)
                    title = m.group(1) if m else ''
                    _ = {'status': status, 'url': '%s%s' % (self.base_url, path), 'title': title}
                    if _ not in self.results['/']:
                        self.results['/'].append(_)

        except Exception, e:
            logging.error('[crawl_index Exception] %s' % str(e))
            traceback.print_exc()

    #
    def load_all_urls_from_file(self):
        try:
            with open(self.log_file) as inFile:
                for line in inFile.xreadlines():
                    _ = line.strip().split()
                    if len(_) == 3 and (_[2].find('^^^200') > 0 or _[2].find('^^^403') > 0 or _[2].find('^^^302') > 0):
                        url, depth = self._cal_depth(url)
                        self._enqueue(url)
        except Exception, e:
            logging.error('[load_all_urls_from_file Exception] %s' % str(e))
            traceback.print_exc()

    #
    def find_text(self, html_doc):
        for _text in self.text_to_find:
            if html_doc.find(_text) > 0:
                return True
        for _regex in self.regex_to_find:
            if _regex.search(html_doc) > 0:
                return True
        return False

    #
    def exclude_text(self, html_doc):
        for _text in self.text_to_exclude:
            if html_doc.find(_text) > 0:
                return False
        for _regex in self.regex_to_exclude:
            if _regex.search(html_doc) > 0:
                return False
        return True

    #
    def _scan_worker(self):
        while self.url_queue.qsize() > 0:
            if time.time() - self.START_TIME > self.TIME_OUT:
                self.url_queue.queue.clear()
                print '[%s] [ERROR] Timed out task: %s' % (get_time(), self.host)
                return
            try:
                item = self.url_queue.get(timeout=0.1)
            except:
                return
            try:
                url_description, tag, code, content_type, content_type_no = item
                prefix = url_description['prefix']
                url = url_description['full_url']
                url = url.replace('{sub}', self.host.split('.')[0])
                if url.find('{hostname_or_folder}') >= 0:
                    _url = url[: url.find('{hostname_or_folder}')]
                    folders = _url.split('/')
                    for _folder in reversed(folders):
                        if _folder not in ['', '.', '..']:
                            url = url.replace('{hostname_or_folder}', _folder)
                            break
                url = url.replace('{hostname_or_folder}', self.host.split(':')[0])
                url = url.replace('{hostname}', self.host.split(':')[0])
                if url.find('{parent}') > 0:
                    if url.count('/') < 2:
                        continue
                    ret = url.split('/')
                    ret[-2] = ret[-1].replace('{parent}', ret[-2])
                    url = '/' + '/'.join(ret[:-1])

            except Exception, e:
                logging.error('[_scan_worker Exception] [1] %s' % str(e))
                continue
            if not item or not url:
                break

            # print '[%s]' % url.strip()
            try:
                status, headers, html_doc = self._http_request(url)
                cur_content_type = headers.get('content-type', '')

                if cur_content_type.find('image/') >= 0:    # exclude image type
                    continue

                if len(html_doc) < 10:    # data too short
                    continue

                if not self.exclude_text(html_doc):    # exclude text found
                    continue

                valid_item = False
                if self.find_text(html_doc):
                    valid_item = True
                else:
                    if status != code and status in [301, 302, 400, 404, 500, 501, 502, 503, 505]:
                        continue
                    if cur_content_type.find('application/json') >= 0 and \
                            not url.endswith('.json'):    # no json
                        continue

                    if tag:
                        if html_doc.find(tag) >= 0:
                            valid_item = True
                        else:
                            continue    # tag mismatch

                    if content_type and cur_content_type.find(content_type) < 0 \
                            or content_type_no and cur_content_type.find(content_type_no) >= 0:
                        continue    # type mismatch

                    if self.has_404 or status != self._404_status:
                        if code and status != code and status != 206:    # code mismatch
                            continue
                        elif code != 403 and status == 403:
                            continue
                        else:
                            valid_item = True

                    if not self.has_404 and status in (200, 206) and url != '/' and not tag:
                        _len = len(html_doc)
                        _min = min(_len, self.len_404_doc)
                        if _min == 0:
                            _min = 10.0
                        if float(_len - self.len_404_doc) / _min > 0.3:
                            valid_item = True

                    if status == 206:
                        if cur_content_type.find('text') < 0 and cur_content_type.find('html') < 0:
                            valid_item = True

                if valid_item:
                    self.lock.acquire()
                    # print '[+] [Prefix:%s] [%s] %s' % (prefix, status, 'http://' + self.host +  url)
                    if prefix not in self.results:
                        self.results[prefix] = []
                    m = re.search('<title>(.*?)</title>', html_doc)
                    title = m.group(1) if m else ''

                    _ = {'status': status, 'url': '%s%s' % (self.base_url, url), 'title': title}
                    if _ not in self.results[prefix]:
                        self.results[prefix].append(_)
                    self.lock.release()

                if len(self.results) >= 10:
                    print '[ERROR] Over 10 vulnerabilities found [%s], seems to be false positives.' % prefix
                    self.url_queue.queue.clear()
            except Exception, e:
                logging.error('[_scan_worker.Exception][2][%s] %s' % (url, str(e)))
                traceback.print_exc()

    #
    def scan(self, threads=6):
        try:
            threads_list = []
            for i in range(threads):
                t = threading.Thread(target=self._scan_worker)
                threads_list.append(t)
                t.start()
            for t in threads_list:
                t.join()
            for key in self.results.keys():
                if len(self.results[key]) > 10:    # Over 10 URLs found under this folder: false positives
                    del self.results[key]
            return self.host, self.results
        except Exception, e:
            print '[scan exception] %s' % str(e)
        finally:
            self.session.close()


def batch_scan(q_targets, q_results, lock, args):
        s = InfoDisScanner(args.timeout*60, args=args)
        while True:
            try:
                target = q_targets.get(timeout=1.0)
            except:
                break
            _url = target['url']
            _file = target['file']

            if _url:
                s.init_from_url(_url)
            else:
                if os.path.getsize(_file) == 0:
                    continue
                s.init_from_log_file(_file)
                if s.host == '':
                    continue

            host, results = s.scan(threads=args.t)
            if results:
                q_results.put((host, results))
                lock.acquire()
                for key in results.keys():
                    for url in results[key]:
                        print '[+] [%s] %s' % (url['status'], url['url'])
                lock.release()


def save_report_thread(q_results, file):
        start_time = time.time()
        if args.md:
            a_template = template['markdown']
        else:
            a_template = template['html']

        t_general = Template(a_template['general'])
        t_host = Template(a_template['host'])
        t_list_item = Template(a_template['list_item'])
        output_file_suffix = a_template['suffix']

        all_results = []
        report_name = os.path.basename(file).lower().replace('.txt', '') \
            + '_' + time.strftime('%Y%m%d_%H%M%S', time.localtime()) + output_file_suffix

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
                                {'status': _['status'], 'url': _['url'], 'title': _['title']}
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
                    webbrowser.open_new_tab(os.path.abspath('report/%s' % report_name))
            else:
                lock.acquire()
                print '[%s] No vulnerabilities found on sites in %s.' % (get_time(), file)
                lock.release()

        except Exception, e:
            print '[save_report_thread Exception] %s %s' % (type(e), str(e))
            sys.exit(-1)


def domain_lookup(q_targets, q_hosts, lock, ips_to_scan):
    r = Resolver()
    r.timeout = r.lifetime = 8.0
    while True:
        try:
            host = q_hosts.get(timeout=0.1)
        except:
            break
        _schema, _host, _path = parse_url(host)
        #print "_schema:{0}\t_host:{1}\t_path:{2}".format(_schema, _host, _path)
        #print _host.split(":")[0]
        try:
            m = re.search('\d+\.\d+\.\d+\.\d+', _host.split(':')[0])
            if m:
                q_targets.put({'file': '', 'url': host})
                ips_to_scan.append(m.group(0))
                #print "in try->if"
            else:
                # 无论查不查的到都将这个url放在target中
                q_targets.put({'file': '', 'url': host})
                answers = r.query(_host.split(':')[0])
                if answers:
                    for _ in answers:
                        ips_to_scan.append(_.address)
        except Exception, e:
            lock.acquire()
            print '[%s][Warning] Invalid domain: [%s]' % (get_time(), host)
            print str(e)
            lock.release()


if __name__ == '__main__':
    args = parse_args()
    #print args.host
    #print type(args.host)
    #lines = [" ".join(args.host)]
    #print "{}".format(lines)
    #assert args.crawler is None
    #sys.exit(-1)

    if args.f:
        input_files = [args.f]
    elif args.d:
        input_files = glob.glob(args.d + '/*.txt')
    elif args.crawler:
        input_files = ['crawler']
    elif args.host:
        input_files = ['hosts']    # several hosts on command line

    ips_to_scan = []    # all IPs to be scanned during current scan

    for file in input_files:
        if args.host:
            lines = [' '.join(args.host)]
        elif args.f or args.d:
            with open(file) as inFile:
                lines = inFile.readlines()
        try:
            print '[%s] Batch web scan start.' % get_time()
            q_results = multiprocessing.Manager().Queue()
            q_targets = multiprocessing.Manager().Queue()
            lock = multiprocessing.Manager().Lock()
            STOP_ME = False

            threading.Thread(target=save_report_thread, args=(q_results, file)).start()
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
                    t = threading.Thread(target=domain_lookup)
                    all_threads.append(t)
                    t.start()
                for t in all_threads:
                    t.join()

                if args.network != 32:
                    for ip in ips_to_scan:
                        if ip.find('/') > 0:
                            continue
                        _network = u'%s/%s' % ('.'.join(ip.split('.')[:3]), args.network)
                        if _network in ips_to_scan:
                            continue
                        ips_to_scan.append(_network)
                        _ips = ipaddress.IPv4Network(u'%s/%s' % (ip, args.network), strict=False).hosts()
                        for _ip in _ips:
                            _ip = str(_ip)
                            if _ip not in ips_to_scan:
                                ips_to_scan.append(_ip)
                                q_targets.put({'file': '', 'url': _ip})

            print '[%s] %s targets entered Queue.' % (get_time(), q_targets.qsize())
            print '[%s] Create %s sub Processes...' % (get_time(), args.p)
            scan_process = []
            for _ in range(args.p):
                p = multiprocessing.Process(target=batch_scan, args=(q_targets, q_results, lock, args))
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
