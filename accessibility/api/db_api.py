# -*- coding: utf-8 -*-
"""
db_api.py —— 数据库接口（先 Mock）。

用户应用只调用这里的函数，不直接连数据库；后续把函数体替换为真实 DB 访问即可。
"""

# ---- Mock 数据 ---------------------------------------------------------------- #

SUBJECTS = ['软件安全', '人工智能导论']

# 6 组人物画像问题（每组一题，1~5 分）
PROFILE_QUESTIONS = [
    {'id': 'p1', 'text': '第1题：你对动手实践类学习有多感兴趣？（1~5分）'},
    {'id': 'p2', 'text': '第2题：你对抽象理论类内容有多感兴趣？（1~5分）'},
    {'id': 'p3', 'text': '第3题：你更偏好项目制学习吗？（1~5分）'},
    {'id': 'p4', 'text': '第4题：你对新技术的接受速度？（1~5分）'},
    {'id': 'p5', 'text': '第5题：你偏好的学习节奏？（1~5分）'},
    {'id': 'p6', 'text': '第6题：你希望的学习深度？（1~5分）'},
]


# ---- 接口函数（Mock 实现） ------------------------------------------------------ #

def db_get_subjects():
    """返回科目列表。"""
    return list(SUBJECTS)


def db_get_profile_questions():
    """返回 6 组人物画像问题（每组含 id 与提示文字）。"""
    return list(PROFILE_QUESTIONS)


def db_save_profile_answer(user_id, question_id, score):
    """保存单题画像打分。Mock：仅打印。"""
    print(f'[db_api] save_profile_answer user={user_id} q={question_id} score={score}', flush=True)


def db_get_learning_content(subject, learning_path, step):
    """返回某学习步骤的文字板内容。Mock：按科目/步骤动态生成一句话。"""
    step_name = learning_path[step] if 0 <= step < len(learning_path) else '未知步骤'
    return f'【{subject}】学习内容：{step_name}（Mock 文字板，第 {step + 1} 步）'


def db_get_quiz_question(subject, learning_path, step):
    """
    返回该学习步骤的题目列表（Mock：每步 2 题，每题含 id / text / answer）。
    step 为学习步骤下标；题目文字按科目/步骤动态生成，answer 为正确答案（供后续判分）。
    """
    step_name = learning_path[step] if 0 <= step < len(learning_path) else '未知步骤'
    return [
        {'id': f'{subject}_{step_name}_q1',
         'text': f'【{subject}·{step_name}】第1题（Mock）：请选择 A/B/C/D',
         'answer': 'A'},
        {'id': f'{subject}_{step_name}_q2',
         'text': f'【{subject}·{step_name}】第2题（Mock）：请选择 A/B/C/D',
         'answer': 'B'},
    ]


def db_submit_quiz_answer(user_id, question_id, answer):
    """提交做题答案。Mock：仅打印。"""
    print(f'[db_api] submit_quiz_answer user={user_id} q={question_id} answer={answer}', flush=True)
