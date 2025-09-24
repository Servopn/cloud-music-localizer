# 音乐管理工具

这是一个用于管理本地音乐文件的工具，主要功能包括：

1. 从网易云音乐获取歌单信息
2. 根据歌单对本地音乐文件进行命名和排序
3. 移除文件名中的前缀

## 文件说明

### 主要文件

- `music_manager.py` - 合并后的主程序文件，包含所有功能和GUI界面
- `ml.ico` - 应用程序图标文件
- `build_app.bat` - Windows平台下的一键打包脚本
- `music_manager.spec` - PyInstaller打包配置文件（由打包脚本自动生成）

### 功能模块（已合并到music_manager.py中）

- 更新歌单：从网易云音乐API获取歌单信息并保存到playlist.txt
- 命名排序：根据playlist.txt对本地音乐文件进行匹配、重命名和排序
- 移除前缀：移除音乐文件名中的数字前缀和其他标记

## 使用方法

### 直接运行（需要Python环境）

1. 确保已安装Python 3.6+

2. 安装依赖包：

   ```
   pip install requests
   pip install browser_cookie3  # 可选，用于自动获取浏览器Cookie
   ```

3. 运行程序：

   ```
   python music_manager.py
   ```

### 打包为可执行文件

1. 确保已安装Python 3.6+
2. Windows系统下直接运行`build_app.bat`脚本
3. 打包完成后，可执行文件位于`dist`文件夹中

### 使用步骤

1. 运行程序后，点击"更新歌单"按钮，输入网易云音乐歌单链接
2. 程序会生成playlist.txt文件
3. 将本地音乐文件放在与playlist.txt相同的目录下
4. 点击"命名排序"按钮，程序会自动匹配并重命名音乐文件
5. 如需移除文件名前缀，可点击"移除前缀"按钮

## 注意事项

- 网易云音乐歌单链接格式应为：`https://music.163.com/api/playlist/detail?id=歌单ID`
- 程序支持的音频格式：.flac, .mp3, .m4a, .wav, .ogg
- 程序会自动处理中文乱码问题
- 如遇到需要登录的歌单，程序会尝试从浏览器获取Cookie

## 开发说明

- 所有功能已合并到单个文件中，便于维护和打包
- GUI使用tkinter开发，具有良好的跨平台兼容性
- 打包脚本支持一键生成Windows可执行文件
