# 脉大夫 MaiPal v5

AI 中医四诊问诊系统 Web 端。基于 Node.js 后端 + 单页 HTML 前端，集成语音识别(STT)、文字转语音(TTS)、面诊/舌诊摄像头分析、调理计划、中医馆商城。

## 快速启动

```bash
# 1. 环境要求：Node.js 18+
node -v

# 2. 设置 API Key（用于 AI 对话功能）
export CODEBUDDY_API_KEY="your_api_key_here"

# 3. 启动服务
node server.js
# 服务运行在 http://localhost:3215

# 4. 打开主页面
# 浏览器访问 http://localhost:3215/index-v3.html
```

### 关于 API Key

对话功能依赖 CodeBuddy Claw API，需要设置 `CODEBUDDY_API_KEY` 环境变量。

- **没有 key 时**：服务可正常启动，页面 UI（调理计划、商城、TTS）均可预览，但 AI 对话无法使用
- **获取方式**：请联系项目维护者获取

> 💡 如需本地演示但无 key，可直接打开 `public/index-v3.html` 作为静态文件查看 UI（商城、调理计划页面均不依赖后端）

## 项目结构

```
├── server.js              # Node.js 后端（对话API转发 + TTS + 望诊代理）
├── package.json           # 项目配置
├── persona.md             # AI 角色设定 + 信号协议
├── public/
│   ├── index-v3.html      # 主页面（横屏版，含3个Tab页）
│   ├── index-v3-portrait.html  # 竖屏版（270°旋转）
│   ├── index.html         # 旧版页面
│   ├── report-demo.html   # 报告演示页
│   ├── assets/
│   │   ├── bg-shanshui.png     # 山水背景
│   │   ├── mai-standby.gif     # 数字人待机动画
│   │   ├── mai-speaking.gif    # 数字人说话动画
│   │   ├── image-7~18.png      # 商城商品/诊所图片
│   │   └── ...
│   └── ...
```

## 功能模块

### 三大 Tab 页
1. **调理计划** - 周日历、健康报告卡、每日养生任务（打卡+积分）
2. **脉医生** - AI 对话问诊、语音输入/播报、面诊/舌诊摄像头分析
3. **中医馆** - 药膳房（茶饮/炖汤/膏方）+ 看医生（合作诊所列表）

### 核心交互
- **TTS**：服务端 Edge-TTS（云健 YunjianNeural 男声）
- **STT**：浏览器 Web Speech API
- **望诊**：摄像头拍照 → 后端 MediaPipe + OpenCV 分析
- **信号协议**：AI 通过 `tool_call` 代码块触发前端动作（CAPTURE_FACE / CAPTURE_TONGUE / GENERATE_REPORT）

### 后端接口
| 路径 | 说明 |
|------|------|
| `/api/opening` | 获取开场白 |
| `/api/chat` | 流式对话（转发 Claw API） |
| `/api/tts` | 文字转语音 |
| `/api/diagnosis/face` | 面诊代理 → TCM 后端 |
| `/api/diagnosis/tongue` | 舌诊代理 → TCM 后端 |

## 依赖服务

- **望诊后端**（可选）：`tcm-diagnosis-platform/backend/app.py` 端口 8000
  - 需要 Python 3.11 + MediaPipe + OpenCV
  - 不启动时望诊功能不可用，但不影响对话

## 中英文切换

页面右上角设置按钮支持中英文切换，AI 回复语言会随之切换。

## License

MIT
