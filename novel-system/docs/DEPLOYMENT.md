# novel-system 部署指南

> 一套基于 Django + Vue + Celery + Playwright 的小说管理系统，含完整采集引擎、站群系统、5 套主题模板、文件下载系统，docker-compose 一键部署。

---

## 0. 系统要求

| 项目 | 最低 | 推荐 |
|------|------|------|
| CPU | 2 核 | 4 核+ |
| 内存 | 2 GB | 4 GB+ |
| 磁盘 | 20 GB | 50 GB+ (按书籍量) |
| Docker | 24.0+ | 最新 |
| Docker Compose | 2.20+ | 最新 |
| 端口 | 80 (nginx) | + 443 (SSL，可选) |

> Playwright 镜像会下载 Chromium 浏览器（约 200MB），首次构建较慢。

---

## 1. 准备环境

### 1.1 安装 Docker

**Ubuntu/Debian:**
```bash
curl -fsSL https://get.docker.com | bash
sudo systemctl enable --now docker
sudo apt install -y docker-compose-plugin
```

**CentOS/RHEL:**
```bash
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable --now docker
```

**验证安装:**
```bash
docker --version           # 24.0+
docker compose version     # v2.20+
```

### 1.2 准备目录

```bash
mkdir -p /opt/novel-system
cd /opt/novel-system
# 把 novel-system 项目代码放在此处
```

---

## 2. 配置环境变量

### 2.1 复制模板

```bash
cd /opt/novel-system
cp .env.example .env
```

### 2.2 编辑 .env

```bash
vim .env
```

**必填项：**

| 变量 | 说明 | 示例 |
|------|------|------|
| `DJANGO_SECRET_KEY` | Django 密钥，至少 50 字符 | 用 `openssl rand -hex 32` 生成 |
| `DB_PASSWORD` | PostgreSQL 密码 | `novel_pwd_strong_2024` |
| `ALLOWED_HOSTS` | 允许访问的域名 | `*` 或 `book.example.com,admin.book.com` |

**可选项（按需启用高级采集）：**

| 变量 | 说明 |
|------|------|
| `FIRECRAWL_API_KEY` | Firecrawl API 密钥（Tier-1 采集，留空跳过） |
| `BROWSER_USE_OPENAI_API_KEY` | OpenAI API 密钥（Tier-2 采集） |
| `HYPERBROWSER_API_KEY` | Hyperbrowser API 密钥 |
| `OPENAI_API_KEY` | 同上 |
| `PLAYWRIGHT_PROXY` | 采集时代理地址，例如 `http://127.0.0.1:7890` |

### 2.3 生成强密钥

```bash
openssl rand -hex 32   # → 替换 DJANGO_SECRET_KEY
openssl rand -base64 24 # → 替换 DB_PASSWORD
```

---

## 3. 构建并启动服务

### 3.1 一键启动

```bash
cd /opt/novel-system/docker
docker compose up -d --build
```

首次构建约需 5-15 分钟（取决于网速，主要在 Playwright Chromium 下载）。

### 3.2 检查服务状态

```bash
docker compose ps
```

应该看到 7 个服务全部为 `Up` / `healthy`：

```
NAME              STATUS         PORTS
novel-postgres    Up (healthy)   5433:5432
novel-redis       Up (healthy)   6380:6379
novel-backend     Up             8000:8000
novel-worker      Up
novel-beat        Up
novel-flower      Up             5555:5555
novel-frontend    Up
novel-nginx       Up             80:80
```

### 3.3 查看启动日志

```bash
docker compose logs -f backend
# 看到类似以下内容说明初始化成功:
# [celery] worker ready: ...
# Default data initialized.
# Application startup complete.
```

---

## 4. 初始化默认数据

启动时 `backend` 容器会自动执行：
1. `python manage.py migrate` — 数据库迁移
2. `python manage.py collectstatic` — 收集静态文件
3. `python manage.py init_default_data` — 初始化种子数据

种子数据包括：

| 数据 | 默认内容 |
|------|---------|
| 超级管理员 | 用户名 `admin`，密码 `admin123456` |
| 5 套主题 | 简约阅读 / 古典书架 / 杂志现代 / 暗黑科技 / 极简榜单 |
| 15 个分类 | 玄幻、奇幻、武侠、仙侠、都市等 |
| 8 条清洗规则 | script/style 移除、广告识别、空白处理等 |
| 100+ 分类关键词 | 用于智能分类 |
| 5 条完结规则 | 已完结/全本/大结局等模式 |
| 2 套下载模板 | TXT + EPUB |
| 18 个权限码 + 4 个内置角色 | RBAC（super_admin / editor / operator / viewer） |
| 默认站点 | localhost → simple_reading 主题 |

