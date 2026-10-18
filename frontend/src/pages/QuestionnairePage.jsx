import React, { useState, useEffect } from 'react'
import {
  Card, Button, Radio, Checkbox, Input, Space, Typography, Tag, message, Spin, Result,
} from 'antd'
import {
  FormOutlined, CheckCircleFilled, EditOutlined, RocketOutlined,
} from '@ant-design/icons'
import useStore from '../store/useStore'
import { submitQuestionnaire, getQuestionnaireStatus } from '../api'

const { Title, Text } = Typography
const { TextArea } = Input

const buildSections = (course) => {
  const isSc = course === '软件安全技术'
  const cname = isSc ? '软件安全' : '人工智能'
  return [
    {
      title: '第一部分：基本信息与背景',
      questions: [
        { key: 'q1', type: 'single', text: '1. 您的年龄段是？', options: ['18岁以下', '18–24岁', '25–30岁', '31–40岁', '41岁及以上'] },
        { key: 'q2', type: 'single', text: '2. 您目前的身份是？', options: ['在校学生（本科及以下）', '在校研究生', '企业技术人员', '企业非技术岗位', '教师/科研人员', '自由职业者', '其他'] },
        { key: 'q3', type: 'single', text: '3. 您的最高学历（含在读）是？', options: ['高中及以下', '大专', '本科', '硕士', '博士'] },
        { key: 'q4', type: 'single', text: '4. 您所学的专业或从事的领域最接近以下哪一类？', options: ['计算机/软件工程/人工智能', '网络空间安全/信息安全', '数学/统计/数据科学', '电子/自动化/通信', '其他理工科', '人文社科/经管', '其他'] },
        { key: 'q5', type: 'single', text: '5. 您是否有编程经验？', options: ['完全没有', '了解基本语法，但很少实际编写', '能完成简单脚本或课程作业', '能独立开发中小型项目', '有较丰富的工程开发经验'] },
        { key: 'q6', type: 'multi', text: '6. 您常用的编程语言是？（多选）', options: ['无', 'Python', 'Java', 'C/C++', 'JavaScript/TypeScript', 'PHP', 'Go', '其他'] },
      ],
    },
    {
      title: isSc ? '第二部分：软件安全知识基础' : '第二部分：人工智能知识基础',
      questions: isSc ? [
        { key: 'q7', type: 'scale', text: '7. 您对以下软件安全基础概念的熟悉程度如何？（1–5 分，1=非常不熟悉，5=非常熟悉）', items: ['信息安全三要素（机密性/完整性/可用性）', '常见 Web 漏洞（XSS、CSRF、SQL 注入等）', '浏览器安全机制（同源策略、沙箱等）', '认证与会话安全', '访问控制与越权', '加密与密钥管理', '文件上传与文件包含漏洞', 'DDoS 与拒绝服务攻击', 'Web 框架与中间件安全', '安全开发生命周期（SDL）'] },
        { key: 'q8', type: 'single', text: '8. 您是否系统学习过网络安全或软件安全相关课程？', options: ['从未学习', '看过科普文章或视频', '完成过一门在线课程', '完成过多门课程或有系统教材学习', '有安全研究或渗透测试实践经验'] },
        { key: 'q9', type: 'single', text: '9. 您是否有过软件安全相关项目或实践（如 CTF、漏洞挖掘、安全开发）？', options: ['没有', '课程作业级别', '个人兴趣实践', '参与过 CTF/众测', '有安全研发或渗透测试项目'] },
        { key: 'q10', type: 'scale', text: '10. 您对以下软件安全应用领域的了解程度如何？（1–5 分）', items: ['Web 安全', '渗透测试', '代码审计', '密码学与加密应用', '移动/物联网安全', '安全运维与应急响应', '隐私保护与合规', '安全开发与 DevSecOps'] },
      ] : [
        { key: 'q7', type: 'scale', text: '7. 您对以下 AI 基础概念的熟悉程度如何？（1–5 分，1=非常不熟悉，5=非常熟悉）', items: ['人工智能的定义与图灵测试', '智能体与环境、PEAS描述', '搜索算法（BFS、DFS、A*）', '命题逻辑与一阶谓词逻辑', '知识图谱与本体论', '监督学习与无监督学习', '线性回归与逻辑回归', '决策树与集成学习', '支持向量机SVM', '神经网络与反向传播', 'CNN、RNN/LSTM', 'Transformer与注意力机制', '自然语言处理基础任务', '计算机视觉基础', '强化学习与Q-Learning', 'AI伦理、偏见与可解释性'] },
        { key: 'q8', type: 'single', text: '8. 您是否系统学习过机器学习或深度学习课程？', options: ['从未学习', '看过科普文章或视频', '完成过一门在线课程', '完成过多门课程或有系统教材学习', '有科研或工程项目实践经验'] },
        { key: 'q9', type: 'single', text: '9. 您是否有过 AI 相关项目实践？', options: ['没有', '课程作业级别', '个人兴趣项目', '企业/科研项目', '多个完整项目'] },
        { key: 'q10', type: 'scale', text: '10. 您对以下 AI 应用领域的了解程度如何？（1–5 分）', items: ['自然语言处理', '计算机视觉', '推荐系统', '自动驾驶', '医疗诊断', '金融风控', '强化学习与机器人', '大语言模型与生成式AI'] },
      ],
    },
    {
      title: '第三部分：多智能体系统认知',
      questions: [
        { key: 'q11', type: 'single', text: '11. 您对「多智能体系统」这一概念的了解程度如何？', options: ['从未听说', '听说过，但不了解具体含义', '了解基本概念', '能区分多智能体与单智能体', '有相关学习或实践经验'] },
        { key: 'q12', type: 'multi', text: '12. 您认为多智能体系统最吸引您的地方是什么？（多选）', options: ['多个智能体协作完成复杂任务', '智能体之间的竞争与博弈', '更接近真实世界的分布式问题求解', '可用于模拟社会、经济、生态系统', '与强化学习结合，实现群体智能', '其他'] },
        { key: 'q13', type: 'single', text: '13. 您希望在学习系统中以什么角色参与多智能体协作？', options: ['观察者：观看智能体行为并学习', '设计者：配置智能体规则与目标', '参与者：作为其中一个智能体参与任务', '训练者：通过反馈训练智能体', '研究者：分析智能体交互数据'] },
        { key: 'q14', type: 'scale', text: '14. 您对以下多智能体相关概念的熟悉程度如何？（1–5 分）', items: ['智能体分类（反射型、目标型、效用型等）', '环境类型（可观察性、确定性、静态性等）', '理性智能体与性能度量', '多智能体通信与协作', '博弈论与策略交互', '多智能体强化学习'] },
      ],
    },
    {
      title: '第四部分：学习偏好与需求',
      questions: [
        { key: 'q15', type: 'multi', text: '15. 您更倾向于哪种学习方式？（多选）', options: ['阅读文字教材', '观看视频讲解', '动手编写代码', '完成交互式练习', '参与项目实战', '与其他学习者讨论', '由智能体一对一辅导'] },
        { key: 'q16', type: 'multi', text: '16. 您希望学习系统提供哪些功能？（多选）', options: ['个性化学习路径推荐', '知识点掌握度诊断', '智能体对话答疑', '代码自动评测与反馈', '多智能体协作完成任务', '学习进度与成绩可视化', '错题与薄弱点复习', '其他'] },
        { key: 'q17', type: 'single', text: '17. 您每周愿意投入多少时间学习本系统内容？', options: ['少于1小时', '1–3小时', '3–5小时', '5–10小时', '10小时以上'] },
        { key: 'q18', type: 'multi', text: `18. 您学习${cname}知识的主要目的是什么？（多选）`, options: isSc ? ['通过课程考试', '提升职业技能', '转行进入安全领域', '满足个人兴趣', '参与科研项目', '参与 CTF/安全竞赛或开发安全产品', '其他'] : ['通过课程考试', '提升职业技能', '转行进入AI领域', '满足个人兴趣', '参与科研项目', '开发自己的AI应用', '其他'] },
        { key: 'q19', type: 'multi', text: `19. 您在学习${cname}过程中遇到的主要困难是什么？（多选）`, options: isSc ? ['数学/密码学基础薄弱', '编程与安全工具使用能力不足', '概念抽象难以理解', '缺乏实践环境（靶场/CTF）', '学习资源太多，不知如何选择', '难以坚持，缺乏反馈', '没有遇到明显困难', '其他'] : ['数学基础薄弱', '编程能力不足', '概念抽象难以理解', '缺乏实践项目', '学习资源太多，不知如何选择', '难以坚持，缺乏反馈', '没有遇到明显困难', '其他'] },
        { key: 'q20', type: 'scale', text: '20. 您对智能体学习伙伴的期望是什么？（1–5 分，1=非常不重要，5=非常重要）', items: ['能理解我的问题并准确回答', '能根据我的水平调整讲解方式', '能主动发现我的知识薄弱点', '能与我进行多轮深入讨论', '能模拟多种角色（教师、同学、考官等）', '能与其他智能体协作共同帮助我'] },
      ],
    },
    {
      title: isSc ? '第五部分：安全伦理与风险意识' : '第五部分：技术态度与伦理意识',
      questions: isSc ? [
        { key: 'q21', type: 'single', text: '21. 您对软件安全/网络安全行业发展的总体态度是？', options: ['非常乐观，前景广阔', '比较乐观，但安全风险严峻', '中立', '比较担忧，攻防失衡', '非常担忧，安全形势严峻'] },
        { key: 'q22', type: 'scale', text: '22. 您对以下安全与伦理问题的关注程度如何？（1–5 分，1=完全不关注，5=非常关注）', items: ['个人隐私泄露', '网络攻击与数据泄露', 'AI 与自动化攻击', '安全漏洞频发', '安全人才短缺', '安全技术与法律伦理边界'] },
        { key: 'q23', type: 'single', text: '23. 您是否了解安全伦理与法规（如《网络安全法》、漏洞披露规范）？', options: ['完全不了解', '听说过相关法规', '了解基本原则', '较熟悉并遵守相关规范', '有深入研究或实践'] },
        { key: 'q24', type: 'single', text: '24. 如果学习系统使用您的学习数据来优化智能体行为，您的态度是？', options: ['完全接受', '接受，但希望知情', '接受，但希望可随时删除', '不太接受', '完全不接受'] },
      ] : [
        { key: 'q21', type: 'single', text: '21. 您对 AI 技术发展的总体态度是？', options: ['非常乐观，认为利大于弊', '比较乐观，但需关注风险', '中立', '比较担忧，需谨慎发展', '非常担忧，可能带来严重问题'] },
        { key: 'q22', type: 'scale', text: '22. 您对以下 AI 伦理问题的关注程度如何？（1–5 分，1=完全不关注，5=非常关注）', items: ['隐私侵犯', '算法歧视', '就业替代', '安全风险', '可解释性不足', '对抗攻击与数据投毒'] },
        { key: 'q23', type: 'single', text: '23. 您是否了解可解释 AI（XAI）相关方法？', options: ['完全不了解', '听说过LIME或SHAP', '了解基本原理', '使用过相关工具', '有深入研究或实践'] },
        { key: 'q24', type: 'single', text: '24. 如果学习系统使用您的学习数据来优化智能体行为，您的态度是？', options: ['完全接受', '接受，但希望知情', '接受，但希望可随时删除', '不太接受', '完全不接受'] },
      ],
    },
    {
      title: '第六部分：开放性问题（选填）',
      questions: [
        { key: 'q25', type: 'open', text: `25. 您希望在本系统中优先学习哪些${cname}主题？请简要列出。` },
        { key: 'q26', type: 'open', text: '26. 您对多智能体学习系统有什么期待或建议？' },
        { key: 'q27', type: 'open', text: `27. 您认为自己目前${cname}知识水平的最大优势与最大短板分别是什么？` },
      ],
    },
  ]
}

