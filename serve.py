# -*- coding: utf-8 -*-
"""本地预览服务：绑定 0.0.0.0，方便手机同网访问。"""
from __future__ import annotations

import socket
import sys
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def get_lan_ips() -> list[str]:
    ips: list[str] = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except OSError:
        pass

    # 再试一次：UDP 探测默认路由出口 IP（不真正发包）
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127.") and ip not in ips:
            ips.insert(0, ip)
    except OSError:
        pass

    return ips


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    ips = get_lan_ips()
    preferred = ips[0] if ips else "你的电脑IP"

    handler = SimpleHTTPRequestHandler
    handler.extensions_map = {
        **getattr(handler, "extensions_map", {}),
        ".html": "text/html; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".md": "text/markdown; charset=utf-8",
    }

    server = ThreadingHTTPServer(("0.0.0.0", port), handler)

    print("=" * 56)
    print("  服务已启动，请保持本窗口开启")
    print("=" * 56)
    print()
    print("电脑访问:")
    print(f"  http://localhost:{port}/rewards.html")
    print()
    print("手机访问（手机和电脑必须连同一个 Wi-Fi）:")
    if ips:
        for ip in ips:
            print(f"  http://{ip}:{port}/rewards.html")
    else:
        print(f"  http://{preferred}:{port}/rewards.html")
        print("  （未能自动识别 IP，请在电脑运行 ipconfig 查看 WLAN 的 IPv4）")
    print()
    print("打不开时请检查:")
    print("  1. 手机是否连的是手机热点 / 访客 Wi-Fi（需与电脑同一网络）")
    print("  2. 右键 start.bat → 以管理员身份运行（放行防火墙）")
    print("  3. 路由器是否开启了 AP 隔离 / 访客网络隔离")
    print()
    print("关闭本窗口即停止服务。")
    print("=" * 56)

    webbrowser.open(f"http://localhost:{port}/rewards.html")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止服务")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
