"""
客观题题库 - 错题分析数据源

字段说明：
- ex_id: 题目唯一 ID
- kp_id: 关联知识点（使用 DB 前缀格式，如 ai_kp0102；关联章节/知识点用于错题聚合）
- type: 单选题 / 多选题 / 判断题 / 编程题
- difficulty: 难度 1-5
- question: 题干
- options: 选项列表
- answer: 单选题/判断题 = 索引(int)；多选题 = 索引列表；编程题 = null（不判分）
- analysis: 解析
"""
EXERCISE_BANK = [
    {
        "ex_id": "ai_ex0101",
        "kp_id": "ai_kp0102",
        "type": "单选题",
        "difficulty": 1,
        "question": "以下哪个是图灵测试的核心思想？",
        "options": ["A. 判断机器是否能思考", "B. 判断机器能否通过对话让人误认为它是人", "C. 判断机器是否有意识", "D. 判断机器能否下棋"],
        "answer": 1,
        "analysis": "图灵测试核心：通过对话判断机器是否具有智能，即能否让人无法区分是人还是机器。",
    },
    {
        "ex_id": "ai_ex0401",
        "kp_id": "ai_kp0402",
        "type": "单选题",
        "difficulty": 2,
        "question": "一阶谓词逻辑中，量词 ∀ 表示的含义是？",
        "options": ["A. 存在", "B. 任意/所有", "C. 否定", "D. 蕴含"],
        "answer": 1,
        "analysis": "∀ 是全称量词，含义为「任意 / 所有」。",
    },
    {
        "ex_id": "ai_ex0402",
        "kp_id": "ai_kp0404",
        "type": "单选题",
        "difficulty": 2,
        "question": "下列哪种方法属于知识表示方法？",
        "options": ["A. 冒泡排序", "B. 语义网络", "C. 快速排序", "D. 哈希查找"],
        "answer": 1,
        "analysis": "语义网络是经典的知识表示方法，其余是算法或数据结构。",
    },
    {
        "ex_id": "ai_ex0403",
        "kp_id": "ai_kp0404",
        "type": "多选题",
        "difficulty": 3,
        "question": "以下哪些属于经典的知识表示方法？",
        "options": ["A. 谓词逻辑", "B. 语义网络", "C. 产生式规则", "D. 哈希表"],
        "answer": [0, 1, 2],
        "analysis": "谓词逻辑、语义网络、产生式规则都是经典知识表示方法，哈希表是数据结构。",
    },
    {
        "ex_id": "ai_ex0404",
        "kp_id": "ai_kp0404",
        "type": "多选题",
        "difficulty": 2,
        "question": "下列关于知识图谱的说法正确的有？",
        "options": ["A. 由节点和边构成", "B. 边可表示实体间关系", "C. 只能表示树形结构", "D. 支持关系推理"],
        "answer": [0, 1, 3],
        "analysis": "知识图谱是图结构（非仅树形），支持关系推理。",
    },
    {
        "ex_id": "ai_ex0405",
        "kp_id": "ai_kp0401",
        "type": "判断题",
        "difficulty": 2,
        "question": "命题逻辑的表达能力强于一阶谓词逻辑。",
        "options": ["正确", "错误"],
        "answer": 1,
        "analysis": "一阶谓词逻辑表达能力更强，可刻画对象间关系。",
    },
    {
        "ex_id": "ai_ex0406",
        "kp_id": "ai_kp0404",
        "type": "判断题",
        "difficulty": 2,
        "question": "知识图谱中的边只能有一种类型。",
        "options": ["正确", "错误"],
        "answer": 1,
        "analysis": "知识图谱的边可以有多种关系类型。",
    },
    {
        "ex_id": "ai_ex0407",
        "kp_id": "ai_kp0304",
        "type": "单选题",
        "difficulty": 3,
        "question": "在 A* 搜索算法中，估价函数 f(n) 通常由哪两部分构成？",
        "options": ["A. g(n) + h(n)", "B. g(n) × h(n)", "C. 只含 g(n)", "D. 只含 h(n)"],
        "answer": 0,
        "analysis": "A* 的估价函数 f(n)=g(n)+h(n)，其中 g(n) 是从起点到 n 的实际代价，h(n) 是 n 到目标的启发式估计代价。",
    },
    {
        "ex_id": "ai_ex0501",
        "kp_id": "ai_kp0501",
        "type": "单选题",
        "difficulty": 1,
        "question": "监督学习与无监督学习的主要区别在于？",
        "options": ["A. 是否使用神经网络", "B. 训练数据是否带有标签", "C. 是否需要 GPU", "D. 是否需要大量数据"],
        "answer": 1,
        "analysis": "监督学习使用带标签的数据训练，无监督学习使用无标签数据。",
    },
    {
        "ex_id": "ai_ex0801",
        "kp_id": None,
        "type": "编程题",
        "difficulty": 4,
        "question": "编写一个 Python 函数 is_prime(n)，判断正整数 n 是否为素数。",
        "options": [],
        "answer": None,
        "analysis": "参考：遍历 2 到 int(n**0.5)+1，若存在整除则非素数。",
    },
]
