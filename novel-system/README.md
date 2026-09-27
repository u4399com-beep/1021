# novel-system · 小说管理系统

> Django + Vue + Celery + Playwright 一体化小说采集 / 站群 / 阅读系统

## 系统概览

```
┌─────────────────────────────────────────────────────────┐
│                  用户浏览器                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  后台管理    │  │  站群前台    │  │  Flower 监控 │    │
│  │  Vue+Element │  │  5 套主题    │  │              │    │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘    │
│         │                  │                              │
└─────────┼──────────────────┼─────────────────────────────┘
          │                  │
   ┌──────▼──────────────────▼─────┐
   │           Nginx (80)            │
   │  反向代理 + 多站点路由 + 静态资源 │
   └──────┬───────────────────┬─────┘
          │                   │
   ┌──────▼──────┐    ┌───────▼───────┐
   │  Vue Admin   │    │  Django API   │
   │  (Vite+Vue3) │    │  + Admin      │
   └─────────────┘    └───────┬───────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                   │
     ┌──────▼──────┐  ┌──────▼──────┐  ┌────────▼────────┐
     │  PostgreSQL │  │   Redis     │  │  Celery Workers │
     │  16 + pg_trgm│  │  Broker     │  │  crawler queue  │
     └─────────────┘  └─────────────┘  └─────────────────┘
                                              │
                                       ┌──────▼──────┐
                                       │  采集引擎    │
                                       │  3 段式 fallback:        │
                                       │  1) requests/httpx (轻)   │
                                       │  2) Firecrawl (AI 托管)   │
                                       │  3) Browser Use (LLM 驱动)│
                                       │  4) Playwright+Stealth (本地)│
                                       └─────────────┘
```

## 项目结构

```
novel-system/
├── backend/                    # Django 后端
│   ├── config/                 # Django 配置（base/dev/prod）
│   ├── apps/                   # Django 应用
│   │   ├── account/            # 用户认证 (JWT)
│   │   ├── novel/              # 书籍/章节/分类/标签
│   │   ├── crawler/            # 采集引擎入口（搜索引擎建议词等）
│   │   ├── crawler_rules/      # 采集规则 CRUD + 测试 API
│   │   ├── crawler_tasks/      # 采集任务 + Celery 编排
│   │   ├── content_cleaner/    # 内容清洗（正则/CSS/XPath）
│   │   ├── smart_classifier/   # 智能分类 + 完结判断
│   │   ├── themes/             # 主题模板元数据
│   │   ├── sites/              # 站群管理 + nginx 生成
│   │   ├── file_download/      # 文件下载（含混淆/广告）
│   │   └── api/                # Dashboard / 系统 API
│   ├── crawler_engine/         # 采集引擎核心
│   │   ├── fetcher.py          # 三段式 fallback fetcher
│   │   ├── parsers/            # 正则/CSS/XPath/JSONPath 解析器
│   │   ├── anti_detection/     # UA / Cookie / Proxy 池
│   │   ├── cleaners/           # 广告清洗
│   │   ├── utils/suggest.py    # 搜索引擎建议词
│   │   └── pipeline.py         # 端到端采集 pipeline
│   ├── management/commands/   # init_default_data / generate_nginx_conf
│   └── requirements/          # base / dev / prod
├── frontend/                   # Vue 3 后台
│   ├── src/
│   │   ├── api/                # 接口封装
│   │   ├── components/layout/  # AdminLayout
│   │   ├── router/             # 路由 + 鉴权
│   │   ├── stores/             # Pinia 用户状态
│   │   ├── styles/             # SCSS 全局
│   │   └── views/              # 后台所有页面
│   │       ├── dashboard/      # 工作台
│   │       ├── novels/         # 小说管理
│   │       ├── rules/          # 采集规则编辑器（带 Monaco + 测试）
│   │       ├── tasks/          # 采集任务（暂停/停止/参数调整）
│   │       ├── cleaner/        # 内容清洗
│   │       ├── classifier/     # 智能分类
│   │       ├── sites/          # 站群管理
│   │       ├── themes/         # 主题模板
│   │       ├── downloads/      # 文件下载
│   │       └── system/         # 系统设置（搜索引擎建议词）
│   └── vite.config.js
├── themes/                     # 5 套前台主题模板
│   ├── simple_reading/         # ★ 完整实现 (首页+详情+章节+分类)
│   ├── classic_shelf/          # ★ 完整实现 (古风)
│   ├── magazine_modern/        # 首页完整 (Flipboard 杂志风)
│   ├── dark_tech/              # 首页完整 (暗黑科技)
│   └── minimal_rank/           # 首页完整 (Goodreads 极简)
├── docker/
│   ├── docker-compose.yml      # 单机一键部署
│   ├── Dockerfile.backend      # Django + Celery + Playwright
│   ├── Dockerfile.frontend     # Vue build + nginx
│   ├── nginx/                  # nginx 配置
│   ├── postgres/init.sql       # PG 初始化 + pg_trgm 扩展
│   └── ...
├── docs/
│   └── DEPLOYMENT.md           # 详尽部署指南（必读）
├── .env.example
└── README.md
```

