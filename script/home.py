#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import m3u8
import sys
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import strict_rfc3339
import re


#with open('./sctvmulticast.html') as f:
#   res=f.read()

sourceTvboxIptv="https://raw.githubusercontent.com/gaotianliuyun/gao/master/list.txt"
sourceIcon51ZMT="http://epg.51zmt.top:8000"
sourceChengduMulticast="http://epg.51zmt.top:8000/sctvmulticast.html"
homeLanAddress="http://192.168.20.34:4000"

def appendOnlineIptvFromTvbox(listIptv):
    onlineIptv = requests.get(sourceTvboxIptv).content
    lines = onlineIptv.splitlines()

    for line in lines:
        line=line.decode('utf-8')
        groupMatch = re.search(r'(.+),#genre#', line)
        if groupMatch:
            g = groupMatch.group(1)
            if g not in listIptv:
                listIptv[g] = []
        else:
            v=line.split(',')
            listIptv[g].extend([{"name": v[0], "address": v[1]}])


def isIn(items, v):
    for item in items:
        if item in v:
            return True

def filterCategory(v):
    listCCTV=["CCTV", "CETV", "CGTN"]
    listSC=[ "卫视"]
    listTV=["SCTV", "四川", "CDTV", "熊猫", "峨眉", "成都"]

    if isIn(listCCTV, v):
        return "CCTV"
    elif isIn(listSC, v):
        return "卫视"
    elif isIn(listTV, v):
        return "四川"
    else:
        return "其他"

def findIcon(m, id):
    for v in m:
        if v["name"] == id:
            return urljoin(sourceIcon51ZMT, v["icon"])
            #return 'http://epg.51zmt.top:8000/' + v["icon"]

    return ""


def loadIcon():
    res = requests.get(sourceIcon51ZMT).content
    m=[]
    #res=""
    #with open('./index.html') as f:
    #    res=f.read()

    soup = BeautifulSoup(res, 'lxml')

    for tr in soup.find_all('tr'):
        td = tr.find_all('td')
        if len(td) < 4:
            continue

        href = ""
        for a in td[0].find_all('a', href=True): 
            if a["href"] == "#":
                continue
            href = a["href"]

        if href != "":
            m.append({"id": td[3].string, "name": td[2].string, "icon": href})

    return m

def generateM3U8(file):
    file=open(file, "w")
    name = '成都电信IPTV - ' + strict_rfc3339.now_to_rfc3339_utcoffset()
    title = '#EXTM3U name=\"' + name + '\"' + ' url-tvg=\"http://epg.51zmt.top:8000/e.xml,https://epg.112114.xyz/pp.xml\"\n\n'
    file.write(title)

    for c in m:
        line = '#EXTINF:-1 tvg-logo="%s" tvg-id="%s" tvg-name="%s" group-title="%s",%s\n' % (c["icon"], c["id"], c["name"], c["tag"], c["name"])
        file.write(line)
        line = homeLanAddress + '/rtp/' + c["address"] + "\n"
        file.write(line)

    file.close()

def generateTXT(file):
    groups={}
    for c in m:
        if c["tag"] not in groups:
            groups[c["tag"]] = []
        groups[c["tag"]].extend([c])

    appendOnlineIptvFromTvbox(groups)

    file=open(file, "w")
    for k, v in groups.items():
        line = '%s,#genre#\n' % (k)
        file.write(line)

        for c in v:
            line = '%s,%s/rtp/%s\n' % (c["name"], homeLanAddress, c["address"])
            if "ct" not in c:
                line = '%s,%s\n' % (c["name"], c["address"])

            file.write(line)

    file.close()


def generateHome():
    generateM3U8("./home/iptv.m3u8")
    generateTXT("./home/iptv.txt")


#exit(0)


res = requests.get(sourceChengduMulticast).content
soup = BeautifulSoup(res, 'lxml')
m=[]
for tr in soup.find_all(name='tr'):
    td = tr.find_all(name='td')
    if td[0].string == "序号":
        continue

    m.append({"id": td[0].string, "name": td[1].string, "address": td[2].string, "ct": True})


listUnused=["单音轨", "画中画", "热门", "直播室", "爱", "92"]
for c in m[:]:
    if isIn(listUnused, c["name"]):
        m.remove(c)
    else:
        c["name"]=c["name"].replace('超高清', '').replace('高清', '').replace('-', '').strip()



mIcons = loadIcon()
for c in m:
    c["tag"] = filterCategory(c["name"])
    c["icon"] = findIcon(mIcons, c["name"])
        

generateM3U8("./m3u8/chengdu.m3u8")
generateHome()




#res = requests.get("https://raw.githubusercontent.com/iptv-org/iptv/master/streams/hk.m3u")

