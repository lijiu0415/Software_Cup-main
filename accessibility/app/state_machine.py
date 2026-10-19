# -*- coding: utf-8 -*-
"""
state_machine.py —— 用户应用层页面状态机（新增）。

架构分工（Python 管流程，网页管显示）：
- Python：只负责「流程推进 + 频闪块启停 + 收 8093 结果 + 状态/结果事件推送」。
- 网页：负责所有文字/业务内容显示、结果记录、业务映射、进度展示。
- Python 通过 WebSocket 桥把「state + ctx + result」推给网页，不承载任何业务内容。

复用官方 HGuiEngine 的 step 机制：App 的 currentStep 恒为 _tick，官方 mainLoop 每帧
调用 _tick，本模块的 StateMachine.tick() 完成「当前状态」的阻塞工作（停时 / 轮询 8093 /
冷却）并推进状态。

绝不触碰：刺激频率、频率数量、刺激时长（引擎侧）、闪烁模式、config.xlsx 映射、8093 协议。
"""
import time
import queue
from collections import Counter

from app.window_control import bring_to_front, send_to_back


# 频闪页固定闪烁时长：与官方检测器「5 秒滑窗」对齐（官方 flashTime=5）。
FLASH_TIMEOUT = 5.0

# 防抖冷却秒数（1~2 秒）
COOLDOWN_SECONDS = 1.5

# 结果采信参数（用户层，与官方「闪满 5 秒再取结果」对齐）
RECENT_SECONDS = 2.0      # 取末尾 N 秒结果的众数作为采信结果
MIN_MODE_RATIO = 0.5      # 众数占比 >= 50% 才算稳定；否则不强制选（静默/重试）

# 真机验证日志（只读，用于核对「结果 → 块 → 频率 → 选项」映射是否正确）
VERIFY_LOG = True
# 块索引 → 频率 的对照表（只读，与官方 settings 完全一致，禁止修改）
BLOCK_FREQ = {0: 6.2, 1: 7.2, 2: 8.2, 3: 9.2, 4: 10.2, 5: 11.2}

# 流程结构（用户层配置，与网页端 Mock 数据保持一致；以后可由网页通过 set_meta 下发）
PROFILE_COUNT = 6            # 画像题数
QUIZ_COUNT_PER_STEP = 2      # 每个学习步骤的做题数
LEARNING_STEP_COUNT = 3      # 学习步骤数


class State:
    WAIT_FRONTEND = 'wait_frontend'
    LOGIN_SSVEP = 'login_ssvep'
    LOGIN_UNAVAILABLE = 'login_unavailable'
    SUBJECT_PROMPT = 'subject_prompt'
    SUBJECT_SSVEP = 'subject_ssvep'
    PROFILE_PROMPT = 'profile_prompt'
    PROFILE_SSVEP = 'profile_ssvep'
    LEARNING_TEXT = 'learning_text'
    QUIZ_PROMPT = 'quiz_prompt'
    QUIZ_SSVEP = 'quiz_ssvep'
    DONE = 'done'


# 各 SSVEP 页面配置：(启用的官方块编号, 块上显示文字, 允许的结果集合)。
# 官方块 0~5 与频率 6.2~11.2 的对应关系保持不变，这里只是在其上叠加业务含义，只改块上显示文字。
SSVEP_BLOCKS = {
    State.LOGIN_SSVEP:   ([0, 1], ['游客登录', '登录'], {0, 1}),
    State.SUBJECT_SSVEP: ([0, 1], ['软件安全', '人工智能导论'], {0, 1}),
    State.PROFILE_SSVEP: ([0, 1, 2, 3, 4], ['1分', '2分', '3分', '4分', '5分'], {0, 1, 2, 3, 4}),
    State.QUIZ_SSVEP:    ([0, 1, 2, 3], ['A', 'B', 'C', 'D'], {0, 1, 2, 3}),
}