## 主要功能

### 1. 采集系统（核心）
- **三段式 fallback**：requests/httpx → Firecrawl → Browser Use → Playwright+Stealth
- **正则/CSS/XPath 三种解析器同时可用**，每条规则可在字段级别指定 selector 类型
- **四种采集目标**：列表页 / 书籍页 / 章节目录 / 章节内容
- **章节目录、章节内容支持分页**
- **反反爬策略**：UA 池、Cookie 池、JS 渲染、随机线程、随机间隔、Playwright Stealth
- **多线程采集**：可自定义 threads_min / threads_max 范围内随机
- **随机间隔**：interval_min / interval_max 范围内随机
- **章节乱序重排**：可选开启，配合站群防止内容雷同
- **去重策略**：按 URL 去重 / 按章节名去重（二选一或都开）
- **完全覆盖 / 增量更新**：两种采集模式
- **章节内容存储**：直接入库 / 生成 TXT / 两者
- **封面下载**：自动转 WebP 存到指定目录
- **任务生命周期**：草稿 → 已入队 → 运行中 → 已暂停 → 已停止 → 完成 / 失败
- **任务随时调整参数**：线程范围、间隔范围
- **规则即时测试**：每条规则编辑页都有测试按钮，可粘贴 HTML 或填 URL
- **任务可重复编辑、立即执行、暂停、停止**

### 2. 内容清洗
- 正则替换 / CSS 移除 / XPath 移除 / 字符串替换
- HTML 标签规范化（白名单 + 属性过滤）
- 广告模式识别（ad-、recommend-、copyright- 等通用规则）
- 试清洗功能（粘贴 HTML 看效果）
- 按优先级执行多条规则

### 3. 智能分类与完结判断
- jieba 分词 + 关键词命中权重
- 100+ 默认分类关键词（玄幻/奇幻/武侠等 15 个分类）
- 完结判断：正则匹配「已完结」「全本」「大结局」等模式
- 试分类 / 试完结判断

### 4. 站群系统
- 单后台 + 单数据库 + 单文件存储，多站点共用
- 每站点独立：域名、站名、主题、TDK、SEO/GEO、偏移量
- 偏移量机制：不同站点列表错位展示，避免雷同 SEO
- 一键生成 nginx 配置 + 自动 reload
- 主题可在后台随时切换

### 5. 5 套主题模板（前台）
| 主题 | 风格 | 完整度 |
|------|------|--------|
| simple_reading | 白底+衬线+暗灰，类似豆瓣读书 | ★★★ 完整 |
| classic_shelf | 木纹+宋体+卷轴，国风 | ★★★ 完整 |
| magazine_modern | 大图+粗标题+瀑布流，Flipboard | ★★ 首页完整 |
| dark_tech | 深色+霓虹+卡片，二次元 | ★★ 首页完整 |
| minimal_rank | 无尽列表+评分+标签云，Goodreads | ★★ 首页完整 |

每个主题均：
- 内置 TDK / SEO / GEO meta 标签
- 支持 head_inject / body_inject 自定义代码注入
- 支持 Schema.org 结构化数据（书籍页）
- 支持 canonical 链接
- 移动端响应式

### 6. 文件下载系统
- 输出 TXT / EPUB 两种格式
- 模板可配置：
  - 章节头部 / 尾部插入
  - 前言 / 后记
  - 站点信息块
  - 广告块（每章随机 30% 概率插入）
- **混淆功能**：零宽字符注入，绕过文本相似度检测
- 模板变量：`{site_name}` / `{book_title}` / `{book_author}` / `{book_intro}`

### 7. 搜索引擎建议词
- 调用百度 / 必应 / Google / 搜狗 的下拉建议 API
- 关键词作为关联标签存储
- 前台每个建议词独立 URL，全部重定向到主书籍页（SEO 集中）
- 后台「系统设置」页可立即拉取测试

### 8. 部署
- **docker-compose 单机一键部署**，包含：
  - PostgreSQL 16 + pg_trgm 扩展
  - Redis 7（broker + cache）
  - Django + gunicorn + uvicorn worker
  - Celery worker + beat + flower
  - Vue Admin (Vite build + nginx serve)
  - nginx 边缘代理
- **开箱即用**：首次启动自动 migrate + 初始化种子数据
- **Playwright Chromium 内置**：镜像构建时自动安装
- **完整部署文档**：`docs/DEPLOYMENT.md`（15 个章节，从环境检查到故障排查）

## 快速开始

```bash
# 1. 克隆 / 解压项目
cd /opt/novel-system

# 2. 配置环境变量
cp .env.example .env
vim .env  # 至少修改 DJANGO_SECRET_KEY 与 DB_PASSWORD

# 3. 启动
cd docker
docker compose up -d --build

# 4. 访问
# 后台管理: http://localhost/admin/    (admin / admin123456)
# API 文档: http://localhost/api/docs/
# 默认站点: http://localhost/
# Flower:   http://localhost:5555/flower

# 5. 修改管理员密码（重要）
docker compose exec backend python manage.py changepassword admin
```

完整部署细节见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)。

