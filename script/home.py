#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import re


# 配置常量
sourceIcon51ZMT = "https://epg.51zmt.top:8001"
sourceChengduMulticast = "https://epg.51zmt.top:8001/sctvmulticast.html"
homeLanAddress = "http://192.168.20.40:5140"
catchupBaseUrl = "http://192.168.20.40:5140"
totalEPG = "https://epg.51zmt.top:8001/e.xml,https://epg.112114.xyz/pp.xml"

# 分组配置
groupCCTV = ["CCTV", "CETV", "CGTN"]
groupWS = ["卫视"]
groupSC = ["SCTV", "四川", "CDTV", "熊猫", "峨眉", "成都"]
group4K = ["4K"]
listUnused = ["单音轨", "画中画", "热门", "直播室", "爱", "92"]


index = 1
def getID():
    global index
    index = index + 1
    return index - 1

def setID(i):
    global index
    if i > index:
        index = i + 1
    return index

def isIn(items, v):
    for item in items:
        if item in v:
            return True
    return False

def filterCategory(v):
    """
    返回频道名匹配的所有分组
    一个频道可以同时属于多个分组
    """
    categories = []
    
    if isIn(groupCCTV, v):
        categories.append("CCTV")
    if isIn(groupWS, v):
        categories.append("卫视")
    if isIn(group4K, v):
        categories.append("4K")
    if isIn(groupSC, v):
        categories.append("四川")
    
    # 如果没有匹配任何分组，则归类为"其他"
    if not categories:
        categories.append("其他")
    
    return categories

def findIcon(m, id):
    for v in m:
        if v["name"] == id:
            return urljoin(sourceIcon51ZMT, v["icon"])
    return ""

def buildCatchupSource(rtsp_url, original_url):
    """
    构建回看源URL
    从rtsp URL中提取主机地址和路径部分，与catchupBaseUrl拼接
    例如: rtsp://182.139.235.40/PLTV/88888896/224/3221228807/10000100000000060000000003732597_0.smil
    提取主机: 182.139.235.40
    提取路径: /PLTV/88888896/224/3221228807/10000100000000060000000003732597_0.smil
    """
    if not rtsp_url or not rtsp_url.startswith("rtsp://"):
        return ""

    # 从rtsp URL中提取主机地址和路径部分
    url_without_protocol = rtsp_url[7:]  # 移除 "rtsp://"
    path_start = url_without_protocol.find("/")
    if path_start == -1:
        return ""

    rtsp_host = url_without_protocol[:path_start]  # 获取主机地址，如 182.139.235.40
    rtsp_path = url_without_protocol[path_start:]  # 获取路径部分，如 /PLTV/...smil

    # 构建完整的回看源URL，使用动态提取的主机地址
    catchup_source = f"{catchupBaseUrl}/rtsp/{rtsp_host}{rtsp_path}?playseek=${{(b)yyyyMMddHHmmss}}-${{(e)yyyyMMddHHmmss}}"

    return catchup_source

def loadIcon():
    res = requests.get(sourceIcon51ZMT, verify=False).content
    m = []
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
    with open(file, "w", encoding='utf-8') as f:
        name = '成都电信IPTV - ' + datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        title = f'#EXTM3U name="{name}" url-tvg="{totalEPG}"\n\n'
        f.write(title)

        for k, v in m.items():
            for c in v:
                if "dup" in c:
                    continue

                # 构建回看源URL
                catchup_source = buildCatchupSource(c["rtsp_url"], c["address"])

                # 生成M3U8条目，添加回看参数
                line = (f'#EXTINF:-1 tvg-logo="{c["icon"]}" tvg-id="{c["id"]}" '
                       f'tvg-name="{c["name"]}" group-title="{k}" '
                       f'catchup="default" catchup-source="{catchup_source}",{c["name"]}\n')
                line2 = f'{homeLanAddress}/rtp/{c["address"]}?FCC=182.139.234.40:8027\n'

                f.write(line)
                f.write(line2)

    print("Build m3u8 success.")

def generateHome():
    generateM3U8("./home/iptv.m3u8")

def main():
    # 加载图标数据
    mIcons = loadIcon()

    # 获取成都组播数据
    res = requests.get(sourceChengduMulticast, verify=False).content
    soup = BeautifulSoup(res, 'lxml')

    global m
    m = {}

    for tr in soup.find_all(name='tr'):
        td = tr.find_all(name='td')
        if len(td) < 7 or td[0].string == "序号":
            continue

        name = td[1].string
        if isIn(listUnused, name):
            continue

        setID(int(td[0].string))

        # 清理频道名称
        name = name.replace('超高清', '').replace('高清', '').replace('-', '').strip()

        groups = filterCategory(name)  # 现在返回分组列表
        icon = findIcon(mIcons, name)

        # 提取rtsp URL
        rtsp_url = td[6].string if td[6].string else ""

        # 创建频道信息对象
        channel_info = {
            "id": td[0].string,
            "name": name,
            "address": td[2].string,
            "rtsp_url": rtsp_url,
            "ct": True,
            "icon": icon
        }

        # 将频道添加到所有匹配的分组中
        for group in groups:
            if group not in m:
                m[group] = []
            m[group].append(channel_info)

    generateHome()

if __name__ == "__main__":
    main()

