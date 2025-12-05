import subprocess
import time
import os

import requests
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.chrome.options import Options
import json

from selenium.webdriver.common.by import By


class ExistingChromeController:
    def __init__(self, port=9222, user_data_dir=None):
        self.port = port
        self.user_data_dir = user_data_dir
        self.chrome_process = None
        self.driver = None

    def start_chrome_with_debugging(self):
        """启动 Chrome 并启用远程调试"""
        chrome_paths = [
            r"C:\Users\HP\AppData\Local\Google\Chrome\Application\chrome.exe",  # Windows
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",  # Windows 32位
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS
            "/usr/bin/google-chrome",  # Linux
            "/usr/bin/chromium-browser"  # Linux Chromium
        ]
        # "C:\Users\HP\AppData\Local\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
        chrome_path = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_path = path
                break

        if not chrome_path:
            print("未找到 Chrome 浏览器")
            return False

        # 构建启动命令
        cmd = [chrome_path, f"--remote-debugging-port={self.port}"]

        if self.user_data_dir:
            cmd.append(f"--user-data-dir={self.user_data_dir}")

        # 添加其他可选参数
        cmd.extend([
            "--no-first-run",
            "--no-default-browser-check",
            "--start-maximized"
        ])

        try:
            # 启动 Chrome
            self.chrome_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            print(f"Chrome 已启动 (PID: {self.chrome_process.pid})")
            time.sleep(3)  # 等待 Chrome 启动
            return True

        except Exception as e:
            print(f"启动 Chrome 失败: {e}")
            return False

    def connect(self):
        """连接到已启动的 Chrome"""
        options = Options()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{self.port}")
        # 启用性能日志
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        try:
            self.driver = webdriver.Chrome(options=options)
            print(f"已连接到 Chrome (端口: {self.port})")
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False

    def open_url(self, url):
        """在当前浏览器中打开 URL"""
        if not self.driver:
            print("未连接到 Chrome")
            return False

        self.driver.get(url)
        print(f"已打开: {url}")
        return True

    def get_current_tabs(self):
        """获取当前所有标签页信息"""
        if not self.driver:
            return []

        tabs_info = []
        original_window = self.driver.current_window_handle

        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            tabs_info.append({
                'handle': handle,
                'title': self.driver.title,
                'url': self.driver.current_url
            })

        # 切换回原始窗口
        self.driver.switch_to.window(original_window)
        return tabs_info

    def close(self):
        """关闭连接（可选关闭浏览器）"""
        if self.driver:
            # 注意：这里只是断开连接，不是关闭浏览器
            print("断开 Selenium 连接")

        if self.chrome_process:
            self.chrome_process.terminate()

            # # 是否关闭浏览器进程
            # response = input("是否关闭 Chrome 浏览器？(y/n): ")
            # if response.lower() == 'y':
            #     self.chrome_process.terminate()
            #     print("Chrome 浏览器已关闭")

    def get_video_url_with_cdp(self, input):
        try:
            # 启用网络域
            self.driver.execute_cdp_cmd('Network.enable', {})

            # 创建存储请求的列表
            requests = []

            def store_request(**kwargs):
                requests.append(kwargs)

            # 添加事件监听（通过日志方式）
            self.driver.execute_cdp_cmd('Network.setRequestInterception', {
                'patterns': [{'urlPattern': '*', 'resourceType': 'Media'}]
            })
            # 访问页面
            self.driver.get(input)
            time.sleep(5)

            # 获取性能日志
            logs = self.driver.get_log('performance')

            video_urls = []
            for entry in logs:
                try:
                    log = json.loads(entry['message'])['message']

                    # 检查网络响应
                    if log.get('method') == 'Network.responseReceived':
                        response = log['params']['response']
                        url = response.get('url', '')

                        # 检查是否是视频
                        content_type = response.get('headers', {}).get('content-type', '')
                        if any(x in url.lower() for x in ['.mp4', '.m3u8', '.mov']) or 'video' in content_type.lower():
                            if url not in video_urls:
                                print(f"✅ 发现视频: {url}")
                                video_urls.append(url)
                except Exception as e:
                    continue
        finally:
            pass
        return video_urls


def download_video_simple(url, filename=None):
    """简单的视频下载函数"""
    if filename is None:
        # 从URL提取文件名
        filename = url.split('/')[-1].split('?')[0]
        if not filename.endswith('.mp4'):
            filename += '.mp4'

    # 设置请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.xiaohongshu.com/',
        'Accept': '*/*',
        'Accept-Encoding': 'identity',  # 重要：不要压缩
        'Range': 'bytes=0-',  # 支持断点续传
    }

    try:
        print(f"开始下载: {filename}")

        # 发送请求
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()  # 检查请求是否成功

        # 获取文件大小
        total_size = int(response.headers.get('content-length', 0))

        # 保存文件
        downloaded = 0
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # 显示进度
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r下载进度: {percent:.1f}% [{downloaded}/{total_size} bytes]", end='')

        print(f"\n✅ 下载完成: {filename}")
        print(f"文件大小: {os.path.getsize(filename)} bytes")
        return True

    except Exception as e:
        print(f"❌ 下载失败: {str(e)}")
        return False


# 使用示例
if __name__ == "__main__":
    # 1. 创建控制器
    chrome = ExistingChromeController(
        port=9225,  # 使用不同的端口避免冲突
        user_data_dir=r"G:\user_data"
    )

    # 2. 启动 Chrome
    if chrome.start_chrome_with_debugging():
        # 3. 连接
        if chrome.connect():
            # 4. 获取当前标签页
            tabs = chrome.get_current_tabs()
            print(f"当前打开的标签页: {len(tabs)}个")

            for i, tab in enumerate(tabs, 1):
                print(f"{i}. {tab['title']} - {tab['url']}")

            # 5. 打开新网页
            chrome.open_url("https://www.xiaohongshu.com/explore")

            # test = chrome.driver.find_element(By.XPATH,'//*[@id="exploreFeeds"]/section[2]/div/a[2]')

            search = chrome.driver.find_element(By.XPATH, '//*[@id="search-input"]')
            search.send_keys("美女穿搭")
            search.send_keys(Keys.ENTER)
            chrome.driver.find_element(By.XPATH, '//*[@id="video"]').click()
            time.sleep(2)
            target = chrome.driver.find_element(By.XPATH,
                                                '//*[@id="global"]/div[2]/div[2]/div/div/div[3]/div[1]/section[1]/div/a[2]')

            d = target.get_attribute("href")
            # aa = test.get_attribute("href")
            urls = chrome.get_video_url_with_cdp(d)
            if urls:
                download_video_simple(urls[0])

            # 保持浏览器打开
            input("按回车键结束...")

    # 9. 关闭
    chrome.close()
