# 古代玉器沁色演化监测与仿古作伪识别系统

## 项目概述

某考古所对出土玉器200件（红山、良渚文化）布设拉曼光谱仪和X射线荧光光谱仪（各20台），每6小时通过5G上报数据。本系统实现了：

- 沁色扩散模型（基于菲克第二定律的Fe³⁺/Mn²⁺离子扩散）
- 仿古作伪识别（基于光谱特征的孤立森林异常检测）
- 告警系统（沁色深度>2mm或异常光谱特征触发，通过企业微信和WebSocket推送）
- Canvas+D3.js可视化展示

## 技术栈

- **后端**: Python 3.9+, Django 4.2, Django REST Framework
- **数据库**: MongoDB
- **前端**: HTML5 Canvas, D3.js
- **实时通信**: Django Channels (WebSocket)
- **算法**: 菲克第二定律扩散模型, 孤立森林异常检测

## 项目结构

```
project/
├── backend/                 # Django后端
│   ├── jade_monitor/       # 项目配置
│   ├── api/                # API接口
│   ├── algorithms/         # 算法模块
│   ├── alerts/             # 告警系统
│   ├── simulator/          # 5G数据模拟器
│   └── manage.py
├── frontend/               # 前端
│   ├── index.html
│   ├── css/
│   └── js/
└── mongodb/                # 数据库初始化
    └── init.js
```

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 初始化MongoDB

```bash
mongo < mongodb/init.js
```

### 3. 启动后端

```bash
cd backend
python manage.py runserver 0.0.0.0:8000
```

### 4. 启动5G模拟器

在API中调用启动接口，或直接运行：

```bash
cd backend
python -c "from simulator.jade_simulator import simulator; simulator.start(30)"
```

### 5. 访问前端

直接打开 `frontend/index.html`，或使用静态文件服务器。

## 核心API接口

### 玉器管理
- `GET /api/artifacts/` - 获取玉器列表
- `GET /api/artifacts/{id}/` - 获取玉器详情

### 光谱数据
- `GET /api/artifacts/{id}/raman/` - 获取拉曼光谱
- `GET /api/artifacts/{id}/xrf/` - 获取XRF光谱
- `POST /api/spectrum/upload/` - 上报告谱数据

### 分析算法
- `POST /api/artifacts/{id}/diffusion/` - 运行沁色扩散模拟
- `POST /api/artifacts/{id}/anomaly/` - 运行作伪识别
- `GET /api/artifacts/{id}/density-map/` - 获取沁色密度图

### 告警系统
- `GET /api/alerts/` - 获取告警列表
- `POST /api/alerts/{id}/acknowledge/` - 确认告警

### 模拟器
- `POST /api/simulator/start/` - 启动5G模拟
- `POST /api/simulator/stop/` - 停止5G模拟

## WebSocket接口

- `ws://localhost:8000/ws/alerts/` - 告警实时推送
- `ws://localhost:8000/ws/spectrum/{artifact_id}/` - 光谱实时更新

## 算法说明

### 沁色扩散模型

基于菲克第二定律：
- ∂C/∂t = D * ∂²C/∂x²
- D = D₀ * exp(-Q/RT) （阿伦尼乌斯方程）

支持的离子：Fe³⁺、Mn²⁺、Cu²⁺

### 孤立森林异常检测

从光谱数据中提取16维特征，使用孤立森林算法进行异常检测，输出作伪概率。

## 配置说明

主要配置项（settings.py）：
- `DIFFUSION_ALERT_THRESHOLD_MM`: 沁色深度告警阈值（默认2.0mm）
- `ANOMALY_SCORE_THRESHOLD`: 异常评分阈值（默认0.7）
- `WECHAT_WEBHOOK_URL`: 企业微信机器人Webhook地址
