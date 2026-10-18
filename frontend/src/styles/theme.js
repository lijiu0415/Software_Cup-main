// 浅色柔和主题配置（AI 智育万象）
import { theme } from 'antd'

export const COLORS = {
  bg: '#F5F7FA',
  cardBg: 'rgba(255,255,255,0.85)',
  cardBorder: 'rgba(0,0,0,0.06)',
  primary: '#4A90F9',
  cyan: '#0EA5E9',
  accent: '#F59E0B',
  success: '#10B981',
  danger: '#EF4444',
  text: '#1F2733',
  textSecondary: '#6B7280',
}

// 玻璃拟态卡片通用样式
export const glassStyle = {
  background: COLORS.cardBg,
  backdropFilter: 'blur(10px)',
  WebkitBackdropFilter: 'blur(10px)',
  border: `1px solid ${COLORS.cardBorder}`,
  borderRadius: 14,
}

// 数字等宽加粗
export const monoStyle = {
  fontFamily: "'SF Mono','JetBrains Mono','Fira Code',Consolas,monospace",
  fontWeight: 700,
}

// Ant Design 浅色主题
export const lightTheme = {
  algorithm: theme.defaultAlgorithm,
  token: {
    colorPrimary: COLORS.primary,
    colorInfo: COLORS.cyan,
    colorLink: COLORS.cyan,
    colorSuccess: COLORS.success,
    colorWarning: COLORS.accent,
    colorError: COLORS.danger,
    colorBgBase: COLORS.bg,
    colorBgContainer: '#FFFFFF',
    colorBgElevated: '#FFFFFF',
    colorBgLayout: COLORS.bg,
    colorTextBase: COLORS.text,
    colorText: COLORS.text,
    colorTextSecondary: COLORS.textSecondary,
    colorBorder: 'rgba(0,0,0,0.1)',
    colorBorderSecondary: 'rgba(0,0,0,0.06)',
    borderRadius: 10,
    fontFamily:
      "'Inter','PingFang SC','HarmonyOS Sans SC','Microsoft YaHei',-apple-system,BlinkMacSystemFont,sans-serif",
    fontSize: 14,
  },
  components: {
    Card: {
      colorBgContainer: '#FFFFFF',
      colorBorderSecondary: 'rgba(0,0,0,0.06)',
      borderRadiusLG: 14,
    },
    Steps: {
      colorPrimary: COLORS.primary,
      colorText: COLORS.textSecondary,
    },
    Timeline: {
      colorPrimary: COLORS.cyan,
    },
    Tag: {
      defaultBg: 'rgba(0,0,0,0.05)',
    },
    Modal: {
      contentBg: '#FFFFFF',
      headerBg: 'transparent',
    },
    Button: {
      colorPrimary: COLORS.primary,
      primaryShadow: '0 0 12px rgba(74,144,249,0.3)',
    },
  },
}
