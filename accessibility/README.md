# TC-BCI 用户应用（SSVEP 问答流程）

基于官方 `guienginemp` 引擎与官方 `UserApp/userapp.py` 框架，在**用户应用层**实现：

> 启动页(SSVEP 登录) → 科目选择(提示3s → SSVEP) → 人物画像(6组×[提示2s → SSVEP 5档])
> → 学习文字板(2s) → 做题(每题×[提示2s → SSVEP 4档]) → 完成。

所有 SSVEP 结果均来自 `EEGViewerDev.exe` **普通模式** 经 UDP `127.0.0.1:8093` 发送的
UTF-8 字符串 `"0"~"5"`。本应用只接收/消费结果，不实现任何 SSVEP 检测。

## 目录结构

```
run.py                     # 入口：python run.py
app/
  main.py                  # 构建布局 + 进入官方 mainLoop
  engine_layout.py         # 官方 settings/layout（原样）+ promptText 文字块 + App 引擎子类
  state_machine.py         # 页面状态机（状态流转 + UDP 消费 + 业务映射 + 防抖冷却）
  udp_client.py            # 监听 8093 的线程 + queue.Queue
  ssvep_context.py         # 运行时上下文
api/
  db_api.py                # 数据库接口（Mock）
  agent_api.py             # Agent 接口（Mock：agent_get_learning_path）
```

## 环境要求

- Python **3.11**（官方 `guienginemp` 提供 cp311 的 .whl）。
- 安装官方引擎与依赖（在你 Python 3.11 环境）：

```bash
pip install "d:/Ican/脑机b款蓝色开发版/脑机b款蓝色开发版/3.资料汇总～开发版/UserApp/package/guienginemp-0.1-cp311-cp311-win_amd64.whl"
pip install pygame pyserial requests
```

> 注：本机默认 `python` 是 3.12，加载不了 cp311 的 `.pyd`，请务必用 Python 3.11 运行。

## 运行 / 测试

1. 先启动 `EEGViewerDev.exe`，选**普通模式**（官方在此模式完成 SSVEP 检测，并向
   `127.0.0.1:8093` 发送结果）。
2. 在项目根目录运行：

```bash
python run.py
```

3. 流程自检（无真实设备时可先用一个 UDP 发送脚本模拟 `0~5` 结果，验证状态跳转）：

```python
# 模拟器（另开一个终端），例如发一个 "0" 给 8093：
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.sendto(b'0', ('127.0.0.1', 8093))
```

预期流程：启动页闪烁「游客登录/登录」→ 收到 `0` 进入科目提示页 → … 依此类推。

## 结果到业务映射（只叠加在官方 0~5 之上，不改频率）

| 页面 | 启用官方块 | 块文字 | 结果映射 |
|---|---|---|---|
| 启动页 | 0,1 | 游客登录 / 登录 | `0`→游客登录；`1`→登录暂未开放(停留) |
| 科目选择 | 0,1 | 软件安全 / 人工智能导论 | `0`→软件安全；`1`→人工智能导论 |
| 人物画像 | 0~4 | 1分~5分 | `r` → `r+1` 分（5 档） |
| 做题 | 0~3 | A/B/C/D | `r` → `'ABCD'[r]` |

## 防抖 / 冷却

- 单独线程收 8093，`0~5` 有效结果入 `queue.Queue`，脏数据忽略。
- 进入提示页 `drain()` 清队列；进入频闪页前再 `drain()` 一次。
- 只在 `*_SSVEP` 状态轮询，且只消费 `allowed_results` 内的**第一个**结果。
- 收到第一个有效结果：立即 `start=False` 停止刺激 → 选中块标红 → 清队列 → 冷却 1.5s → 跳转。
- 频闪页最多等 `FLASH_TIMEOUT=5` 秒，超时视为未检测到，短暂停顿后重试本页。

## 接口占位（先 Mock）

- `api/db_api.py`：`db_get_subjects / db_get_profile_questions / db_save_profile_answer /
  db_get_learning_content / db_get_quiz_question / db_submit_quiz_answer`
- `api/agent_api.py`：`agent_get_learning_path(profile_answers)`
- `db_get_quiz_question(subject, learning_path, step)` 返回该学习步骤的**题目列表**
  （Mock 每步 2 题），应用内部遍历「下一题」。

## Vue 前端集成（本地 WebSocket 桥）

本地 `ws://127.0.0.1:8765`（`app/bridge_server.py`）。Python 端推送事件，Vue 端订阅；
只做消息转发，不碰任何频率/刺激实现。

**消息协议（JSON）：**

Python -> 网页：
```json
{"type":"state",  "state":"profile_ssvep", "ctx":{...}}
{"type":"result", "state":"profile_ssvep", "result":2}
```
网页 -> Python：
```json
{"action":"restart"}
```

- `ctx` 快照含：`user_id / login_choice / subject / profile_answers / learning_path /
  profile_index / quiz_index / learning_step_index`。
- `result` 为官方 0~5；业务映射见 `web/useSSVEPBridge.js` 里的 `RESULT_MAP`
  （科目 0/1、画像 `r+1` 分、做题 `ABCD[r]`）。

**Vue 用法：**

```js
import { useSSVEPBridge } from './useSSVEPBridge'
const { connected, state, ctx, lastResult, send, onResult } = useSSVEPBridge()
onResult((r) => console.log('结果', r.result))
```

**联调测试：**

1. 启动应用 `python run.py`（桥自动监听 8765）。
2. 浏览器打开 `web/demo.html`（建议先 `python -m http.server` 起个静态服务再开，避免
   `file://` 下部分浏览器限制）。
3. 另开终端跑 `python demo_simulate.py`，即可在测试页看到状态/结果实时刷新。

## 需实机验证的两点（不影响频率）

1. `promptText` 的 `'class': 'Block'`：已在本机 Python 3.11 环境实例化验证通过
   （`promptText` 类型为 `Block`），无需改动。
2. 块上文字若较长（如「人工智能导论」6 个字在 300×200 块内可能略挤），可只调
   `textsize`/`textanchor`（纯显示参数，与频率无关）。

## 网页前端（最新架构）

- **前端工程**：`webapp/`（Vue3 + Vite，端口 5173）。`cd webapp && npm install && npm run dev`
- **接口文档**：见 [INTERFACE.md](INTERFACE.md)（WebSocket 协议 + 业务数据接口 + 结果映射）。
- 旧 `web/useSSVEPBridge.js`、`web/demo.html` 为早期联调件，已被 `webapp/` 取代，仅作参考。
- 分工：Python 管流程 + 频闪 + 收 8093；网页管全部文字/业务显示 + 记录结果。
