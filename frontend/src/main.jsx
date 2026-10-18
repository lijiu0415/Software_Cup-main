import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import 'github-markdown-css/github-markdown.css'
import 'katex/dist/katex.min.css'
import './styles/global.css'
import { lightTheme } from './styles/theme'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ConfigProvider locale={zhCN} theme={lightTheme}>
      <App />
    </ConfigProvider>
  </React.StrictMode>
)