### 4.1 修改管理员密码（强烈建议）

```bash
docker compose exec backend python manage.py changepassword admin
```

---

## 4.5 配置采集引擎 API Key（可选）

启动后，后台 → 系统设置 → 采集引擎标签页可看到每个 Tier 的状态：

| Tier | 用途 | 依赖 | 配置方式 |
|------|------|------|---------|
| httpx | 静态页面 | 已内置 | 无需配置 |
| firecrawl | AI 托管爬虫（处理 JS+反爬） | `firecrawl-py` | `FIRECRAWL_API_KEY` |
| browser-use | LLM 驱动浏览器 | `browser-use` + `langchain-openai` | `BROWSER_USE_OPENAI_API_KEY` 或 `OPENAI_API_KEY` |
| playwright | 本地浏览器 + Stealth | `playwright` | 可选 `HYPERBROWSER_API_KEY` 走 CDP 远程浏览器 |

**首次配置**：编辑 `.env` 后重启：

```bash
vim /opt/novel-system/.env
# 设置 FIRECRAWL_API_KEY=fc-xxxxx
# 设置 OPENAI_API_KEY=sk-xxxxx
# 设置 HYPERBROWSER_API_KEY=hb-xxxxx
cd /opt/novel-system/docker
docker compose up -d
```

**测试采集引擎**：

后台 → 系统设置 → 采集引擎 → 填入 URL → 单 Tier 测试 / 完整 fallback 测试。

或者命令行：

```bash
docker compose exec backend python /app/../scripts/test_crawler_engine.py https://example.com/list --status
docker compose exec backend python /app/../scripts/test_crawler_engine.py https://example.com/list
docker compose exec backend python /app/../scripts/test_crawler_engine.py https://example.com/list --tier firecrawl
```

---

## 4.6 创建 RBAC 用户与角色

1. 后台 → 用户与权限 → 角色 tab → 新建角色 → 选择权限组合
2. 后台 → 用户与权限 → 用户 tab → 新建用户 → 选择角色
3. JWT 中携带 `permissions` 列表，前端会据此动态显示菜单

**内置 4 个角色**（不可删除，可在其基础上分配给用户）：

| 角色 | 适合 | 权限范围 |
|------|------|---------|
| `super_admin` | 技术管理员 | 全部 18 项 |
| `editor` | 内容编辑 | 书籍、采集规则、清洗、分类、下载 |
| `operator` | 采集操作员 | 查看 + 启停任务 |
| `viewer` | 只读用户 | 全部查看 |

---

## 4.7 启用 SEO 检测

后台 → SEO 检测 → 选择站点 → 查看检测详情：

- **12 项自动检查**：site_title、site_description、site_keywords、canonical、geo_region、geo_lang、robots_txt、sitemap_enabled、favicon、head_inject、body_inject、logo
- **评分**：0-100 分，绿（80+）/ 黄（60-79）/ 红（< 60）
- **修复建议**：每项失败检查给出具体建议

**生成 / 刷新 sitemap**：

后台 → SEO 检测 → 重新生成 sitemap 按钮（所有站点）

或定时任务（crontab 推荐）：

```bash
# 每天凌晨 3 点刷新所有站点的 sitemap
0 3 * * * cd /opt/novel-system/docker && docker compose exec -T backend \
  python manage.py refresh_sitemaps >> /var/log/novel-sitemaps.log 2>&1
```

**前台访问**：

- 默认站点 sitemap: `http://site1.com/sitemap.xml`
- 默认站点 RSS: `http://site1.com/rss.xml`
- 单本书 RSS: `http://site1.com/book/<slug>/rss.xml`

nginx 配置中已经把这些路由反代到 backend，开箱可用。

---

## 5. 访问系统

| 入口 | 地址 | 说明 |
|------|------|------|
| 后台管理 (Vue) | `http://localhost/admin/` | 管理采集规则、任务、站群、主题 |
| Django Admin | `http://localhost/django-admin/` | 原生 Django Admin（备用） |
| API 文档 | `http://localhost/api/docs/` | Swagger UI |
| 默认站点 | `http://localhost/` | 简约阅读主题前台 |
| Celery 监控 | `http://localhost:5555/flower` | Flower 任务监控 |

---

## 6. 添加第一个采集源

### 6.1 编写采集规则

1. 访问 `http://localhost/admin/` → 用 admin 账号登录
2. 左侧菜单 → 采集规则
3. 右上角「采集源管理」→ 添加源（域名 + 名称）
4. 返回列表 → 新建规则

**规则示例 — 起点中文网列表页:**

```json
{
  "item_selector": { "type": "css", "expr": "div.book-list > ul > li" },
  "book_url":     { "type": "xpath", "expr": ".//a/@href" },
  "book_title":   { "type": "css", "expr": "h3.title::text" },
  "book_author":  { "type": "css", "expr": "span.author::text" }
}
```

