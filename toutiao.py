#!coding=utf-8
##爬取今日头条频道数据
import requests
import json
import random
import time
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)  ###禁止提醒SSL警告
import hashlib
import execjs
from selenium import webdriver
from toutiaoitem import toutiaoitem
from proxies import get_proxy_ip
import re
import html
import urllib
from bs4 import BeautifulSoup
import traceback
import pymysql

class toutiao(object):

    def __init__(self,url, type):
        self.url = url + type + '/';
        self.type = type;
        self.s = requests.session()
        self.page = 0
        self.user_page = 0
        self.search_item_list = []
        self.search_user_list = []
        self.user_artcile_list = []
        headers = {'Accept': '*/*',
                   'Accept-Language': 'zh-CN',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.3; rv:11.0) like Gecko',
                   'Connection': 'Keep-Alive',
                   }
        self.s.headers.update(headers)
        self.channel = re.search('ch/(.*?)/',self.url).group(1)
        
        self.s2 = requests.session()
        headers2 = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
                    'Connection': 'keep-alive',
                    'authority': 'www.toutiao.com',
                    'method': 'GET',
                    'scheme': 'https'
                    }
        self.s2.headers.update(headers2)
        
        self.db = pymysql.connect("localhost", "root", "root", "cb_data");
        self.cursor = self.db.cursor()

    def closes(self):
        self.s.close()

    def get_channel_data(self, page):  #获取数据
        req = self.s.get(url=self.url, verify=False, proxies=get_proxy_ip())
        #print (self.s.headers)
        #print(req.text)
        headers = {'referer': self.url}
        max_behot_time='0'
        signature='.1.hXgAApDNVcKHe5jmqy.9f4U'
        eas = 'A1E56B6786B47FE'
        ecp = '5B7674A7FF2E9E1'
        self.s.headers.update(headers)
        item_list = []
        browser = webdriver.Chrome()
        browser.implicitly_wait(10)
        browser.get(self.url)
        for i in range(0, page):
            try:
                headers = {'referer': self.url};
                self.s.headers.update(headers);
                
                Honey = json.loads(self.get_js());

                eas = Honey['as'];
                ecp = Honey['cp'];
                signature = Honey['_signature'];
                if i > 0:
                    signature = browser.execute_script("return window.TAC.sign("+ max_behot_time +")");
                proxyIp = get_proxy_ip();
                url='https://www.toutiao.com/api/pc/feed/?category={}&utm_source=toutiao&widen=1&max_behot_time={}&max_behot_time_tmp={}&tadrequire=true&as={}&cp={}&_signature={}'.format(self.channel,max_behot_time,max_behot_time,eas,ecp,signature);
                req=self.s.get(url=url, verify=False, proxies=proxyIp);
                time.sleep(random.random() * 2 + 0.5);
                j=json.loads(req.text);
                for k in range(0, len(j['data'])):
                    try:
                        item = toutiaoitem();
                        now=time.time();
                        if j['data'][k]['tag']:
                            if j['data'][k]['tag'] != 'ad' or j['data'][k]['tag'] != 'ad.platform.site':
                                item.title = j['data'][k]['title'];  ##标题
                                item.source = j['data'][k]['source'];  ##作者
                                item.source_url = 'https://www.toutiao.com'+j['data'][k]['source_url'];   ##文章链接
                                item.media_url = 'https://www.toutiao.com'+j['data'][k]['media_url'];  #作者主页
                                item.article_genre = j['data'][k]['article_genre'];  #文章类型
                                try:
                                    item.comments_count = j['data'][k]['comments_count'];  ###评论
                                except:
                                    item.comments_count = 0;

                                item.tag = j['data'][k]['tag'];  ###频道名
                                try:
                                    item.chinese_tag = j['data'][k]['chinese_tag'];   ##频道中文名
                                except:
                                    item.chinese_tag = '';
                                try:
                                    item.label = j['data'][k]['label'];  ## 标签
                                except:
                                    item.label = [];
                                try:
                                    item.abstract = j['data'][k]['abstract'];  ###文章摘要
                                except:
                                    item.abstract = '';
                                behot = int(j['data'][k]['behot_time']);
                                item.behot_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(behot));  ####发布时间
                                item.collect_time = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(now));  ##抓取时间
                                item.item_id = j['data'][k]['item_id'];
                                try:
                                    item.image_list = j['data'][k]['image_list'];
                                except:
                                    item.image_list = [];

                                self.get_article_detail(item, proxyIp);
                                self.save_item(item);
                    except Exception as e:
                        traceback.print_exc();
                max_behot_time = str(j['next']['max_behot_time']);
            except Exception as e:
                traceback.print_exc();

    """
    文章详情
    """
    def get_article_detail(self, item, proxyIp):
        url = 'https://www.toutiao.com/i' + item.item_id
        if item.article_genre == 'article':
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
                'Connection': 'keep-alive',
                'authority': 'www.toutiao.com',
                'referer': 'https://www.toutiao.com/i' + item.item_id + '/',
                'method': 'GET',
                'path': 'a/' + item.item_id + '/',
                'scheme': 'https'
            }
            self.s2.headers.update(headers)
            req = self.s.get(url, proxies=proxyIp)
            #随机休眠几秒
            time.sleep(random.random() * 2 + 0.2)
            resp_data = req.text;
            content = re.findall(r"content:(.+)", resp_data)[0]
            content = html.unescape(content)
            content = re.findall("'(.+)'", content)[0]
            #content = BeautifulSoup(content,'lxml').get_text()
            #更新文章内容
            item.content = content
        return item
    
    """
    存入数据库
    """
    def save_item(self, item):
        if item.content:
            sql = "select * from news where url = '%s'" % (item.source_url);
            self.cursor.execute(sql);
            data = self.cursor.fetchone()
            if data is None:
                sql = "insert into news set title = \
                        '%s',content = '%s',url = '%s',module_level_1 = '%s',news_time = '%s',source = '%s'" %\
                        (item.title, pymysql.escape_string(item.content), pymysql.escape_string(item.source_url), self.type, item.behot_time, item.source);
                try:
                    self.cursor.execute(sql);
                    self.db.commit();
                    print(self.type + " : " + item.source_url + " : " + item.source);
                except:
                    traceback.print_exc();
                    self.db.rollback()
            else:
                if data[8]:
                    print("Url : " + item.source_url + " already exist, skip." + " id : " + str(data[0]));
                else:
                    sql = "update news set source = '%s' where id = '%s'" % (item.source, str(data[0]));
                    try:
                        self.cursor.execute(sql);
                        self.db.commit();
                        print("update source for id : " + str(data[0]));
                    except:
                        traceback.print_exc();
                        self.db.rollback()
        else:
            print("Url : " + item.source_url + " empty content !");

    def get_js(self):  ###大牛破解as ,cp,  _signature  参数的代码，然而具体关系不确定，不能连续爬取
        f = open(r"./toutiao-TAC.sign.js", 'r', encoding='UTF-8')
        line = f.readline()
        htmlstr = ''
        while line:
            htmlstr = htmlstr + line
            line = f.readline()
        ctx = execjs.compile(htmlstr)
        return ctx.call('get_as_cp_signature')

if __name__=='__main__':
    types = ["news_car","news_entertainment","news_sports","news_tech","news_regimen","news_history","news_military","news_travel","news_world","news_baby","news_essay","news_fashion","news_finance","news_food","news_game"];
    url='https://www.toutiao.com/ch/';
    for type in types:
        t=toutiao(url, type)
        t.get_channel_data(1000)
        t.closes()


