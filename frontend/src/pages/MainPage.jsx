import React from 'react'
import { Steps, message } from 'antd'
import { BookOutlined, FlagOutlined, FormOutlined } from '@ant-design/icons'
import useStore from '../store/useStore'
import QuestionnairePage from './QuestionnairePage'
import LearningPage from './LearningPage'
import LearningPathPage from './LearningPathPage'

const STEPS = [
  { title: '问卷画像', description: '填写评估问卷', icon: <FormOutlined /> },
  { title: '个性化规划', description: 'AI 生成学习路径', icon: <FlagOutlined /> },
  { title: '知识点学习', description: '生成学习资源', icon: <BookOutlined /> },
]

export default function MainPage() {
  const { currentStep, setCurrentStep, questionnaire_complete } = useStore()

  // 导航守卫：个性化规划 / 知识点学习前必须先完成问卷
  const handleStepChange = (step) => {
    if (step >= 1 && !questionnaire_complete) {
      message.warning('请先完成问卷，生成学习画像')
      setCurrentStep(0)
      return
    }
    setCurrentStep(step)
  }

  const renderStep = () => {
    switch (currentStep) {
      case 0:
        return <QuestionnairePage />
      case 1:
        return <LearningPathPage />
      case 2:
        return <LearningPage />
      default:
        return <QuestionnairePage />
    }
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* 顶部步骤条 */}
      <div style={{ flexShrink: 0, display: 'flex', justifyContent: 'center', marginBottom: 20 }}>
        <div style={{ maxWidth: 720, width: '100%', padding: '14px 24px', background: 'rgba(0,0,0,0.03)', borderRadius: 16, border: '1px solid rgba(0,0,0,0.08)' }}>
          <Steps
            current={currentStep}
            onChange={handleStepChange}
            items={STEPS}
            size="small"
            responsive={false}
          />
        </div>
      </div>

      {/* 内容区：按步骤渲染，带过渡 */}
      <div key={currentStep} className="step-fade-enter" style={{ flex: 1, minHeight: 0 }}>
        {renderStep()}
      </div>
    </div>
  )
}