## API 速览

所有 API 在 `/api/v1/` 下，需 Bearer Token 认证（除登录外）。

| 端点 | 用途 |
|------|------|
| `POST /auth/login/` | 登录获取 JWT |
| `POST /auth/refresh/` | 刷新 Token |
| `GET /auth/me/` | 当前用户信息 |
| `GET /dashboard/` | 工作台统计 |
| `GET/POST /novels/books/` | 书籍 CRUD |
| `GET/POST /rules/` | 采集规则 CRUD |
| `POST /rules/test/` | 测试规则 |
| `GET/POST /tasks/` | 采集任务 CRUD |
| `POST /tasks/{id}/run/` | 启动任务 |
| `POST /tasks/{id}/pause/` | 暂停任务 |
| `POST /tasks/{id}/stop/` | 停止任务 |
| `GET /tasks/{id}/progress/` | 任务进度 |
| `GET/POST /sites/` | 站群管理 |
| `POST /sites/{id}/regenerate_nginx/` | 重新生成 nginx 配置 |
| `GET /themes/` | 主题列表 |
| `GET/POST /downloads/templates/` | 下载模板 |
| `POST /downloads/generate/generate/` | 触发文件生成 |
| `GET /crawler/suggest/?kw=斗破苍穹` | 搜索引擎建议词 |
| `GET /crawler/engine/status/` | 采集引擎各 Tier 状态（httpx/firecrawl/browser-use/playwright） |
| `POST /crawler/engine/test/` | 单 Tier 测试某个 URL |
| `POST /crawler/engine/fetch/` | 完整 fallback 链路抓取 |
| `GET/POST /auth/users/` | 用户 CRUD（需 `user.manage` 权限） |
| `GET/POST /auth/roles/` | 角色与权限管理 |
| `GET /auth/roles/catalog/` | 权限目录（18 个权限码） |
| `GET /seo/audit/` | 全站 SEO 检测 |
| `GET /seo/audit/<site_id>/` | 单站点 SEO 检测 |
| `POST /seo/regenerate-sitemaps/` | 重新生成 sitemap |
| `GET /sitemap.xml` | 默认站点 sitemap |
| `GET /rss.xml` | 默认站点 RSS |
| `GET /book/<slug>/rss.xml` | 单本书的章节 RSS |

完整 API Schema：`http://localhost/api/schema/`  ·  Swagger UI：`http://localhost/api/docs/`

## 默认账号

- 用户名：`admin`
- 密码：`admin123456`

**首次登录后请立即修改密码！**

## RBAC 权限

系统初始化 4 个内置角色（不可删除）：

| 角色 | 权限范围 |
|------|---------|
| `super_admin` | 全部权限（18 项） |
| `editor` | 编辑书籍、采集规则、清洗、分类、下载 |
| `operator` | 查看 + 执行/暂停/停止采集任务 |
| `viewer` | 只读 |

权限码 18 项，覆盖：novel / rule / task / cleaner / classifier / site / download / seo / user / system。

可在「用户与权限」页面创建自定义角色并分配任意权限组合。

## 二次开发

### 修改后端

```bash
docker compose exec backend bash
# 进入容器，修改代码后自动 reload（dev 模式）
```

### 修改前端

```bash
docker compose exec frontend sh
cd /app
npm install   # 如果新增依赖
npm run build # 重新构建
```

或本地开发：
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

### 修改主题

直接编辑 `themes/<code>/index.html` 与 `assets/*.css`。

修改后 nginx 容器内会立即反映（挂载了卷），浏览器强刷即可。

### 添加新的采集解析器

在 `backend/crawler_engine/parsers/selectors.py` 中扩展 `apply()` 函数。

## 许可证

私有项目，未授权不可复制或分发。

## 路线图（后续会话可迭代）

- [x] 完善 magazine_modern / dark_tech / minimal_rank 主题的 book_detail / chapter 页面
- [x] 增加 Firecrawl 和 Browser Use 实测集成（含 engine status / test / fetch API + 后台测试面板）
- [x] RBAC 多用户权限（4 个内置角色 + 18 个权限码 + 用户管理面板）
- [x] sitemap.xml 自动生成 + RSS 输出（站点级 RSS + 单本书章节 RSS）
- [x] SEO 自动检测面板（12 项检查：TDK / GEO / canonical / robots / sitemap / favicon / inject 等）
- [x] 采集任务定时调度（cron 表达式 + Celery beat + 后台编辑器 + 预览下次 5 次）
- [x] EPUB 封面嵌入（自动从 book.cover 或 cover_url 下载并嵌入 metadata + spine）
- [x] Hyperbrowser 代理池实测（会话池管理 + 手动创建/释放 + diagnostics + 后台管理）
- [ ] Hyperbrowser 多 region 代理池切换
- [ ] 代理池自动剔除低成功率代理
- [ ] EPUB 内嵌水印图片
- [ ] 任务调度优先级（多任务并发限制）

**手动验证指南**：见 [docs/OPERATIONS.md](docs/OPERATIONS.md)（包含 5 大场景的命令行 + 后台浏览器双路径验证步骤）。
