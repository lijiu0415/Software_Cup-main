# -*- coding: utf-8 -*-
"""
demo_simulate.py —— 无 EEG 设备时的演示脚本，按完整流程顺序向 127.0.0.1:8093 发送模拟结果。

流程：启动页(游客登录) → 科目选择(软件安全) → 人物画像6题 → 学习(3步) → 做题(3×2题) → 完成。

用法：先 `python run.py` 启动应用（等窗口出现、约 3 秒），再另开一个终端 `python demo_simulate.py`。
"""
import socket
import time

ADDR = ('127.0.0.1', 8093)
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send(v, gap):
    time.sleep(gap)
    s.sendto(str(v).encode(), ADDR)
    print(f'  -> 发送结果 {v}')


print('[demo] 开始（先给应用 3 秒缓冲，确保 8093 已绑定）')
time.sleep(3)

# (结果, 与上一次结果之间的等待秒)
# 等待秒 = 冷却1.5s + 提示页2~3s 的粗调，留 1~1.5s 余量，保证落在频闪页窗口内。
steps = [
    (0, 0),    # 启动页: 0 = 游客登录
    (0, 5),    # 科目: 0 = 软件安全
    (0, 4.5),  # 画像 q1 -> 1分
    (1, 4.5),  # 画像 q2 -> 2分
    (2, 4.5),  # 画像 q3 -> 3分
    (3, 4.5),  # 画像 q4 -> 4分
    (4, 4.5),  # 画像 q5 -> 5分
    (2, 4.5),  # 画像 q6 -> 3分
    (0, 7),    # 学习步骤1 题1 -> A
    (1, 4.5),  # 学习步骤1 题2 -> B
    (2, 7),    # 学习步骤2 题1 -> C
    (3, 4.5),  # 学习步骤2 题2 -> D
    (0, 7),    # 学习步骤3 题1 -> A
    (1, 4.5),  # 学习步骤3 题2 -> B
]
for v, gap in steps:
    send(v, gap)

print('[demo] 流程发送完毕（应用随后显示“学习完成”并回到启动页）')
