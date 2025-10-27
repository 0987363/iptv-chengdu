#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import re
import sys


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
    """
    加载图标数据，如果失败则返回空列表
    图标加载失败不应该阻止整个程序运行
    """
    try:
        print(f"正在获取图标数据: {sourceIcon51ZMT}")
        response = requests.get(sourceIcon51ZMT, verify=False, timeout=30)
        response.raise_for_status()
        
        if not response.content:
            print("⚠️  图标数据为空，将使用默认图标")
            return []
            
        res = response.content
        soup = BeautifulSoup(res, 'lxml')
        m = []

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

        print(f"成功加载 {len(m)} 个图标")
        return m
        
    except requests.exceptions.RequestException as e:
        print(f"⚠️  图标数据获取失败: {e}")
        print("将继续执行，但频道将使用默认图标")
        return []
    except Exception as e:
        print(f"⚠️  解析图标数据时发生错误: {e}")
        print("将继续执行，但频道将使用默认图标")
        return []

def generateM3U8(file):
    """
    生成M3U8文件，包含异常处理
    """
    try:
        print(f"正在生成M3U8文件: {file}")
        with open(file, "w", encoding='utf-8') as f:
            name = '成都电信IPTV - ' + datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
            title = f'#EXTM3U name="{name}" url-tvg="{totalEPG}"\n\n'
            f.write(title)

            total_written = 0
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
                    total_written += 1

        print(f"✅ M3U8文件生成成功，共写入 {total_written} 个频道")
        
    except IOError as e:
        print(f"❌ 文件写入失败: {e}")
        print("请检查文件路径和写入权限")
        print("ERROR: File write failed - GitHub Action will be terminated")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 生成M3U8文件时发生未知错误: {e}")
        print("ERROR: M3U8 generation failed - GitHub Action will be terminated")
        sys.exit(1)

def generateHome():
    generateM3U8("./home/iptv.m3u8")

def main():
    # 加载图标数据
    mIcons = loadIcon()

    # 获取成都组播数据
    try:
        print(f"正在获取成都组播数据: {sourceChengduMulticast}")
        response = requests.get(sourceChengduMulticast, verify=False, timeout=30)
        response.raise_for_status()  # 检查HTTP状态码
        
        if not response.content:
            raise ValueError("获取到的内容为空")
            
        res = response.content
        soup = BeautifulSoup(res, 'lxml')
        
        # 验证页面内容是否有效（检查是否包含表格数据）
        tables = soup.find_all('table')
        if not tables:
            raise ValueError("页面中未找到表格数据，可能页面结构已变化")
            
        # 检查是否有有效的频道数据行
        valid_rows = 0
        for tr in soup.find_all('tr'):
            td = tr.find_all('td')
            if len(td) >= 7 and td[0].string != "序号":
                valid_rows += 1
                
        if valid_rows == 0:
            raise ValueError("未找到有效的频道数据")
            
        print(f"成功获取到 {valid_rows} 条频道数据")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
        print("请检查网络连接或稍后重试")
        print("ERROR: Network request failed - GitHub Action will be terminated")
        sys.exit(1)
    except ValueError as e:
        print(f"❌ 数据验证失败: {e}")
        print("远程数据源可能已变化，请检查数据源")
        print("ERROR: Data validation failed - GitHub Action will be terminated")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 获取成都组播数据时发生未知错误: {e}")
        print("ERROR: Unknown error occurred - GitHub Action will be terminated")
        sys.exit(1)

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

    # 验证是否有足够的频道数据
    total_channels = sum(len(channels) for channels in m.values())
    if total_channels == 0:
        print("❌ 未获取到任何频道数据，无法生成M3U8文件")
        print("ERROR: No channel data found - GitHub Action will be terminated")
        sys.exit(1)
    
    print(f"✅ 数据处理完成，共获取到 {total_channels} 个频道，分布在 {len(m)} 个分组中")
    for group, channels in m.items():
        print(f"   - {group}: {len(channels)} 个频道")

    generateHome()

if __name__ == "__main__":
    try:
        main()
        print("✅ 脚本执行成功完成")
    except SystemExit:
        # 重新抛出SystemExit，保持原有的退出码
        raise
    except Exception as e:
        print(f"❌ 脚本执行过程中发生严重错误: {e}")
        print("ERROR: Critical error occurred - GitHub Action will be terminated")
        import traceback
        traceback.print_exc()
        sys.exit(1)

