# -*- coding: utf-8 -*-
"""
agent_api.py —— Agent 接口（先 Mock）。

agent_get_learning_path(profile_answers) 根据画像打分生成学习路径；当前为 Mock，
后续可替换为调用真实 Agent / 规则引擎。
"""


def agent_get_learning_path(profile_answers):
    """
    Mock：根据画像打分生成学习路径。

    profile_answers: list[int]，6 个 1~5 的分数。
    返回：学习步骤名列表，例如 ['概念入门', '标准训练', '综合实践']。
    """
    total = sum(profile_answers) if profile_answers else 0
    # 简单按总分分层（Mock 逻辑，可替换）
    if total >= 24:
        depth = '进阶'
    elif total >= 18:
        depth = '标准'
    else:
        depth = '基础'
    return ['概念入门', f'{depth}训练', '综合实践']
