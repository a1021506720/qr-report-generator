#!/usr/bin/env python3
"""
本地预览服务器
在项目根目录运行：python server.py
默认监听 0.0.0.0:8080，局域网内手机可直接扫码访问
"""

import http.server
import socketserver
import socket
import os
import sys
from pathlib import Path

PORT = 8080
BASE_DIR = Path(__file__).parent


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def log_message(self, fmt, *args):
        # 简化日志：只显示请求路径和状态
        print(f"  [{self.address_string()}] {fmt % args}")


def main():
    os.chdir(BASE_DIR)
    local_ip = get_local_ip()

    # 允许端口快速复用
    socketserver.TCPServer.allow_reuse_address = True

    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print("\n" + "=" * 50)
        print("    检测报告本地预览服务器")
        print("=" * 50)
        print(f"  本机访问：http://127.0.0.1:{PORT}/reports/")
        print(f"  局域网  ：http://{local_ip}:{PORT}/reports/")
        print("\n  Ctrl+C 停止服务器")
        print("=" * 50 + "\n")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[✓] 服务器已停止")
            sys.exit(0)


if __name__ == "__main__":
    main()
