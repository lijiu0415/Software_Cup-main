# -*- coding: utf-8 -*-
"""
ssvep_context.py —— 运行时上下文（新增）。

存放一次完整流程的业务数据，不含任何进度计数器（进度计数器在 StateMachine 内）。
"""
from dataclasses import dataclass, field


@dataclass
class SSVEPContext:
    user_id: str = None
    login_choice: str = None              # '游客登录' / '登录'
    subject: str = None                   # '软件安全' / '人工智能导论'
    profile_answers: list = field(default_factory=list)   # 6 组画像打分（1~5）

    def reset(self):
        self.user_id = None
        self.login_choice = None
        self.subject = None
        self.profile_answers = []
