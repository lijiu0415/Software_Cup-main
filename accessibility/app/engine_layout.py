# -*- coding: utf-8 -*-
"""
engine_layout.py —— 官方刺激界面 + 官方布局（原样保留）+ 引擎子类（新增）。

官方部分（不可改，逐字保留）：
- settings：6 个刺激块的频率/尺寸/位置/命令，频率 6.2~11.2 原样不动。
- layout：屏幕配置与 6 个 sinBlock 的创建参数（frequency/phase 等）原样不动。

新增部分（用户应用层）：
- App(HGuiEngine)：把官方 step 链替换为一个 _tick 分发，驱动 StateMachine。
- （文字/业务内容显示已迁移到网页端，本窗口只负责频闪块。）
"""
from guienginemp.hguiengine import HGuiEngine

from app.state_machine import StateMachine
from app.udp_client import UDPResultClient
from app.ssvep_context import SSVEPContext
from app.bridge_server import BridgeServer
from app.window_control import get_hwnd, send_to_back


## ============================================================================== ##
## 【官方原样·禁止修改】settings：6 个刺激块的频率/尺寸/位置/命令。
##   频率值、频率数量、刺激时长、闪烁模式一律不动。
settings = [{ 'size':(300,200),'position':(150,100),'freq':6.2,'cmd':'前进','cmdbuf':b'2','cmdTime':3},
             {'size':(300,200),'position':(800,100),'freq':7.2,'cmd':'后退','cmdbuf':b'1','cmdTime':3},
             {'size':(300,200),'position':(1450,100),'freq':8.2,'cmd':'左转','cmdbuf':b'3','cmdTime':3},
             {'size':(300,200),'position':(150,700),'freq':9.2,'cmd':'右转','cmdbuf':b'4','cmdTime':3},
             {'size':(300,200),'position':(800,700),'freq':10.2,'cmd':'鸣笛','cmdbuf':b'6','cmdTime':3},
             {'size':(300,200),'position':(1450,700),'freq':11.2,'cmd':'亮灯','cmdbuf':b'5','cmdTime':3}  ]
## ============================================================================== ##


## ============================================================================== ##
## 【官方原样·禁止修改】layout：屏幕配置 + 6 个 sinBlock 的创建参数。
##   frequency / phase / 尺寸 / 位置 / 闪烁模式一律不动。
layout = {}
layout = {'screen': {'size': (1600,800), 'color': (0, 0, 0), 'type': 'normal',
                     'Fps': 60, 'caption': 'ssvep demo'}}

for id, setting in enumerate(settings):
    layout['sti%d' % (id)] = {
        'class': 'sinBlock',
        'parm': {'size': setting['size'],
                 'position': setting['position'],
                 'anchor': 'center',
                 'bordercolor': (150, 150, 150),
                 'borderon': True,
                 'borderwidth': 2,
                 'textcolor': (0, 255, 0),
                 'textanchor': 'midtop',
                 'textsize': 60,
                 'text': setting['cmd'],
                 'layer': 1,
                 'visible': True,
                 'start': False,
                 'frequency': setting['freq'],
                 'phase': 0}}
## ============================================================================== ##


## ============================================================================== ##
## （文字/业务内容显示已迁移到网页端，本窗口不再需要独立文字块。）
## ============================================================================== ##


class App(HGuiEngine):
    """用户应用引擎：继承官方 HGuiEngine，复用 mainLoop / stimuli / lock / reset。"""

    def __init__(self, stim):
        super().__init__(stim)

        # 新增：运行时上下文 + UDP 结果线程 + 本地 WebSocket 桥 + 状态机
        self.ctx = SSVEPContext()
        self.udp = UDPResultClient()
        self.udp.start()
        self.bridge = BridgeServer()   # 供 Vue 前端连接（可选，不影响独立运行）
        self.bridge.start()
        self.hwnd = get_hwnd()         # 频闪窗句柄，用于「前后切」窗口控制
        send_to_back(self.hwnd)        # 启动时先最小化，等前端连上再弹出
        self.sm = StateMachine(self, self.ctx, self.udp)

        # 复用官方 currentStep 机制：恒指向 _tick，由官方 mainLoop 反复调用
        self.currentStep = self._tick

    def _tick(self):
        """每帧被官方 mainLoop 调用一次，执行状态机的当前状态并推进。"""
        self.sm.tick()
