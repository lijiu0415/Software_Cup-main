# -*- coding: utf-8 -*-
"""
bridge_server.py —— 本地 WebSocket 桥（新增），供 Vue 前端连接。

职责：
- Python -> 网页：推送状态（state）与 SSVEP 结果（result）事件。
- 网页 -> Python：接收控制指令，指令入队，由状态机轮询消费（当前支持 {"action":"restart"}）。

只做消息转发，不触碰任何 SSVEP 频率 / 刺激实现。
默认监听 ws://127.0.0.1:8765，仅本机可连。
"""
import asyncio
import json
import threading
import queue

import websockets


class BridgeServer(threading.Thread):
    def __init__(self, host='127.0.0.1', port=8765):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.loop = None
        self._clients = set()
        self._lock = threading.Lock()
        self._inbox = queue.Queue()   # 网页 -> Python 的指令

    # ---- 线程 / 事件循环 ----
    def run(self):
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._serve())
        except OSError as e:
            print(f'[bridge] 启动失败（端口 {self.port} 可能被占用）：{e}', flush=True)

    async def _serve(self):
        async with websockets.serve(self._handler, self.host, self.port):
            print(f'[bridge] ws://{self.host}:{self.port} 已启动', flush=True)
            await asyncio.Future()  # 常驻，直到进程退出

    async def _handler(self, ws):
        with self._lock:
            self._clients.add(ws)
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue
                self._inbox.put(msg)
        finally:
            with self._lock:
                self._clients.discard(ws)

    # ---- 网页 -> Python ----
    def poll_command(self):
        """非阻塞取一条网页指令，无则返回 None。"""
        try:
            return self._inbox.get_nowait()
        except queue.Empty:
            return None

    def has_clients(self):
        """是否有前端已连接。"""
        with self._lock:
            return len(self._clients) > 0

    # ---- Python -> 网页 ----
    def emit(self, message):
        """向所有已连接网页推送一条 JSON 事件（线程安全）。"""
        if self.loop is None:
            return
        data = json.dumps(message, ensure_ascii=False)
        with self._lock:
            clients = list(self._clients)
        for ws in clients:
            try:
                asyncio.run_coroutine_threadsafe(ws.send(data), self.loop)
            except Exception:
                pass
