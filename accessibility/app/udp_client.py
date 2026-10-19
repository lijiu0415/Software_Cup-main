# -*- coding: utf-8 -*-
"""
udp_client.py —— 监听官方 8093 结果的线程 + 队列（新增，基于官方 threadfun 改造）。

协议不变：绑定 127.0.0.1:8093，收 UTF-8 字符串 "0"~"5"，转为 int 0~5 入队。
本模块只做「接收 + 入队」，不做任何 SSVEP 检测，也不触碰 8093 协议本身。
"""
import socket
import threading
import queue


class UDPResultClient(threading.Thread):
    def __init__(self, host='127.0.0.1', port=8093):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.results = queue.Queue()
        self._stop = threading.Event()

    def run(self):
        # 复用官方 threadfun 的 socket 绑定与接收方式（地址/端口/编码不变）
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.host, self.port))
        while not self._stop.is_set():
            try:
                buf, addr = sock.recvfrom(64)
                val = int(buf.decode('utf-8').strip())
                if val in (0, 1, 2, 3, 4, 5):
                    self.results.put_nowait(val)
            except Exception:
                # 脏数据 / 空包 / 非 0~5：忽略
                continue

    def drain(self):
        """清空结果队列（进入提示页 / 频闪页前调用，丢弃非当前状态的结果）。"""
        while True:
            try:
                self.results.get_nowait()
            except queue.Empty:
                break

    def stop(self):
        self._stop.set()
