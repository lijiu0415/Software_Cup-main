# 接口文档（Python 桥 ↔ 网页前端）

## 架构分工

- **本地 Python（`app/`）**：只负责流程推进 + 频闪块启停 + 收 8093 结果 + 推事件。**不含任何业务内容。**
- **网页（`webapp/`，Vue3 + Vite）**：所有文字/业务内容显示、结果记录、业务映射、进度。

连接：`ws://127.0.0.1:8765`（本地 WebSocket）。

> 频闪块（6 个刺激频率）永远留在 Python 的 pygame 原生窗口，网页只显示业务 UI。

---

## 接口 1：WebSocket 消息协议

### Python → 网页（事件）

**状态事件**（每次状态变化发一次；进入同一状态重试不重复发）：
```json
{
  "type": "state",
  "state": "profile_prompt",
  "ctx": {
    "user_id": "guest_1792128307",
    "login_choice": "游客登录",
    "subject": "软件安全",
    "profile_answers": [1, 2, 3],
    "profile_index": 3,
    "quiz_index": 0,
    "learning_step_index": 0
  }
}
```

**结果事件**（收到一次有效 SSVEP 结果时发）：
```json
{ "type": "result", "state": "profile_ssvep", "result": 2 }
```

### 网页 → Python（命令）

```json
{ "action": "restart" }
```
预留（后续可加）：`{"action":"start"}`、`{"action":"set_meta","profile_count":6,"quiz_count":2,"learning_step_count":3}`。

### 状态清单

| state | 含义 | 网页显示 |
|---|---|---|
| `login_ssvep` | 启动页频闪 | 游客登录(块0) / 登录(块1) |
| `login_unavailable` | 登录暂未开放 | 提示文案 |
| `subject_prompt` | 科目提示（3s） | 「请进行想选择的科目」 |
| `subject_ssvep` | 科目频闪 | 软件安全(块0) / 人工智能导论(块1) |
| `profile_prompt` | 画像问题提示（2s） | 第 N 题文字 |
| `profile_ssvep` | 画像打分频闪 | 1~5分（块0~4） |
| `learning_text` | 学习文字板（2s） | 学习内容 |
| `quiz_prompt` | 做题提示（2s） | 题目文字 |
| `quiz_ssvep` | 做题频闪 | A/B/C/D（块0~3） |
| `done` | 完成 | 感谢文案 |

### 结果 → 业务映射（与块文字一致）

| state | 映射 |
|---|---|
| `login_ssvep` | 0→游客登录，1→登录 |
| `subject_ssvep` | 0→软件安全，1→人工智能导论 |
| `profile_ssvep` | `result + 1`（0~4 → 1~5 分） |
| `quiz_ssvep` | `'ABCD'[result]`（0~3 → A/B/C/D） |

---

## 接口 2：业务数据接口（网页端，Mock，可换后端）

在 `webapp/src/api/` 中，签名固定，换实现不改调用：

```js
// db.js
dbGetSubjects() -> ['软件安全','人工智能导论']
dbGetProfileQuestions() -> [{id, text} × 6]
dbGetLearningContent(subject, learningPath, step) -> text
dbGetQuizQuestion(subject, learningPath, step) -> [{id, text, answer} × 2]
dbSaveProfileAnswer(userId, questionId, score)
dbSubmitQuizAnswer(userId, questionId, answer)

// agent.js
agentGetLearningPath(profileAnswers) -> ['概念入门','标准训练','综合实践']
```

Python 端的旧 `api/db_api.py` / `agent_api.py` 已不再被调用（业务内容全部交给网页），仅保留签名供参考。

---

## 运行 / 联调

1. **Python 端**：`python run.py`（自动监听 8093 + 开 WebSocket 8765）
2. **网页端**：`cd webapp && npm install && npm run dev`（http://127.0.0.1:5173/）
3. **模拟结果**（无设备时）：`python demo_simulate.py`
4. 浏览器打开 5173，能看到登录页 → 科目 → 画像 → 学习 → 做题 → 完成 逐页切换；pygame 窗口并排显示频闪块。
