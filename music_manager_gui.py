import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import sys
import os
import threading

# 导入功能模块
import update_playlist
import organize_playlist
import remove_prefixes

def get_resource_path(relative_path):
    """获取资源文件的绝对路径，处理PyInstaller打包后的情况"""
    try:
        # PyInstaller创建临时文件夹，并将路径存储在sys._MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

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
        self.run_function(update_playlist.update_playlist, playlist_url)

    def organize_files(self):
        """命名排序"""
        self.run_function(organize_playlist.organize_playlist)

    def remove_prefixes(self):
        """移除前缀"""
        self.run_function(remove_prefixes.remove_prefixes_func)

def main():
    root = tk.Tk()
    app = MusicManagerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()