import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import sys
import os
import threading
import requests
import json
import webbrowser
import time
import unicodedata
import string
import difflib
import re
from urllib.parse import urlencode
from io import StringIO
import contextlib

# 尝试导入browser_cookie3，如果不可用则设置标志
try:
    import browser_cookie3
    BROWSER_COOKIE_AVAILABLE = True
except ImportError:
    BROWSER_COOKIE_AVAILABLE = False

# 安全设置标准输出编码为UTF-8
try:
    if sys.stdout:
        sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# 支持的音频文件扩展名
SUPPORTED_FORMATS = ('.flac', '.mp3', '.m4a', '.wav', '.ogg', '.fla')

def get_resource_path(relative_path):
    """获取资源文件的绝对路径，处理PyInstaller打包后的情况"""
    try:
        # PyInstaller创建临时文件夹，并将路径存储在sys._MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# ==================== 更新歌单功能 ====================
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
        output.append("\n现在可以运行 命名排序 功能来匹配和重命名音乐文件了")
    else:
        output.append("更新playlist.txt失败")
        
    return "\n".join(output)

# ==================== 命名排序功能 ====================
def normalize_text(text):
    """文本标准化处理（增强乱码清理）"""
    if not isinstance(text, str):
        return text

    # 替换常见中日文特殊字符为ASCII等价
    special_replaces = {
        '〜': '~', '～': '~', 'ー': '-', 'ｰ': '-', '（': '(', '）': ')',
        '「': '[', '」': ']', '【': '[', '】': ']', '｛': '{', '｝': '}',
        '“': '"', '”': '"', '‘': "'", '’': "'", '・': '.', '。': '.'
    }
    for orig, repl in special_replaces.items():
        text = text.replace(orig, repl)

    # 音调处理 (降噪处理)
    normalized_chars = []
    for char in text:
        try:
            # NFC规范化
            normalized = unicodedata.normalize('NFC', char)
            # 转换为小写
            if normalized.isalpha():
                normalized = normalized.lower()
            normalized_chars.append(normalized)
        except:
            normalized_chars.append(char)

    text = ''.join(normalized_chars)

    # 移除变音符记号
    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if not unicodedata.combining(c)
    )

    # 转换全角字符为半角
    fullwidth_ranges = [
        (0xFF01, 0xFF0F),  # 全角标点
        (0xFF1A, 0xFF20),  # 全角符号
        (0xFF3B, 0xFF40),  # 全角括弧
        (0xFF5B, 0xFF5E)  # 全角运算符
    ]
    for start, end in fullwidth_ranges:
        for code in range(start, end + 1):
            half_code = code - 0xFEE0
            if 0x21 <= half_code <= 0x7E:
                text = text.replace(chr(code), chr(half_code))

    # ============ 关键修复1：改进乱码清理 ============
    # 清理非常用符号和乱码字符
    text = re.sub(r'[^\w\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\s\(\)\-\~\.]', '', text)
    # 合并连续空格
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def extract_core_title(title):
    """提取标题核心部分（增强乱码处理）"""
    if not title:
        return ""

    if not isinstance(title, str):
        return str(title)

    # 移除常见模式的正则表达式
    patterns = [
        r'\(.*?\)',  # 普通括号内容
        r'\{.*?\}',  # 花括号内容
        r'\[.*?\]',  # 方括号内容
        r'【.*?】',  # 中日文方括号
        r'（.*?）',  # 中日文括号
        r'\sfeat\..*?$',  # feat信息
        r'\sft\..*?$',  # ft. 信息
        r'\s翻自.*?$',  # 翻唱信息
        r'\scover.*?$',  # cover信息
        r'(-?\s?remix( version)?)$',  # remix修饰
        r'(piano ver\.?)$',  # 钢琴版
        r'(acoustic)\s*$',  # 原音版
        r'(live)\s*$',  # 现场版
        r'(\[.*\])\s*$',  # 额外标签
        r'^\d+\s*[-_\.]?\s*',  # 前置数字标号
        r'^[\(\[]\s*未?匹配\s*[\)\]]',  # 已有的未匹配标记
    ]

    for pattern in patterns:
        title = re.sub(pattern, '', title, flags=re.IGNORECASE)

    # ============ 关键修复2：移除乱码和非文本字符 ============
    title = re.sub(r'[^\w\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\s]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()

    # 清理残留的括号
    unwanted_brackets = ['[', ']', '{', '}', '(', ')', '（', '）', '【', '】']
    for bracket in unwanted_brackets:
        if title.startswith(bracket) and title.endswith(bracket):
            title = title[1:-1].strip()

    return title

def advanced_similarity(s1, s2):
    """多维度文本相似度计算（添加日语假名规范化）"""
    s1 = str(s1) if not isinstance(s1, str) else s1
    s2 = str(s2) if not isinstance(s2, str) else s2

    # ============ 关键修复3：日语字符规范化处理 ============
    if bool(re.search(r'[\u3040-\u30ff]', s1 + s2)):
        # 片假名转平假名
        s1 = re.sub(r'[ァ-ヺ]', lambda x: chr(ord(x.group(0)) - 96), s1)
        s2 = re.sub(r'[ァ-ヺ]', lambda x: chr(ord(x.group(0)) - 96), s2)
        # 去除模糊字符
        s1 = re.sub(r'[ゔゕゖゝゞゟ]', '', s1)
        s2 = re.sub(r'[ゔゕゖゝゞゟ]', '', s2)

    # 快速检查相同情况
    if s1 == s2:
        return 1.0

    # 标准化处理
    s1 = s1.lower().strip()
    s2 = s2.lower().strip()

    # 核心部分提取
    core1 = extract_core_title(s1)
    core2 = extract_core_title(s2)

    # 核心匹配检查
    if core1 and core2:
        if core1 == core2:
            return 0.95

        if core1 in s2 or s1 in s2 or core2 in s1:
            return 0.85

    # 使用Python内建的SequenceMatcher
    matcher = difflib.SequenceMatcher(None, s1, s2)
    return matcher.ratio()

def improved_fuzzy_match(query, title, threshold=0.72):
    """改进的模糊匹配算法（降低阈值）"""
    # ============ 关键修复4：降低匹配阈值 ============
    adjusted_threshold = max(0.65, threshold)  # 最低降至0.65

    query = str(query)
    title = str(title)

    # 0. 完全匹配
    if query == title:
        return (title, "exact")

    # 1. 标准化处理
    q_norm = normalize_text(query)
    t_norm = normalize_text(title)

    # 2. 核心部分匹配
    q_core = extract_core_title(q_norm)
    t_core = extract_core_title(t_norm)

    if q_core == t_core:
        return (title, "core")

    # 3. 相互包含检查
    if q_core in t_norm or q_norm in t_norm:
        return (title, f"包含核心({q_core}在{title[:20]}中)")

    if t_core in q_norm:
        return (title, "反包含")

    # 4. 相似度匹配
    similarity_score = advanced_similarity(q_norm, t_norm)
    if similarity_score >= adjusted_threshold:  # 使用调整后的阈值
        return (title, f"相似度:{similarity_score:.2f}")

    # 5. 子序列匹配
    matcher = difflib.SequenceMatcher(None, q_norm, t_norm)
    matching_block = matcher.find_longest_match(0, len(q_norm), 0, len(t_norm))
    if matching_block.size > 0:
        min_length = min(len(q_norm), len(t_norm)) * 0.5
        if matching_block.size >= min_length:
            return (title, "公共子串")

    return (None, "")

def read_playlist(playlist_file):
    """读取播放列表文件并标准化处理"""
    playlist = []

    try:
        with open(playlist_file, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                clean_line = line.strip()
                if not clean_line:
                    continue

                # 匹配多种格式：数字.标题
                match = re.match(r'^\s*\d+\.\s*(.+)', clean_line)
                if match:
                    playlist.append(match.group(1))
                # 匹配 - 标题格式
                elif re.match(r'^\s*-', clean_line):
                    playlist.append(re.sub(r'^\s*-\s*', '', clean_line))
                # 其他格式直接添加
                else:
                    playlist.append(clean_line)
    except Exception as e:
        return []

    # 去除重复项
    seen = set()
    unique_playlist = []
    for title in playlist:
        norm_title = normalize_text(title)
        if norm_title and norm_title not in seen:
            seen.add(norm_title)
            unique_playlist.append(norm_title)

    return unique_playlist

def read_song_metadata(file_path):
    """从文件名提取元数据-数据处理"""
    filename = os.path.splitext(os.path.basename(file_path))[0]

    # 清理文件名：去除前缀数字和标识
    clean_filename = re.sub(r'^\d+\s*[-_\.]?\s*', '', filename)  # 数字前缀
    clean_filename = re.sub(r'\(\s*Not Found\s*\)', '', clean_filename, flags=re.IGNORECASE)  # (Not Found)
    clean_filename = re.sub(r'\（\s*未找到\s*\）', '', clean_filename)  # (未找到)
    clean_filename = re.sub(r'\s*\[Not Matched\]', '', clean_filename, flags=re.IGNORECASE)  # [Not Matched]

    # 分离标题和艺术家
    patterns_to_try = [
        r'^(.*?)\s*[-~–—]{1,3}\s*(.*?)$',  # 艺术家 - 标题
        r'^(.*?)\s*[\(（]\s*(.*?)\s*[\)）]$',  # 艺术家 (标题)
        r'^(.*?)\s{2,}(.*?)$',  # 艺术家    标题
        r'^(.*?)\s*by\s*(.*?)$',  # 标题 by 艺术家
        r'^(.*?)\s*-\s*(.*?)$'  # 标题 - 艺术家（备选）
    ]

    title, artist = clean_filename, None

    for pattern in patterns_to_try:
        match = re.search(pattern, clean_filename, re.IGNORECASE)
        if match:
            groups = match.groups()
            # 通常第一个为艺术家，第二个为标题
            if len(groups) >= 2:
                possible_title = groups[1]
                if len(possible_title) > 0:  # 确保有意义的标题
                    title = possible_title.strip()
                    artist = groups[0].strip()
                    break

    # 返回原始文件名作为标题以便保持文件命名结构
    return {
        'file_path': file_path,
        'original_filename': os.path.basename(file_path),
        'clean_title': normalize_text(title),
        'original_title': title,
        'display_title': filename,  # 用于显示的原文件名
        'artist': artist
    }

def match_songs(songs, playlist_titles, threshold=0.72):
    """
    核心匹配逻辑
    """
    matched = []  # 存储匹配的信息 (位置, 文件信息)
    unmatched = []  # 存储未匹配的信息

    output = []
    output.append(f"\n🔍 开始处理 {len(songs)} 首歌曲...\n")

    # 处理每个歌曲文件
    for file_info in songs.values():
        primary_title = file_info['clean_title']
        if not primary_title:
            unmatched.append(file_info)
            output.append(f"  ❌ 无法处理: {file_info['display_title']}")
            continue

        output.append(f"处理: {file_info['display_title'][:50]}...")
        best_score = 0.0
        best_match = None
        match_method = ""
        match_position = 0

        # 在播放列表中查找匹配
        for idx, pl_title in enumerate(playlist_titles):
            matched_title, method = improved_fuzzy_match(primary_title, pl_title, threshold)

            score = 0.0
            if method:
                if method.startswith("相似度:"):
                    score = float(method.split(':')[1])
                elif method in ("exact", "core"):
                    score = 1.0
                elif method.startswith("包含核心"):
                    score = 0.85
                elif method == "反包含":
                    score = 0.8
                elif method == "公共子串":
                    score = 0.75

            # 更新最佳匹配
            if score > best_score:
                best_score = score
                best_match = matched_title
                match_method = method
                match_position = idx + 1  # 位置从1开始

        # 处理匹配结果
        if best_match and best_score > 0:
            matched.append({
                'position': match_position,
                'method': match_method,
                'file_info': file_info
            })
            output.append(f"  ✅ 匹配 ({match_method}) -> 播放列表第 {match_position} 首: '{best_match}'")
        else:
            unmatched.append(file_info)
            output.append(f"  ❌ 未匹配")

    return matched, unmatched, "\n".join(output)

def rename_files_in_place(matched, unmatched):
    """在当前目录直接重命名文件"""
    # 重命名计数器
    renamed_count = 0
    skipped_count = 0
    output = []

    # ============ 检查重复排序并自动填补空位 ============
    if matched:
        # 按照原始位置排序
        matched.sort(key=lambda x: x['position'])

        # 检查是否有重复的序号，并重新分配连续序号
        positions = [m['position'] for m in matched]
        unique_positions = sorted(list(set(positions)))

        # 重新分配连续的序号（从1开始）
        for i, match_info in enumerate(matched):
            match_info['position'] = i + 1

        output.append(f"\n📋 已重新分配序号，确保连续唯一: 共 {len(matched)} 个文件")
    # ============ 检查结束 ============

    output.append("\n正在处理匹配文件:")
    for match_info in matched:
        file_info = match_info['file_info']
        old_path = file_info['file_path']

        # 提取文件扩展名
        basename, ext = os.path.splitext(file_info['original_filename'])

        # 新文件名：位置_原始文件名
        new_name = f"{match_info['position']:03d}_{file_info['original_filename']}"
        new_path = os.path.join(os.path.dirname(old_path), new_name)

        # 检查是否已经重命名过
        if file_info['original_filename'].startswith(f"{match_info['position']:03d}_"):
            output.append(f"  ⚙ 已处理: {new_name}")
            skipped_count += 1
            continue

        # 检查新文件名是否已存在
        if os.path.exists(new_path):
            # 生成唯一后缀
            suffix = 1
            while True:
                temp_name = f"{match_info['position']:03d}_{suffix}_{file_info['original_filename']}"
                temp_path = os.path.join(os.path.dirname(old_path), temp_name)
                if not os.path.exists(temp_path):
                    new_name = temp_name
                    new_path = temp_path
                    break
                suffix += 1

        # 重命名文件
        try:
            os.rename(old_path, new_path)
            output.append(f"  ✓ {file_info['original_filename'][:30]} -> {new_name[:37]}")
            renamed_count += 1
        except Exception as e:
            output.append(f"  ✗ 无法重命名 {file_info['original_filename']}: {str(e)}")
            skipped_count += 1

    output.append("\n正在处理未匹配文件:")
    for file_info in unmatched:
        old_path = file_info['file_path']
        old_name = file_info['original_filename']
        basename, ext = os.path.splitext(old_name)

        # 检查是否已有标记
        unmatched_prefixes = ['(未匹配)', '（未匹配）', '[未匹配]', '（未找到）', '(unmatched)']
        if any(old_name.startswith(prefix) for prefix in unmatched_prefixes):
            output.append(f"  ➖ 已跳过: {old_name} (已标记)")
            skipped_count += 1
            continue

        # 新文件名：统一使用中文标记
        new_name = '（未匹配）' + old_name
        new_path = os.path.join(os.path.dirname(old_path), new_name)

        # 检查新文件名是否已存在
        if os.path.exists(new_path):
            # 生成唯一后缀
            suffix = 1
            while True:
                temp_name = f"（未匹配）_{suffix}_{old_name}"
                temp_path = os.path.join(os.path.dirname(old_path), temp_name)
                if not os.path.exists(temp_path):
                    new_name = temp_name
                    new_path = temp_path
                    break
                suffix += 1

        # 重命名文件
        try:
            os.rename(old_path, new_path)
            output.append(f"  ⚠ {old_name[:27]} -> {new_name[:37]}")
            renamed_count += 1
        except Exception as e:
            output.append(f"  ✗ 无法重命名 {old_name}: {str(e)}")
            skipped_count += 1

    output.append(f"\n处理完成: 重命名 {renamed_count} 个文件, 跳过 {skipped_count} 个")
    return "\n".join(output)

def get_valid_songs(directory):
    """获取指定目录中的所有有效歌曲（支持.fla）"""
    songs = {}
    file_count = 0

    output = []
    output.append("\n扫描音频文件...")
    for file in os.listdir(directory):
        if os.path.splitext(file.lower())[1] in SUPPORTED_FORMATS:
            file_path = os.path.join(directory, file)
            file_count += 1

            try:
                metadata = read_song_metadata(file_path)
                key = f"{file_count}_{metadata['clean_title']}"
                songs[key] = metadata
                output.append(f"  [{file_count}] {file[:45]}")
            except Exception as e:
                output.append(f"  [{file_count}] ❌ 读取出错: {file} - {str(e)}")

    output.append(f"发现 {file_count} 个音频文件，有效处理 {len(songs)} 个")
    return songs, "\n".join(output)

def organize_playlist():
    """命名排序功能的主函数"""
    output = []
    
    output.append("\n" + "=" * 60)
    output.append("🎵 本地歌曲匹配工具 (修复乱码版)")
    output.append("=" * 60)

    # 获取当前目录
    current_dir = os.getcwd()
    output.append(f"工作目录: {current_dir}")

    # 检查播放列表
    playlist_file = os.path.join(current_dir, "playlist.txt")
    if not os.path.exists(playlist_file):
        output.append("\n❌ 错误: 未找到 playlist.txt 文件")
        output.append("请创建一个播放列表文件：")
        output.append("   1. 每行一个歌曲标题")
        output.append("   2. 可以包含序号（如 '1. 歌曲名' 或 ' - 歌曲名'）")
        return "\n".join(output)

    # 收集音频文件
    songs, songs_output = get_valid_songs(current_dir)
    output.append(songs_output)
    
    if not songs:
        output.append("✅ 没有需要处理的音频文件")
        return "\n".join(output)

    # 读取播放列表
    playlist_titles = read_playlist(playlist_file)
    if not playlist_titles:
        output.append("\n❌ 错误: 无法从播放列表文件中提取有效的歌曲标题")
        output.append("请检查playlist.txt文件内容")
        return "\n".join(output)

    output.append(f"\n播放列表包含 {len(playlist_titles)} 首歌曲")

    # 执行匹配
    matched, unmatched, match_output = match_songs(songs, playlist_titles, threshold=0.68)  # 降低阈值
    output.append(match_output)

    # 输出统计
    output.append("\n" + "=" * 50)
    output.append("匹配结果统计:")
    output.append(f"  成功匹配: {len(matched)} 首歌曲")
    output.append(f"  未能匹配: {len(unmatched)} 首歌曲")
    if songs:
        ratio = len(matched) / len(songs) * 100
        output.append(f"  匹配率: {ratio:.1f}%")
    output.append("=" * 50)

    # 在当前目录下直接处理文件
    if matched or unmatched:
        rename_output = rename_files_in_place(matched, unmatched)
        output.append(rename_output)
        output.append("\n✅ 完成! 文件已直接处理在当前目录")
    else:
        output.append("\n⚠️ 没有文件需要处理")

    output.append("\n操作说明:")
    output.append(" - 匹配的文件: 开头添加三位数字序号")
    output.append(" - 未匹配文件: 开头添加'（未匹配）'标记")
    output.append(" - 原文件名结构保持不变")
    output.append(" - 新特性: 改进了中日文乱码处理")
    
    return "\n".join(output)

# ==================== 移除前缀功能 ====================
def remove_prefixes_func():
    """删除所有音乐文件的前缀功能函数"""
    current_dir = os.getcwd()
    output = []
    output.append(f"当前目录: {current_dir}")

    # 遍历当前目录下的所有文件
    for file in os.listdir(current_dir):
        if file.endswith(SUPPORTED_FORMATS[:2]):  # 只处理.flac和.mp3文件
            file_path = os.path.join(current_dir, file)

            # 提取文件名（不包括路径）
            filename = os.path.basename(file)

            # 删除前缀（包括数字前缀和"(未找到)"前缀）
            new_filename = re.sub(r'^\d+_', '', filename)  # 删除数字前缀
            new_filename = re.sub(r'^（未找到）', '', new_filename)  # 删除"(未找到)"前缀
            new_filename = re.sub(r'^（未匹配）', '', new_filename)  # 删除"(未匹配)"前缀
            new_filename = re.sub(r'^\(未找到\)', '', new_filename)  # 删除"(未找到)"前缀（英文括号）
            new_filename = re.sub(r'^_', '', new_filename)  # 删除下划线前缀
            new_filename = re.sub(r'^-', '', new_filename)  # 删除连字符前缀

            # 如果文件名有变化，则重命名文件
            if new_filename != filename:
                new_file_path = os.path.join(current_dir, new_filename)
                try:
                    os.rename(file_path, new_file_path)
                    output.append(f"已重命名: {filename} -> {new_filename}")
                except Exception as e:
                    output.append(f"重命名文件时出错 {filename}: {e}")
            else:
                output.append(f"无需重命名: {filename}")
                
    return "\n".join(output)

# ==================== GUI界面 ====================
class MusicManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("音乐管理工具")
        self.root.geometry("600x400")
        self.root.resizable(True, True)

        # 创建主框架
        self.main_frame = ttk.Frame(root, padding="20")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(3, weight=1)

        # 标题
        title_label = ttk.Label(self.main_frame, text="音乐管理工具", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # 按钮框架
        button_frame = ttk.LabelFrame(self.main_frame, text="功能选项", padding="10")
        button_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)

        # 三个功能按钮
        self.update_btn = ttk.Button(button_frame, text="更新歌单", command=self.update_playlist)
        self.update_btn.grid(row=0, column=0, padx=5, pady=5, sticky=(tk.W, tk.E))

        self.organize_btn = ttk.Button(button_frame, text="命名排序", command=self.organize_files)
        self.organize_btn.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))

        self.remove_btn = ttk.Button(button_frame, text="移除前缀", command=self.remove_prefixes)
        self.remove_btn.grid(row=0, column=2, padx=5, pady=5, sticky=(tk.W, tk.E))

        # 进度条
        self.progress = ttk.Progressbar(self.main_frame, mode='indeterminate')
        self.progress.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        # 输出文本框
        output_frame = ttk.LabelFrame(self.main_frame, text="运行输出", padding="10")
        output_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        self.output_text = scrolledtext.ScrolledText(output_frame, height=10)
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 退出按钮
        self.exit_btn = ttk.Button(self.main_frame, text="退出", command=root.quit)
        self.exit_btn.grid(row=4, column=2, sticky=tk.E, pady=(0, 0))

    def run_function(self, func, *args):
        """运行功能函数"""
        try:
            # 开始进度条
            self.progress.start()

            # 在新线程中运行函数，避免阻塞GUI
            thread = threading.Thread(target=self._run_function_thread, args=(func, *args))
            thread.daemon = True
            thread.start()

        except Exception as e:
            self.progress.stop()
            messagebox.showerror("错误", f"运行功能时发生错误:\n{str(e)}")

    def _run_function_thread(self, func, *args):
        """在后台线程中运行函数"""
        try:
            # 运行函数
            result = func(*args)
            
            # 在主线程中更新UI
            self.root.after(0, self._function_finished, func.__name__, result)
        except Exception as e:
            self.root.after(0, self._function_error, str(e))

    def _function_finished(self, func_name, result):
        """函数运行完成后的回调"""
        # 停止进度条
        self.progress.stop()

        # 显示输出
        self.output_text.insert(tk.END, f"运行 {func_name} 的输出:\n")
        self.output_text.insert(tk.END, "=" * 50 + "\n")
        if result:
            self.output_text.insert(tk.END, result)
        self.output_text.insert(tk.END, "=" * 50 + "\n")
        self.output_text.see(tk.END)

    def _function_error(self, error_msg):
        """函数运行出错的回调"""
        self.progress.stop()
        messagebox.showerror("错误", f"运行功能时发生错误:\n{error_msg}")

    def update_playlist(self):
        """更新歌单 - 需要用户输入歌单链接"""
        # 弹出对话框请求用户输入歌单链接
        playlist_url = simpledialog.askstring(
            "输入歌单链接",
            "请输入网易云音乐歌单链接:\n(格式: https://music.163.com/api/playlist/detail?id=歌单ID)",
            parent=self.root
        )

        if not playlist_url:
            messagebox.showwarning("取消操作", "未输入歌单链接，操作已取消")
            return

        # 验证URL格式
        if not playlist_url.startswith("https://music.163.com/api/playlist/detail?id="):
            messagebox.showerror("错误", "请输入正确的歌单API链接\n格式应为: https://music.163.com/api/playlist/detail?id=歌单ID")
            return

        # 运行更新歌单功能，并传递用户输入的链接
        self.run_function(update_playlist, playlist_url)

    def organize_files(self):
        """命名排序"""
        self.run_function(organize_playlist)

    def remove_prefixes(self):
        """移除前缀"""
        self.run_function(remove_prefixes_func)

def main():
    root = tk.Tk()
    app = MusicManagerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()