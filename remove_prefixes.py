import os
import re
import sys
from io import StringIO
import contextlib

# 安全设置标准输出编码为UTF-8
try:
    if sys.stdout:
        sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# 支持的音频文件扩展名
SUPPORTED_FORMATS = ('.flac', '.mp3')

def remove_prefixes_func():
    """删除所有音乐文件的前缀功能函数"""
    current_dir = os.getcwd()
    output = []
    output.append(f"当前目录: {current_dir}")

    # 遍历当前目录下的所有文件
    for file in os.listdir(current_dir):
        if file.endswith(SUPPORTED_FORMATS):
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

def main():
    # 调用功能函数
    result = remove_prefixes_func()
    print(result)

if __name__ == "__main__":
    remove_prefixes_func()