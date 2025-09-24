import requests
import json
import webbrowser
import time
import os
import sys
from urllib.parse import urlencode
from io import StringIO
import contextlib

# 安全设置标准输出编码为UTF-8
try:
    if sys.stdout:
        sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

try:
    import browser_cookie3
    BROWSER_COOKIE_AVAILABLE = True
except ImportError:
    BROWSER_COOKIE_AVAILABLE = False

def fetch_playlist_data(playlist_url, cookie=None):
    """获取歌单数据"""
    try:
        # 设置更完整的User-Agent模拟浏览器请求
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://music.163.com/',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

        # 如果提供了Cookie，则添加到请求头中
        if cookie:
            headers['Cookie'] = cookie
        else:
            # 默认Cookie参数
            headers['Cookie'] = 'appver=2.0.2'

        # 从URL中提取歌单ID
        playlist_id = playlist_url.split('=')[-1]

        # 构造完整的API URL和参数
        api_url = "https://music.163.com/api/playlist/detail"
        params = {
            'id': playlist_id,
            'n': 100000,
            's': 8
        }

        response = requests.get(api_url, headers=headers, params=params)
        response.raise_for_status()

        # 解析JSON数据
        data = response.json()

        # 检查返回码
        if data.get('code') != 200:
            return None, response.status_code

        return data, response.status_code
    except requests.exceptions.RequestException as e:
        return None, getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
    except json.JSONDecodeError as e:
        return None, None

def parse_playlist_tracks(data):
    """解析歌单中的歌曲信息"""
    if not data or 'result' not in data or 'tracks' not in data['result']:
        return []

    tracks = data['result']['tracks']
    track_list = []

    for track in tracks:
        # 获取歌曲名和艺术家
        song_name = track.get('name', '未知歌曲')
        artists = track.get('artists', [])

        # 拼接艺术家名称
        if artists:
            artist_names = ' / '.join([artist.get('name', '') for artist in artists])
            track_info = f"{artist_names} - {song_name}"
        else:
            track_info = song_name

        track_list.append(track_info)

    return track_list

def update_playlist_file(track_list, filename="playlist.txt"):
    """更新playlist.txt文件"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            for i, track in enumerate(track_list, 1):
                f.write(f"{i}. {track}\n")
        return True, f"成功更新 {filename}，共 {len(track_list)} 首歌曲"
    except Exception as e:
        return False, f"写入文件时出错: {e}"

def get_cookie_from_browser():
    """从浏览器自动获取Cookie"""
    if not BROWSER_COOKIE_AVAILABLE:
        return None

    try:
        # 尝试从Firefox获取Cookie
        try:
            firefox_cookies = browser_cookie3.firefox(domain_name='.music.163.com')
            cookie_dict = {cookie.name: cookie.value for cookie in firefox_cookies}

            # 检查是否有必要的Cookie
            if 'MUSIC_U' in cookie_dict:
                # 构造Cookie字符串
                cookie_str = '; '.join([f"{name}={value}" for name, value in cookie_dict.items()])
                return cookie_str
        except Exception:
            pass

        # 尝试从Chrome获取Cookie
        try:
            chrome_cookies = browser_cookie3.chrome(domain_name='.music.163.com')
            cookie_dict = {cookie.name: cookie.value for cookie in chrome_cookies}

            # 检查是否有必要的Cookie
            if 'MUSIC_U' in cookie_dict:
                # 构造Cookie字符串
                cookie_str = '; '.join([f"{name}={value}" for name, value in cookie_dict.items()])
                return cookie_str
        except Exception:
            pass

        return None
    except Exception:
        return None

def update_playlist(playlist_url):
    """更新歌单功能的主函数"""
    output = []
    
    # 验证URL格式
    if not playlist_url.startswith("https://music.163.com/api/playlist/detail?id="):
        output.append("错误: 请输入正确的歌单API链接")
        output.append("格式应为: https://music.163.com/api/playlist/detail?id=歌单ID")
        return "\n".join(output)

    # 初始尝试获取数据
    output.append("正在获取歌单数据...")
    data, status_code = fetch_playlist_data(playlist_url)

    # 检查是否需要登录
    cookie = None
    if not data or (data and data.get('code') == 20001) or status_code == 403:
        output.append("检测到可能需要登录才能访问该歌单")
        # 直接尝试从浏览器获取Cookie，无需用户确认
        cookie = get_cookie_from_browser()

        if cookie:
            output.append("正在使用获取到的Cookie重新获取歌单数据...")
            data, status_code = fetch_playlist_data(playlist_url, cookie)

    if not data:
        output.append("无法获取歌单数据")
        return "\n".join(output)

    # 检查返回码
    if data.get('code') != 200:
        output.append(f"获取歌单数据失败，错误码: {data.get('code')}")
        if data.get('code') == 20001:
            output.append("请确保您已正确登录并提供了有效的Cookie")
        return "\n".join(output)

    output.append("正在解析歌单信息...")
    track_list = parse_playlist_tracks(data)

    if not track_list:
        output.append("未能解析到任何歌曲信息")
        return "\n".join(output)

    output.append(f"成功解析到 {len(track_list)} 首歌曲")

    # 更新playlist.txt文件
    success, message = update_playlist_file(track_list)
    output.append(message)
    
    if success:
        output.append("playlist.txt 更新完成!")
        output.append("\n现在可以运行 organize_playlist.py 来匹配和重命名音乐文件了")
    else:
        output.append("更新playlist.txt失败")
        
    return "\n".join(output)

def main():
    """主函数"""
    print("网易云音乐歌单更新工具")
    print("=" * 40)

    # 获取用户输入的歌单链接
    playlist_url = None
    attempts = 0
    while not playlist_url and attempts < 3:
        try:
            playlist_url = input("请输入网易云音乐歌单链接: ").strip()
            if not playlist_url:
                print("输入不能为空，请重新输入")
                attempts += 1
                time.sleep(0.1)  # 短暂延迟
        except EOFError:
            print("未检测到输入数据")
            return
        except Exception as e:
            print(f"输入错误: {e}")
            attempts += 1
            time.sleep(0.1)  # 短暂延迟

    if not playlist_url:
        print("输入尝试次数过多，程序退出")
        return

    # 调用功能函数
    result = update_playlist(playlist_url)
    print(result)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n操作已取消")
    except Exception as e:
        print(f"\n发生错误: {str(e)}")