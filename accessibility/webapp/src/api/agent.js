// Agent 接口（Mock）。以后接真实 Agent/后端时，只替换实现，不改函数签名。

export function agentGetLearningPath(profileAnswers) {
  const total = (profileAnswers || []).reduce((a, b) => a + b, 0)
  let depth = '基础'
  if (total >= 24) depth = '进阶'
  else if (total >= 18) depth = '标准'
  return ['概念入门', `${depth}训练`, '综合实践']
}