### 6.2 测试规则

在规则编辑页：
1. 填写测试 URL（如 `https://www.example.com/list/1.html`）
2. 点击「测试」按钮
3. 查看解析结果，调整 JSON 配置直到正确
4. 保存

### 6.3 创建采集任务

1. 左侧菜单 → 采集任务 → 新建任务
2. 选择目标类型 + 绑定 4 个规则（列表/书籍/目录/章节）
3. 配置：
   - 线程范围（如 2-5）
   - 间隔范围（如 1-3 秒）
   - 模式：完全覆盖 或 增量更新
   - 内容存储：数据库 / TXT / 两者
   - 智能选项：乱序、去重、清洗、分类、完结检测
4. 保存后点击「立即执行」

### 6.4 监控任务

- 任务列表实时显示进度
- 点击任务名查看详情、日志、调整参数
- 支持暂停 / 停止 / 重启

---

## 7. 添加站点（站群管理）

### 7.1 配置 DNS

为每个站点准备一个域名，将 A 记录指向当前服务器 IP。

例如：
```
site1.com → 1.2.3.4
site2.com → 1.2.3.4
admin.site1.com → 1.2.3.4  (可选，统一后台)
```

### 7.2 在后台添加站点

1. 后台 → 站群管理 → 新建
2. 填写：
   - 域名：`site1.com`
   - 站名：`小说站 1`
   - 主题：选 simple_reading
   - TDK：SEO 标题、描述、关键词
   - 偏移量：0（避免与 site2.com 内容完全重复）
3. 保存

### 7.3 生成 nginx 配置

后台 → 站群管理 → 选择站点 → 点击「重生 nginx」按钮

或命令行：

```bash
docker compose exec backend python manage.py generate_nginx_conf
```

### 7.4 重载 nginx

```bash
docker compose exec nginx nginx -s reload
```

或：

```bash
docker compose restart nginx
```

### 7.5 访问新站点

打开 `http://site1.com`（需 DNS 已生效），看到 simple_reading 主题界面。

---

## 8. 配置文件下载

### 8.1 模板管理

后台 → 文件下载 → 下载模板

可以编辑：
- 章节头部 / 尾部插入内容
- 前言 / 后记
- 站点信息块
- 广告块（每章随机 30% 概率插入）
- 混淆开关 + 密度 + 字符集

模板变量可用：
- `{site_name}` — 站点名
- `{book_title}` — 书名
- `{book_author}` — 作者
- `{book_intro}` — 简介

### 8.2 触发下载

方式一：API 触发
```bash
curl -X POST http://localhost/api/v1/downloads/generate/generate/ \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{"book_id": 1, "template_id": 1}'
```

方式二：前台按钮（用户点击书籍详情页的「下载」按钮，由前台发起请求）

### 8.3 文件存储位置

- 文本文件：`/opt/novel-system/backend/media/downloads/<book_id>/`
- 在后台「下载记录」可查看每次下载记录并下载文件

---

## 9. 备份与恢复

### 9.1 数据库备份

```bash
# 备份
docker compose exec postgres pg_dump -U novel novel > backups/novel_$(date +%Y%m%d).sql

# 恢复
cat backups/novel_20240927.sql | docker compose exec -T postgres psql -U novel novel
```

### 9.2 媒体文件备份

```bash
tar czf backups/media_$(date +%Y%m%d).tar.gz backend/media/
```

### 9.3 自动备份（crontab）

```bash
# 编辑 crontab
crontab -e

# 添加每天凌晨 3 点备份
0 3 * * * cd /opt/novel-system/docker && \
  docker compose exec -T postgres pg_dump -U novel novel > /opt/novel-system/backups/novel_$(date +\%Y\%m\%d).sql && \
  tar czf /opt/novel-system/backups/media_$(date +\%Y\%m\%d).tar.gz /opt/novel-system/backend/media/ 2>/dev/null

# 保留最近 30 天
0 4 * * * find /opt/novel-system/backups -mtime +30 -delete
```

---

## 10. 性能调优

### 10.1 调整 worker 数量

编辑 `docker/docker-compose.yml`：

```yaml
worker:
  command: >
    celery -A config worker
      --loglevel=info
      --concurrency=8     # ← 提高到 8
      -Q crawler,download,celery
```

```bash
docker compose up -d worker
```

### 10.2 调整 PostgreSQL

编辑 `docker/postgres/init.sql` 后重启：

```bash
docker compose down postgres
docker compose up -d postgres
```

### 10.3 增加 Redis 缓存

修改 `docker-compose.yml` 中 Redis 的 `--maxmemory` 参数。

