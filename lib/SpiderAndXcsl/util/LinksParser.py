#!/usr/bin/env python
# coding=utf-8

import urlparse
from bs4 import BeautifulSoup

def get_baseurl(link):
    netloc = urlparse.urlparse(link).netloc
    if netloc:
        split_url = link.split(netloc)
        baseurl = '%s%s' % (split_url[0], netloc)
        return baseurl


class LinksParser(object):
    """docstring for link_parser"""
    def __init__(self, html_content):
        super(LinksParser, self).__init__()
        self.html_content = html_content
        self.url_links = {
            'a':[],
            'link':[],
            'img':[],
            'script':[]
        }
        self.url = self.html_content.url
        self.baseurl = get_baseurl(self.url)
        self.soup = BeautifulSoup(self.html_content.text, 'lxml')

    def complet_url(self, link):
        if link.startswith('/') or link.startswith('.'):
            return urlparse.urljoin(self.baseurl, link)
        elif link.startswith('http') or link.startswith('https'):
            return link
        elif link.startswith('#'): # 为了兼容某些变态的URI模式
            return urlparse.urljoin(self.url, link)
        else:
            return False

    def getall(self):
        self.get_tag_a()
        self.get_tag_link()
        self.get_tag_img()
        self.get_tag_script()
        # links 去重
        for child in self.url_links.keys():
            self.url_links[child] = list(set(self.url_links[child]))
        return {self.url : self.url_links}

    def get_tag_a(self):
        # 处理A链接
        for tag in self.soup.find_all('a'):
            if tag.attrs.has_key('href'):
                link = tag.attrs['href']
                # link = urlparse.urldefrag(tag.attrs['href'])[0] # 处理掉#tag标签信息
                complet_link = self.complet_url(link.strip())
                if complet_link:
                    self.url_links['a'].append(complet_link)
        return self.url_links

    def get_tag_link(self):
        # 处理link链接资源
        for tag in self.soup.find_all('link'):
            if tag.attrs.has_key('href'):
                link = tag.attrs['href']
                complet_link = self.complet_url(link.strip())
                if complet_link:
                    self.url_links['link'].append(complet_link)
        return self.url_links

    def get_tag_img(self):
        # 处理img链接资源
        for tag in self.soup.find_all('img'):
            if tag.attrs.has_key('src'):
                link = tag.attrs['src']
                complet_link = self.complet_url(link.strip())
                if complet_link:
                    self.url_links['img'].append(complet_link)
        return self.url_links

    def get_tag_script(self):
        # 处理script链接资源
        for tag in self.soup.find_all('script'):
            if tag.attrs.has_key('src'):
                link = tag.attrs['src']
                complet_link = self.complet_url(link.strip())
                if complet_link:
                    self.url_links['script'].append(complet_link)
        return self.url_links