const LETTER = (i) => String.fromCharCode(65 + i)

export default function QuestionnairePage() {
  const { studentId, studentProfile, setStudentProfile, setQuestionnaireComplete, setCurrentStep } = useStore()
  const course = studentProfile?.course || '人工智能导论'
  const sections = buildSections(course)
  const [answers, setAnswers] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [loading, setLoading] = useState(true)
  const [done, setDone] = useState(false)
  const [result, setResult] = useState(null)

  useEffect(() => {
    let active = true
    const load = async () => {
      if (!studentId) { setLoading(false); return }
      try {
        const res = await getQuestionnaireStatus(studentId, course)
        if (!active) return
        if (res.data.completed) {
          setAnswers(res.data.answers || {})
          setResult({ profile: res.data.profile, summary: res.data.summary })
          setDone(true)
          setQuestionnaireComplete(true)
        }
      } catch {
        // 首屏失败不阻塞
      } finally {
        if (active) setLoading(false)
      }
    }
    load()
    return () => { active = false }
  }, [studentId, course, setQuestionnaireComplete])

  const setAnswer = (key, value) => setAnswers((prev) => ({ ...prev, [key]: value }))

  const setScaleItem = (key, idx, value) => {
    setAnswers((prev) => {
      const items = sections.flatMap((s) => s.questions).find((q) => q.key === key)?.items || []
      const arr = Array.isArray(prev[key]) ? [...prev[key]] : items.map(() => 0)
      arr[idx] = value
      return { ...prev, [key]: arr }
    })
  }

  const collectUnanswered = () => {
    const all = sections.flatMap((s) => s.questions)
    const missing = []
    for (const q of all) {
      if (q.type === 'open') continue
      const v = answers[q.key]
      if (q.type === 'scale') {
        if (!Array.isArray(v) || v.length < q.items.length || v.some((x) => !x)) missing.push(q.text.split('.')[0])
      } else if (q.type === 'multi') {
        if (!Array.isArray(v) || v.length === 0) missing.push(q.text.split('.')[0])
      } else if (!v) {
        missing.push(q.text.split('.')[0])
      }
    }
    return missing
  }

  const handleSubmit = async () => {
    const missing = collectUnanswered()
    if (missing.length > 0) {
      message.warning(`还有 ${missing.length} 题未作答，请完成后提交`)
      return
    }
    setSubmitting(true)
    try {
      const res = await submitQuestionnaire(studentId, answers, course)
      const profile = res.data.profile || {}
      setStudentProfile(profile)
      setQuestionnaireComplete(true)
      setResult({ profile, summary: res.data.summary || '' })
      setDone(true)
      message.success('问卷已提交，学习画像已生成')
    } catch {
      message.error('提交失败，请稍后重试')
    } finally {
      setSubmitting(false)
    }
  }

  const handleReEdit = () => {
    setDone(false)
    setResult(null)
  }

  if (loading) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (done && result) {
    const p = result.profile
    return (
      <div style={{ height: '100%', overflow: 'auto', display: 'flex', justifyContent: 'center' }}>
        <Card className="glass-card" style={{ maxWidth: 640, width: '100%', alignSelf: 'flex-start' }}>
          <Result
            icon={<CheckCircleFilled style={{ color: '#10B981' }} />}
            title="学习画像已生成"
            subTitle={result.summary || '问卷分析完成，已据此生成您的个性化学习画像'}
          />
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center', marginBottom: 20 }}>
            {p.course && <Tag color="blue" style={{ fontSize: 14, padding: '4px 12px' }}>课程：{p.course}</Tag>}
            {p.base_level != null && <Tag color="cyan" style={{ fontSize: 14, padding: '4px 12px' }}>基础 {p.base_level}/5</Tag>}
            {p.learn_goal && <Tag color="geekblue" style={{ fontSize: 14, padding: '4px 12px' }}>{p.learn_goal}</Tag>}
            {p.cognitive_style && <Tag color="purple" style={{ fontSize: 14, padding: '4px 12px' }}>{p.cognitive_style}</Tag>}
            {p.learn_preference && <Tag color="green" style={{ fontSize: 14, padding: '4px 12px' }}>{p.learn_preference}</Tag>}
            {p.learn_speed != null && <Tag color="orange" style={{ fontSize: 14, padding: '4px 12px' }}>速度 {p.learn_speed}/5</Tag>}
          </div>
          <Space direction="vertical" style={{ width: '100%' }} size={12}>
            <Button block type="primary" icon={<RocketOutlined />} onClick={() => setCurrentStep(1)}>
              进入个性化规划
            </Button>
            <Button block type="text" icon={<EditOutlined />} onClick={handleReEdit}>
              重新填写问卷
            </Button>
          </Space>
        </Card>
      </div>
    )
  }

  return (
    <div style={{ height: '100%', overflowY: 'auto', paddingRight: 8 }}>
      <div style={{ maxWidth: 760, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 16, paddingBottom: 80 }}>
        <Card className="glass-card">
          <Space align="start">
            <FormOutlined style={{ fontSize: 22, color: '#4A90F9' }} />
            <div>
              <Title level={4} style={{ margin: 0 }}>用户评估问卷</Title>
              <Text type="secondary" style={{ fontSize: 13 }}>
                请根据真实情况作答（约 10–15 分钟）。单选/多选/量表为必答，开放题选填。作答仅用于学习画像与系统适配。
              </Text>
            </div>
          </Space>
        </Card>

        {sections.map((sec) => (
          <Card key={sec.title} className="glass-card" title={<span style={{ fontSize: 15 }}>{sec.title}</span>}>
            <Space direction="vertical" size={20} style={{ width: '100%' }}>
              {sec.questions.map((q) => (
                <div key={q.key}>
                  <div style={{ fontWeight: 600, marginBottom: 8, color: '#1F2733', fontSize: 14 }}>{q.text}</div>

                  {q.type === 'single' && (
                    <Radio.Group
                      value={answers[q.key]}
                      onChange={(e) => setAnswer(q.key, e.target.value)}
                      style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
                    >
                      {q.options.map((op, i) => (
                        <Radio key={i} value={LETTER(i)} style={{ color: '#1F2733' }}>
                          {LETTER(i)}. {op}
                        </Radio>
                      ))}
                    </Radio.Group>
                  )}

                  {q.type === 'multi' && (
                    <Checkbox.Group
                      value={answers[q.key] || []}
                      onChange={(v) => setAnswer(q.key, v)}
                      style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
                    >
                      {q.options.map((op, i) => (
                        <Checkbox key={i} value={LETTER(i)} style={{ color: '#1F2733' }}>
                          {LETTER(i)}. {op}
                        </Checkbox>
                      ))}
                    </Checkbox.Group>
                  )}

                  {q.type === 'open' && (
                    <TextArea
                      rows={3}
                      value={answers[q.key] || ''}
                      onChange={(e) => setAnswer(q.key, e.target.value)}
                      placeholder="（选填）请简要作答"
                      style={{ fontFamily: 'inherit' }}
                    />
                  )}

                  {q.type === 'scale' && (
                    <div style={{ overflowX: 'auto' }}>
                      <div style={{ display: 'flex', minWidth: 520, padding: '6px 0', borderBottom: '1px solid rgba(0,0,0,0.08)', color: '#6B7280', fontSize: 12 }}>
                        <div style={{ flex: 1 }}>条目</div>
                        {[1, 2, 3, 4, 5].map((n) => (
                          <div key={n} style={{ width: 44, textAlign: 'center' }}>{n}</div>
                        ))}
                      </div>
                      {q.items.map((item, idx) => {
                        const val = answers[q.key]?.[idx]
                        return (
                          <div key={idx} style={{ display: 'flex', minWidth: 520, padding: '8px 0', alignItems: 'center', borderBottom: '1px solid rgba(0,0,0,0.04)' }}>
                            <div style={{ flex: 1, fontSize: 13, color: '#1F2733' }}>{item}</div>
                            {[1, 2, 3, 4, 5].map((n) => (
                              <div key={n} style={{ width: 44, textAlign: 'center' }}>
                                <Radio
                                  checked={val === n}
                                  onChange={() => setScaleItem(q.key, idx, n)}
                                />
                              </div>
                            ))}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              ))}
            </Space>
          </Card>
        ))}

        <Card className="glass-card" style={{ position: 'sticky', bottom: 0, zIndex: 10 }}>
          <Button type="primary" block size="large" loading={submitting} onClick={handleSubmit}>
            提交问卷，生成学习画像
          </Button>
        </Card>
      </div>
    </div>
  )
}