### 10.4 启用 HTTPS

在 nginx 容器外层用 Caddy 或 nginx-proxy + Let's Encrypt 自动签发证书：

```bash
# 示例：用 Caddy 作为前置 TLS 反向代理
docker run -d --name caddy -p 443:443 -p 80:80 \
  -v /opt/caddy/Caddyfile:/etc/caddy/Caddyfile \
  caddy:latest
```

Caddyfile 示例：
```
site1.com {
  reverse_proxy localhost:80
}
admin.site1.com {
  reverse_proxy localhost:80
}
```

---

## 11. 故障排查

### 11.1 服务无法启动

```bash
docker compose logs backend   # 查看后端日志
docker compose logs worker    # 查看 worker 日志
docker compose logs nginx     # 查看 nginx 日志
```

### 11.2 Playwright 安装失败

进入 backend 容器手动安装：

```bash
docker compose exec backend playwright install chromium
docker compose exec backend playwright install-deps chromium
```

### 11.3 数据库连接失败

```bash
docker compose exec postgres pg_isready -U novel -d novel
docker compose exec backend python manage.py dbshell
```

### 11.4 任务卡住

```bash
# Flower 监控
访问 http://localhost:5555/flower

# 重启 worker
docker compose restart worker

# 查看任务状态
docker compose exec backend python manage.py shell
>>> from apps.crawler_tasks.models import CrawlerTask
>>> CrawlerTask.objects.filter(status='running').update(status='error', last_error='manual reset')
```

### 11.5 主题 404

```bash
# 检查主题目录是否挂载
docker compose exec nginx ls /usr/share/nginx/themes/

# 检查 nginx 配置
docker compose exec nginx cat /etc/nginx/conf.d/admin.conf
docker compose exec nginx ls /etc/nginx/sites-enabled/
```

---

## 12. 升级

### 12.1 拉取新版本

```bash
cd /opt/novel-system
git pull origin main
```

### 12.2 重建并迁移

```bash
cd docker
docker compose build
docker compose up -d
docker compose exec backend python manage.py migrate
```

### 12.3 重启服务

```bash
docker compose restart
```

---

## 13. 卸载

```bash
# 停止并删除容器
docker compose down -v   # -v 同时删除数据卷

# 删除镜像
docker rmi $(docker images | grep novel | awk '{print $3}')

# 删除目录
cd /opt
rm -rf novel-system
```

---

## 14. 常见问题 (FAQ)

**Q1: 第一次启动很慢？**
A: 主要在下载 Playwright Chromium（约 200MB），下载完后构建会很快。

**Q2: 采集任务一直 pending？**
A: 检查 worker 是否启动 (`docker compose ps worker`)；查看 Flower 是否有任务积压；检查 Redis 是否正常。

**Q3: 站点访问 404？**
A: 1) 检查 DNS 是否解析到服务器；2) 后台生成 nginx 配置后是否 reload；3) nginx 容器内 `/etc/nginx/sites-enabled/` 是否有该站点的 conf 文件。

**Q4: 采集到一半卡死？**
A: 1) 检查目标站点是否被封 IP（启用代理）；2) 检查 Playwright 是否有错误；3) 切换到 Browser Use 或 Firecrawl 试试。

**Q5: 章节内容乱码？**
A: 1) 编码问题，编辑 `crawler_engine/fetcher.py` 加 `chardet` 自动检测；2) 检查站点是否使用 GBK 等非 UTF-8 编码。

**Q6: 5 套主题前台只有 simple_reading 完整可用？**
A: simple_reading 和 classic_shelf 是完整实现（含 book_detail / chapter / category 页面）；magazine_modern / dark_tech / minimal_rank 完整实现了首页，详情/章节页是占位，需要按相同结构补充 HTML+CSS。

**Q7: 主题如何修改样式？**
A: 直接编辑 `/themes/<code>/assets/style.css`。修改后 nginx 容器需要 reload（或者浏览器强刷即可，因为 nginx 没有缓存）。

**Q8: 搜索引擎建议词功能怎么用？**
A: 后台 → 系统设置 → 搜索引擎建议词 标签页，输入关键词（书名）点击拉取，可以看到百度/必应/Google/搜狗的下拉建议词。这些词会作为关联关键词存储，前台通过 `SuggestKeyword` 表自动生成跳转链接，全部指向主书籍页。

---

## 15. 联系与反馈

- 项目结构、代码逻辑、问题排查：阅读 `README.md`
- API 文档：访问 `/api/docs/`
- 二次开发：见 `docs/DEVELOPMENT.md`

如有问题，请描述清楚：
1. 出错的环节（启动 / 采集 / 站群 / 下载）
2. `docker compose logs` 中的相关日志
3. 浏览器请求的 URL 与返回状态码
