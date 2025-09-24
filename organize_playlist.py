import os
import re
import sys
import unicodedata
import string
import difflib
from io import StringIO
import contextlib

# 安全设置标准输出编码为UTF-8
try:
    if sys.stdout:
        sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# 支持的音频文件扩展名 (添加了.fla扩展支持)
SUPPORTED_FORMATS = ('.flac', '.mp3', '.m4a', '.wav', '.ogg', '.fla')


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

def main():
    """主程序入口"""
    # 调用功能函数
    result = organize_playlist()
    print(result)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n操作已取消")
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")