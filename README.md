# 基于大模型的个性化资源生成与学习多智能体系统

## 第十五届软件杯A3赛题

基于**讯飞星火大模型 + Astron智能体编排引擎 + 知识图谱**三大核心技术，实现对话式学生画像、多智能体协同生成个性化学习资源、知识图谱驱动的自适应学习路径，落地高校《人工智能导论》因材施教场景。

---

## 核心功能

1. **对话式学习画像**：5-10轮自然语言引导对话，自动抽取6维学生特征（知识基础、认知风格、学习偏好、易错类型、学习速度、目标方向）
2. **多智能体协同生成**：1个协调Agent + 5个专业执行Agent（诊断/教案/习题/代码/思维导图），并行生成5类个性化学习资源
3. **知识图谱驱动**：课程-章节-知识点三层DAG，≥12章节、100+知识点，前置校验+页面跳转+掌握度追踪
4. **自适应学习路径**：DAG拓扑排序 + 能力加权算法，动态推荐最优学习顺序

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.10+ / FastAPI / SQLAlchemy / PostgreSQL 16 |
| 向量库 | Chroma（讯飞星火Embedding） |
| 前端 | React 18 + Vite / Ant Design 5 |
| AI | 讯飞星火大模型（Spark Lite/Pro/Ultra） |
| 编排 | Astron智能体编排引擎 |
| 部署 | Docker + Docker Compose |

## 快速启动

```bash
# 1. 配置环境变量
cp backend/config/.env.example backend/config/.env
# 编辑 backend/config/.env 填入讯飞API密钥

# 2. 一键启动全部服务
docker-compose up -d

# 3. 访问
# 前端:     http://localhost:3000
# 后端API:  http://localhost:8000/docs
```

## 项目结构

```
a3-edu-agent-system/
├── docker-compose.yml          # 容器编排
├── README.md                   # 本文件
├── docs/                       # 赛事交付文档
│   ├── 开发说明书.md
│   ├── 测试说明书.md
│   ├── AI编码工具说明.md
│   └── 知识图谱数据.json
├── knowledge_base/             # 课程知识库
│   ├── chapters/               # 分章节讲义
│   ├── exercises/              # 习题+解析
│   └── code_demos/             # Python代码案例
├── backend/                    # FastAPI后端
│   ├── main.py                 # 入口
│   ├── config/                 # 配置
│   ├── db/                     # 数据库层
│   ├── agents/                 # 多智能体
│   ├── kg/                     # 知识图谱
│   ├── rag/                    # RAG向量检索
│   ├── api/                    # 接口路由
│   └── utils/                  # 工具类
└── frontend/                   # React前端
    └── src/
        ├── components/         # 通用组件
        ├── pages/              # 页面
        ├── store/              # 状态管理
        └── api/                # 请求封装
```

## 多智能体架构

```
前端请求 → 协调Agent（Coordinator）
              ├── 诊断Agent（Diagnose）  → 学生画像 + 知识断点
              ├── 教案Agent（Lesson）    → Markdown教案 + LaTeX公式
              ├── 习题Agent（Exercise）  → 针对性练习题 + 解析
              ├── 代码Agent（Code）      → Python代码 + 逐行注释
              └── 思维导图Agent（Mindmap）→ Mermaid脑图
```

## 数据库表

- `student_profile` - 学生画像（6维特征）
- `knowledge_point` - 知识点节点
- `kp_dependency` - 知识点依赖边（DAG）
- `student_mastery` - 学生知识点掌握度
- `learning_resource` - 学习资源
- `chat_record` - 对话记录

## 性能指标

- 对话响应：≤3s
- 单类资源生成：≤5s
- 全套资源生成：≤10s
- 并发：≥50用户同时在线

## 开发团队

第十五届软件杯A3赛题参赛作品
