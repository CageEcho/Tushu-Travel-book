# TripFlow · 旅行全流程助手

> 粘贴一篇小红书攻略 → 自动生成百度地图多途径点动线（比赛 demo：重庆特种兵 2 日游）。

## 当前进度
- 阶段 2（后端 MVP）✅、阶段 3（正式前端）✅ 已完成
- 单端口 `8000` 运行（前端 + 后端同源）
- 详情见 `项目状态.md`、证据包见 `证据包/阶段2/` 与 `证据包/阶段3/`

## 目录结构
```
旅行助手/
├── PRD-旅行全流程助手.md          # 产品需求文档
├── PRD补全清单.md                 # 阶段0 体检
├── 技术适配声明.md                # 阶段1
├── 第2阶段技术开发文档.md         # 阶段2 后端 MVP
├── 前端技术适配声明.md            # 阶段3 正式前端
├── 项目状态.md                    # 进度 + 决策台账
├── .env / .env.example            # 密钥（.env 不提交）
├── backend/                       # 后端（Python + FastAPI）
├── frontend/                      # 前端（Vite + React）
├── data/                          # 数据库 + 生成的长图/路线
└── 证据包/                        # 阶段2 / 阶段3 截图 + 验收文档
```

## 启动（单端口 8000）

```bash
# 1. 前端构建（首次 / 修改前端后）
cd frontend && npm install && npm run build

# 2. 后端启动（首次）
cd ../backend
python3.12 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/playwright install chromium        # 长图导出用

# 3. 启动服务
./.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

浏览器打开 http://127.0.0.1:8000/（预置 demo 链接，一键试试）。
手机（同一 WiFi）打开 http://<电脑IP>:8000/。

## 密钥（均不提交，已在 `.gitignore` 中忽略）
- 项目根 `.env`（从 `.env.example` 复制）：
  - `BAIDU_MAP_AK`：百度地图开放平台「服务端」AK
  - `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` / `DEEPSEEK_BASE_URL`：DeepSeek
  - `BAIDU_NAV_MAX_VIA`（每段最多途经点，默认 15）/ `BAIDU_URI_SRC`（唤起来源）
- `frontend/.env.local`（从 `frontend/.env.example` 复制）：
  - `VITE_BAIDU_BROWSER_AK`：百度地图「浏览器端」AK（JSAPI GL 交互地图），构建时注入 `index.html`

## 验证
```bash
cd backend
./.venv/bin/python -m pytest tests/ -q     # mock 自动化测试
./.venv/bin/python smoke_test.py           # 真实模型端到端冒烟（需先启动服务）
./.venv/bin/python e2e_frontend.py         # 前端完整闭环 E2E（需先启动服务）
```
