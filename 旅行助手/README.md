# TripFlow · 旅行全流程助手

> 粘贴一篇小红书攻略 → 自动生成百度地图多途径点动线（比赛 demo：重庆特种兵 2 日游）。

## 当前进度
- 阶段 2（后端 MVP）用户已确认可用；阶段 3 正在按视觉参考迭代，尚待验收
- 单端口 `8000` 运行（前端 + 后端同源）
- 详情见 `开发文档/项目状态.md`、证据包见 `开发文档/证据包/阶段2/` 与 `开发文档/证据包/阶段3/`

## 如何继续开发（下次新会话）
直接告诉 AI：
> 继续旅行助手项目，先读 `开发文档/项目状态.md`，然后接上上次进度。

## 当前视觉预览（2026-09-29）
- 首页：http://127.0.0.1:8000/
- 地点确认代表页：http://127.0.0.1:8000/?trip=58ad7c22 （本机已有行程）
- 浅蓝渐变、三栏行程工作台、按天切换、地点卡片联动地图；手机切换清单/地图。
- 首页「试试这篇重庆攻略」只把示例链接填入输入框，由用户点发送再解析。
- 地点确认卡片名称前展示方形实景小图（点开看百科词条）：百度百科词条首图（按城市校验、排除小说/歌曲等同名词条与标志类白底图），后端下载缩略图缓存到 `data/assets/{id}/photos/`，接口 `GET /api/v1/trips/{id}/photos`；找不到可靠图片的地点不展示。
- 动线结果每天卡片结尾「今晚住哪」：以当天最后一站为锚点，按经济 / 舒适 / 高端各推荐一家（百度地点检索的档次、评分与评价数；无价格数据），接口 `GET /api/v1/trips/{id}/hotels`，结果缓存在 `data/assets/{id}/hotels.json`。
- 前端修改后在 `frontend` 执行 `npm run build`，刷新 8000 页面。验证使用 `npm run test`；构建已包含 TypeScript 检查。

## 未了项
- 代表页视觉反馈与截图验收
- 分享只读、运行中刷新恢复、生成后重新编辑等既有衔接问题
- ESLint 尚未配置；不将本次构建通过视为整个前端阶段验收通过

## 目录结构
```
旅行助手/
├── 开发文档/                      # 全部开发文档（见 0-目录.md）
│   ├── 0-目录.md
│   ├── PRD-旅行全流程助手.md
│   ├── PRD补全清单.md
│   ├── 技术适配声明.md
│   ├── 第2阶段技术开发文档.md
│   ├── 前端技术适配声明.md
│   ├── 项目状态.md
│   └── 证据包/（阶段2 / 阶段3）
├── backend/                       # 后端（Python + FastAPI）
├── frontend/                      # 前端（Vite + React）
├── data/                          # 数据库 + 生成的长图/路线
├── .env / .env.example            # 密钥（.env 已 gitignore）
└── README.md                      # 启动说明
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

## 密钥（`.env`）
- `BAIDU_MAP_AK`：百度地图开放平台「服务端」AK
- `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` / `DEEPSEEK_BASE_URL`：DeepSeek
- 浏览器端 AK（JSAPI GL 交互地图）：复制 `frontend/.env.example` 为 `frontend/.env.local`，填写 `VITE_BAIDU_JSAPI_AK`。本地配置及构建产物不上传 GitHub；修改后需重新构建。

## 验证
```bash
cd backend
./.venv/bin/python -m pytest tests/ -q     # mock 自动化测试
./.venv/bin/python smoke_test.py           # 真实模型端到端冒烟（需先启动服务）
./.venv/bin/python e2e_frontend.py         # 前端完整闭环 E2E（需先启动服务）
```

## 朋友协作

首次接手请阅读 [协作/接手说明.md](协作/接手说明.md)。新仓库保存最新源码和文档快照，不包含旧 Git 历史、密钥、本机数据库、依赖目录或构建产物。
