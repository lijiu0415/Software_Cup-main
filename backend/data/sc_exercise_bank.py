"""
客观题题库 - 错题分析数据源（软件安全技术）

字段说明：
- ex_id: 题目唯一 ID（sc_exNNNN）
- kp_id: 关联知识点（使用 DB 前缀格式，如 sc_kp0301；关联章节/知识点用于错题聚合）
- type: 单选题 / 多选题 / 判断题 / 编程题
- difficulty: 难度 1-5
- question: 题干
- options: 选项列表
- answer: 单选题/判断题 = 索引(int)；多选题 = 索引列表；编程题 = null（不判分）
- analysis: 解析
"""
SC_EXERCISE_BANK = [
    {
        "ex_id": "sc_ex0101",
        "kp_id": "sc_kp0105",
        "type": "单选题",
        "difficulty": 1,
        "question": "信息安全三要素 CIA 中，C 指的是？",
        "options": ["A. 完整性", "B. 可用性", "C. 机密性", "D. 不可否认性"],
        "answer": 2,
        "analysis": "CIA 分别指机密性（Confidentiality）、完整性（Integrity）、可用性（Availability）。",
    },
    {
        "ex_id": "sc_ex0102",
        "kp_id": "sc_kp0301",
        "type": "单选题",
        "difficulty": 2,
        "question": "以下哪种 XSS 类型是将恶意脚本存储在服务器数据库中？",
        "options": ["A. 反射型 XSS", "B. 存储型 XSS", "C. DOM 型 XSS", "D. 盲 XSS"],
        "answer": 1,
        "analysis": "存储型 XSS 将恶意脚本持久化存储在服务器（如数据库），用户访问时被触发。",
    },
    {
        "ex_id": "sc_ex0103",
        "kp_id": "sc_kp0401",
        "type": "单选题",
        "difficulty": 2,
        "question": "CSRF 攻击利用的是？",
        "options": ["A. 用户已登录的会话凭证", "B. 服务器数据库漏洞", "C. 网络层协议缺陷", "D. 加密算法弱点"],
        "answer": 0,
        "analysis": "CSRF 诱导已登录用户在不知情下发起请求，借用了用户的登录凭证与会话。",
    },
    {
        "ex_id": "sc_ex0104",
        "kp_id": "sc_kp0702",
        "type": "单选题",
        "difficulty": 3,
        "question": "SQL 注入中，使用「1' OR '1'='1」的目的通常是？",
        "options": ["A. 绕过登录校验", "B. 删除数据库", "C. 修改密码", "D. 读取文件"],
        "answer": 0,
        "analysis": "构造恒真条件可让 WHERE 子句恒成立，从而绕过登录等逻辑校验。",
    },
    {
        "ex_id": "sc_ex0105",
        "kp_id": "sc_kp0902",
        "type": "单选题",
        "difficulty": 2,
        "question": "存储用户密码更安全的做法是？",
        "options": ["A. 明文存储", "B. 加盐哈希存储", "C. Base64 编码存储", "D. 对称加密后存储"],
        "answer": 1,
        "analysis": "加盐哈希（如 bcrypt、argon2）能抵御彩虹表与撞库，是推荐做法。",
    },
    {
        "ex_id": "sc_ex0201",
        "kp_id": "sc_kp0301",
        "type": "多选题",
        "difficulty": 2,
        "question": "XSS 攻击可能造成的危害包括？",
        "options": ["A. 窃取用户 Cookie", "B. 会话劫持", "C. 页面篡改", "D. 钓鱼攻击"],
        "answer": [0, 1, 2, 3],
        "analysis": "XSS 可窃取 Cookie、劫持会话、篡改页面、实施钓鱼等，危害广泛。",
    },
    {
        "ex_id": "sc_ex0202",
        "kp_id": "sc_kp0702",
        "type": "多选题",
        "difficulty": 3,
        "question": "防御 SQL 注入的常见措施包括？",
        "options": ["A. 参数化查询", "B. 预编译语句", "C. 最小权限原则", "D. 直接拼接用户输入"],
        "answer": [0, 1, 2],
        "analysis": "参数化查询、预编译语句与最小权限是防御手段；拼接用户输入是危险做法。",
    },
    {
        "ex_id": "sc_ex0203",
        "kp_id": "sc_kp0201",
        "type": "判断题",
        "difficulty": 2,
        "question": "浏览器同源策略要求协议、域名、端口三者都相同才视为同源。",
        "options": ["正确", "错误"],
        "answer": 0,
        "analysis": "同源策略以协议、域名、端口三者一致来判定同源。",
    },
    {
        "ex_id": "sc_ex0204",
        "kp_id": "sc_kp1104",
        "type": "判断题",
        "difficulty": 3,
        "question": "ECB 加密模式下，相同的明文块会产生相同的密文块。",
        "options": ["正确", "错误"],
        "answer": 0,
        "analysis": "ECB 是确定性的分块加密模式，相同明文块会得到相同密文块，泄露数据模式。",
    },
    {
        "ex_id": "sc_ex0301",
        "kp_id": None,
        "type": "编程题",
        "difficulty": 4,
        "question": "编写一个 Python 函数，用参数化查询的方式从数据库查询用户名对应的用户（避免 SQL 注入）。",
        "options": [],
        "answer": None,
        "analysis": "参考：cursor.execute('SELECT * FROM users WHERE username = ?', (username,))，使用占位符参数化，不拼接字符串。",
    },
]