class StateMachine:
    def __init__(self, app, ctx, udp):
        self.app = app          # HGuiEngine 子类，提供 .stimuli / .lock
        self.ctx = ctx          # SSVEPContext 运行时上下文
        self.udp = udp          # UDPResultClient（线程 + queue）
        self.state = State.WAIT_FRONTEND
        self.profile_index = 0
        self.quiz_index = 0
        self.learning_step_index = 0
        self._last_emitted_state = None   # 用于桥的状态去重

    # ------------------------------------------------------------------ #
    # 主循环入口：每被 mainLoop 调用一次，执行当前状态的一步并推进
    # ------------------------------------------------------------------ #
    def tick(self):
        self._poll_commands()
        self._emit_state()
        if self.state == State.WAIT_FRONTEND:
            self._do_wait_frontend()
        elif self.state == State.LOGIN_SSVEP:
            self._do_login_ssvep()
        elif self.state == State.LOGIN_UNAVAILABLE:
            self._do_login_unavailable()
        elif self.state == State.SUBJECT_PROMPT:
            self._do_subject_prompt()
        elif self.state == State.SUBJECT_SSVEP:
            self._do_subject_ssvep()
        elif self.state == State.PROFILE_PROMPT:
            self._do_profile_prompt()
        elif self.state == State.PROFILE_SSVEP:
            self._do_profile_ssvep()
        elif self.state == State.LEARNING_TEXT:
            self._do_learning_text()
        elif self.state == State.QUIZ_PROMPT:
            self._do_quiz_prompt()
        elif self.state == State.QUIZ_SSVEP:
            self._do_quiz_ssvep()
        elif self.state == State.DONE:
            self._do_done()

    # ------------------------------------------------------------------ #
    # 通用工具
    # ------------------------------------------------------------------ #
    def _pause(self, seconds):
        """非频闪阶段：清空结果队列，隐藏所有刺激块，停留 seconds 秒。文字显示交给网页。"""
        send_to_back(getattr(self.app, 'hwnd', None))  # 频闪窗最小化，露出浏览器
        self.udp.drain()  # 进入提示页清空队列
        with self.app.lock:
            for i in range(6):
                self.app.stimuli['sti%d' % i].reset({'visible': False, 'start': False})
        time.sleep(seconds)

    def _run_ssvep(self, block_indices, labels, allowed):
        """
        闪满 FLASH_TIMEOUT 秒，取末尾结果的众数作为采信结果；不稳定则返回 None（不强制选择）。

        与官方「闪满 5 秒再取结果」对齐；只改用户层显示/启停，不触碰频率/相位/闪烁模式。
        """
        bring_to_front(getattr(self.app, 'hwnd', None))  # 频闪窗恢复置顶，盖住浏览器
        self.udp.drain()  # 进入频闪页前再清空一次队列

        with self.app.lock:
            for i in range(6):
                if i in block_indices:
                    text = labels[block_indices.index(i)]
                    self.app.stimuli['sti%d' % i].reset(
                        {'visible': True, 'start': True, 'text': text,
                         'bordercolor': (150, 150, 150)})
                else:
                    self.app.stimuli['sti%d' % i].reset(
                        {'visible': False, 'start': False})

        # 闪满 FLASH_TIMEOUT 秒，收集 allowed 内的结果（带时间戳）
        results = []
        deadline = time.time() + FLASH_TIMEOUT
        while time.time() < deadline:
            try:
                r = self.udp.results.get(timeout=0.05)
            except queue.Empty:
                continue
            if r in allowed:
                results.append((time.time(), r))

        # 取末尾 RECENT_SECONDS 的众数（稳定结果）
        result = self._pick_result(results)

        # 立即停止刺激；选中块标红作为反馈
        with self.app.lock:
            for i in range(6):
                self.app.stimuli['sti%d' % i].reset({'start': False})
            if result is not None:
                self.app.stimuli['sti%d' % result].reset({'bordercolor': (255, 0, 0)})

        if result is not None:
            if VERIFY_LOG:
                label = labels[block_indices.index(result)]
                freq = BLOCK_FREQ.get(result)
                print(f'[verify] 结果 {result} → 块{result} ({freq}Hz) → 选项 "{label}"', flush=True)
            self._emit({'type': 'result', 'state': self.state, 'result': result})
        self.udp.drain()  # 忽略后续重复结果
        return result

    def _pick_result(self, results):
        """从 (时间戳, 结果) 列表里取末尾 RECENT_SECONDS 的众数；不稳定返回 None。"""
        if not results:
            return None
        now = time.time()
        recent = [r for (t, r) in results if now - t <= RECENT_SECONDS]
        if not recent:
            return None
        counter = Counter(recent)
        result, count = counter.most_common(1)[0]
        if count / len(recent) < MIN_MODE_RATIO:
            return None  # 众数不占优：结果乱跳，未注视到 → 不强制选
        return result

    def _cooldown(self):
        """防抖冷却 1~2 秒（此时选中块保持标红作为反馈）。"""
        time.sleep(COOLDOWN_SECONDS)

    # ------------------------------------------------------------------ #
    # 桥接 / 事件（Python -> 网页）
    # ------------------------------------------------------------------ #
    def _emit(self, message):
        bridge = getattr(self.app, 'bridge', None)
        if bridge is not None:
            bridge.emit(message)

    def _ctx_snapshot(self):
        return {
            'user_id': self.ctx.user_id,
            'login_choice': self.ctx.login_choice,
            'subject': self.ctx.subject,
            'profile_answers': list(self.ctx.profile_answers),
            'profile_index': self.profile_index,
            'quiz_index': self.quiz_index,
            'learning_step_index': self.learning_step_index,
        }

    def _emit_state(self):
        if self.state == self._last_emitted_state:
            return
        self._last_emitted_state = self.state
        self._emit({'type': 'state', 'state': self.state, 'ctx': self._ctx_snapshot()})

    def _poll_commands(self):
        bridge = getattr(self.app, 'bridge', None)
        if bridge is None:
            return
        while True:
            cmd = bridge.poll_command()
            if cmd is None:
                break
            if isinstance(cmd, dict) and cmd.get('action') == 'restart':
                self.ctx.reset()
                self.profile_index = 0
                self.quiz_index = 0
                self.learning_step_index = 0
                self.state = State.LOGIN_SSVEP
                self._last_emitted_state = None

    # ------------------------------------------------------------------ #
    # 各状态实现
    # ------------------------------------------------------------------ #
    def _frontend_connected(self):
        bridge = getattr(self.app, 'bridge', None)
        if bridge is None:
            return True
        return bridge.has_clients()

    def _do_wait_frontend(self):
        """等待前端连上，再等 2 秒，然后才进入启动页频闪（频闪窗才会弹出）。"""
        while not self._frontend_connected():
            time.sleep(0.2)
        time.sleep(2.0)  # 连上后再等 2 秒
        self.state = State.LOGIN_SSVEP

    def _do_login_ssvep(self):
        result = self._run_ssvep(*SSVEP_BLOCKS[State.LOGIN_SSVEP])
        if result is None:
            time.sleep(0.3)
            return  # 保持本状态，重试
        self._cooldown()
        if result == 0:
            # 游客登录：生成临时用户，进入科目选择
            self.ctx.user_id = 'guest_%d' % int(time.time())
            self.ctx.login_choice = '游客登录'
            self.state = State.SUBJECT_PROMPT
        else:
            # 结果 1 = 登录：当前未开放，提示后停留在启动页
            self.ctx.login_choice = '登录'
            self.state = State.LOGIN_UNAVAILABLE

    def _do_login_unavailable(self):
        self._pause(2.0)
        self.state = State.LOGIN_SSVEP

    def _do_subject_prompt(self):
        self._pause(3.0)
        self.state = State.SUBJECT_SSVEP

    def _do_subject_ssvep(self):
        result = self._run_ssvep(*SSVEP_BLOCKS[State.SUBJECT_SSVEP])
        if result is None:
            time.sleep(0.3)
            return
        self._cooldown()
        self.ctx.subject = {0: '软件安全', 1: '人工智能导论'}[result]
        self.profile_index = 0
        self.state = State.PROFILE_PROMPT

    def _do_profile_prompt(self):
        self._pause(2.0)
        self.state = State.PROFILE_SSVEP

    def _do_profile_ssvep(self):
        result = self._run_ssvep(*SSVEP_BLOCKS[State.PROFILE_SSVEP])
        if result is None:
            time.sleep(0.3)
            return
        self._cooldown()
        self.ctx.profile_answers.append(result + 1)  # 5 档：官方 0~4 -> 1~5 分
        self.profile_index += 1
        if self.profile_index >= PROFILE_COUNT:
            self.learning_step_index = 0
            self.state = State.LEARNING_TEXT
        else:
            self.state = State.PROFILE_PROMPT

    def _do_learning_text(self):
        self._pause(2.0)
        self.quiz_index = 0
        self.state = State.QUIZ_PROMPT

    def _do_quiz_prompt(self):
        self._pause(2.0)
        self.state = State.QUIZ_SSVEP

    def _do_quiz_ssvep(self):
        result = self._run_ssvep(*SSVEP_BLOCKS[State.QUIZ_SSVEP])
        if result is None:
            time.sleep(0.3)
            return
        self._cooldown()
        self.quiz_index += 1
        if self.quiz_index >= QUIZ_COUNT_PER_STEP:
            self.learning_step_index += 1
            if self.learning_step_index >= LEARNING_STEP_COUNT:
                self.state = State.DONE
            else:
                self.state = State.LEARNING_TEXT
        else:
            self.state = State.QUIZ_PROMPT

    def _do_done(self):
        self._pause(3.0)
        self.ctx.reset()
        self.profile_index = 0
        self.quiz_index = 0
        self.learning_step_index = 0
        self.state = State.LOGIN_SSVEP
