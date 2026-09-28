# novel-system 详细安装部署图文教程

> **版本**: v98 · **98 轮迭代** · 58 个数据模型 · 6 套主题模板
>
> **技术栈**: Django 4.2 + Vue 3 + Celery + PostgreSQL + Redis + Playwright + Docker

---

## 目录

1. [环境要求](#1-环境要求)
2. [方式一：一键部署（推荐）](#2-方式一一键部署推荐)
3. [方式二：手动部署](#3-方式二手动部署)
4. [首次配置](#4-首次配置)
5. [系统功能验证](#5-系统功能验证)
6. [常用运维命令](#6-常用运维命令)
7. [故障排查](#7-故障排查)
8. [升级与备份](#8-升级与备份)

---

## 1. 环境要求

| 项目 | 最低 | 推荐 |
|------|------|------|
| CPU | 2 核 | 4 核+ |
| 内存 | 2 GB | 4 GB+ |
| 磁盘 | 20 GB | 50 GB+ |
| 操作系统 | Ubuntu 20.04 / CentOS 8 / Debian 11 | Ubuntu 22.04 LTS |
| Docker | 24.0+ | 最新版 |
| Docker Compose | v2.20+ | 最新版 |

### 1.1 安装 Docker

```bash
# Ubuntu / Debian
curl -fsSL https://get.docker.com | bash
sudo systemctl enable --now docker

# 验证
docker --version          # 应显示 24.0+
docker compose version     # 应显示 v2.20+
```

### 1.2 安装 Docker Compose（如果版本不够）

```bash
# Docker Compose v2 已内置于 Docker Engine
# 如果 docker compose 不可用，安装插件：
sudo apt install docker-compose-plugin
```

---

## 2. 方式一：一键部署（推荐）

只需一条命令，自动完成从克隆到启动的全部步骤：

```bash
curl -fsSL https://raw.githubusercontent.com/u4399com-beep/1021/main/quick-deploy.sh | bash
```

或使用 wget：

```bash
wget -qO- https://raw.githubusercontent.com/u4399com-beep/1021/main/quick-deploy.sh | bash
```

脚本会自动执行以下 8 个步骤：
1. 检查/安装 Docker
2. 克隆项目到 `/opt/novel-system`
3. 生成 `.env` 配置文件（随机密钥）
4. 构建 Docker 镜像（10-15 分钟）
5. 启动 8 个服务容器
6. 数据库迁移 + 种子数据初始化
7. 导入 cunshu.la 采集规则
8. 验证服务状态

部署完成后，打开浏览器访问：

| 服务 | 地址 | 默认账号 |
|------|------|---------|
| 后台管理 | `http://服务器IP/admin/` | admin / admin123456 |
| 默认站点 | `http://服务器IP/` | - |
| API 文档 | `http://服务器IP/api/docs/` | - |
| Celery 监控 | `http://服务器IP:5555/flower` | - |

---

## 3. 方式二：手动部署

如果一键脚本不适用，或需要自定义配置，按以下步骤操作：

### 3.1 克隆项目

```bash
git clone https://github.com/u4399com-beep/1021.git /opt/novel-system
cd /opt/novel-system
```

### 3.2 配置环境变量

```bash
cp .env.example .env
vim .env
```

**必填项**：

```ini
# Django 密钥（至少 50 字符，用 openssl rand -hex 32 生成）
DJANGO_SECRET_KEY=你的随机密钥

# 数据库密码
DB_PASSWORD=你的数据库密码

# 允许的域名
ALLOWED_HOSTS=*
```

**可选项（按需启用）**：

```ini
# ─── 采集引擎 API Key（留空则跳过该 Tier） ───
FIRECRAWL_API_KEY=fc-xxxxx          # Firecrawl
OPENAI_API_KEY=sk-xxxxx             # Browser Use (需要 OpenAI)
HYPERBROWSER_API_KEY=hb-xxxxx       # Hyperbrowser 代理池

# ─── 验证码识别 ───
CAPTCHA_2CAPTCHA_KEY=               # 2captcha API Key

# ─── 读写分离 ───
DATABASE_REPLICA_ENABLED=false       # 设为 true 启用只读副本
```

### 3.3 构建并启动

```bash
cd /opt/novel-system/docker

# 构建镜像（首次约 10-15 分钟，主要是 Playwright Chromium 下载）
docker compose build

# 启动全部 8 个服务
docker compose up -d

# 查看服务状态
docker compose ps
```

正常输出应类似：

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

### 3.4 初始化数据

```bash
# 数据库迁移
docker compose exec backend python manage.py migrate --noinput

# 收集静态文件
docker compose exec backend python manage.py collectstatic --noinput

# 初始化种子数据（管理员账号 + 6 套主题 + 分类 + 清洗规则 + RBAC 权限）
docker compose exec backend python manage.py init_default_data

# 导入 cunshu.la 采集规则
docker compose exec backend python manage.py seed_cunshu_la_rules
```

### 3.5 修改管理员密码

```bash
docker compose exec backend python manage.py changepassword admin
```

---

## 4. 首次配置

### 4.1 添加采集源 + 规则

1. 打开 `http://服务器IP/admin/` → 用 admin 登录
2. 左侧菜单 → **采集规则**
3. 右上角「采集源管理」→ 添加源（域名 + 名称）
4. 返回列表 → **新建规则**
5. 选择目标类型（列表页/书籍页/章节目录/章节内容）
6. 在 Monaco 编辑器中粘贴 JSON 配置
7. 点击「测试」按钮验证解析结果
8. 保存规则

### 4.2 创建采集任务

1. 左侧菜单 → **采集任务** → 新建任务
2. 绑定 4 个规则（列表/书籍/目录/章节）
3. 配置参数：
   - 线程范围（如 2-5）
   - 间隔范围（如 1-3 秒）
   - 模式：完全覆盖 或 增量更新
   - 内容存储：数据库 / TXT / 两者
4. 智能选项：乱序重排、去重、清洗、分类、完结检测
5. 保存后点击「立即执行」

### 4.3 添加站点（站群管理）

1. 左侧菜单 → **站群管理** → 新建
2. 填写域名、站名、选择主题、TDK 配置
3. 保存后点击「重生 nginx」生成配置
4. 重载 nginx：`docker compose exec nginx nginx -s reload`

### 4.4 启用混淆（反爬指纹）

1. 左侧菜单 → **混淆与伪原创**
2. 选择站点 → 创建配置 → 启用
3. 配置 3 层混淆：
   - HTML 结构混淆（类名随机化、属性乱序、空白噪声）
   - 文本转码（半角→全角、同形字、零宽字符、标点变体）
   - 伪原创（同义词替换、句型重排、干扰句插入）
4. 保存后每次页面渲染都会生成唯一 HTML 结构

### 4.5 配置 SEO 检测

1. 左侧菜单 → **SEO 检测** → 刷新检测
2. 查看每站点的 12 项检查评分
3. 按建议修复 TDK / GEO / canonical / robots / sitemap
4. 点击「重新生成 sitemap」

---

## 5. 系统功能验证

### 5.1 验证采集引擎

```bash
# 查看各 Tier 状态
docker compose exec backend python /app/../scripts/test_crawler_engine.py --status

# 测试某个 URL
docker compose exec backend python /app/../scripts/test_crawler_engine.py https://www.example.com/list
```

### 5.2 运行综合测试

```bash
# v1-v18 测试
docker compose exec backend python /app/../scripts/test_v1_to_v16.py

# v19-v26 测试
docker compose exec backend python /app/../scripts/test_v19_to_v26.py

# v27-v53 测试
docker compose exec backend python /app/../scripts/test_v39_to_v53.py

# v54-v68 测试
docker compose exec backend python /app/../scripts/test_v54_to_v68.py

# v69-v83 测试
docker compose exec backend python /app/../scripts/test_v69_to_v83.py

# v84-v98 测试
docker compose exec backend python /app/../scripts/test_v84_to_v98.py
```

### 5.3 验证主题预览

```bash
# 在浏览器中打开
http://服务器IP/themes/preview.html      # 6 套主题总览
http://服务器IP/themes/uaa_clone/index.html  # 笔趣阁蓝
http://服务器IP/themes/simple_reading/    # 简约阅读
http://服务器IP/themes/classic_shelf/     # 古典书架
http://服务器IP/themes/magazine_modern/  # 杂志现代
http://服务器IP/themes/dark_tech/        # 暗黑科技
http://服务器IP/themes/minimal_rank/      # 极简榜单
```

### 5.4 验证健康状态

```bash
# 公开健康检查（无需认证）
curl http://服务器IP/api/v1/dashboard/health/public/

# 详细健康检查（需认证）
curl -H "Authorization: Bearer <TOKEN>" http://服务器IP/api/v1/dashboard/health/
```

---

## 6. 常用运维命令

### 6.1 服务管理

```bash
cd /opt/novel-system/docker

# 启动所有服务
docker compose up -d

# 停止所有服务
docker compose down

# 重启单个服务
docker compose restart backend
docker compose restart worker

# 查看日志
docker compose logs -f backend    # 后端日志
docker compose logs -f worker     # Celery worker 日志
docker compose logs -f nginx      # nginx 日志

# 进入容器
docker compose exec backend bash
docker compose exec postgres psql -U novel
```

### 6.2 数据库管理

```bash
# 备份数据库
docker compose exec -T postgres pg_dump -U novel novel > backups/novel_$(date +%Y%m%d).sql

# 恢复数据库
cat backups/novel_20240101.sql | docker compose exec -T postgres psql -U novel novel

# 触发自动备份
docker compose exec backend python manage.py shell -c "
from apps.dashboard.backup_engine import run_backup
print(run_backup())
"

# 数据完整性检查
curl -H "Authorization: Bearer <TOKEN>" \
  http://服务器IP/api/v1/dashboard/integrity/
```

### 6.3 采集任务管理

```bash
# 查看运行中的任务
docker compose exec backend python manage.py shell -c "
from apps.crawler_tasks.models import CrawlerTask
for t in CrawlerTask.objects.filter(status='running'):
    print(f'{t.id}: {t.name} — {t.processed_items}/{t.total_items}')
"

# 手动触发备份
curl -X POST -H "Authorization: Bearer <TOKEN>" \
  http://服务器IP/api/v1/dashboard/backup/trigger/

# 查看任务统计
curl -H "Authorization: Bearer <TOKEN>" \
  http://服务器IP/api/v1/tasks/stats/
```

---

## 7. 故障排查

### 7.1 服务无法启动

```bash
# 查看错误日志
docker compose logs backend --tail=50
docker compose logs postgres --tail=50
```

### 7.2 Playwright 安装失败

```bash
docker compose exec backend playwright install chromium
docker compose exec backend playwright install-deps chromium
```

### 7.3 502 Bad Gateway

```bash
# 检查后端是否运行
docker compose ps backend
# 检查后端日志
docker compose logs backend --tail=30
# 重启
docker compose restart backend
```

### 7.4 采集任务卡住

```bash
# 检查 Redis
docker compose exec redis redis-cli ping

# 检查 Celery worker
docker compose logs worker --tail=30

# 重置卡住的任务
docker compose exec backend python manage.py shell -c "
from apps.crawler_tasks.models import CrawlerTask
CrawlerTask.objects.filter(status='running').update(status='error', last_error='manual reset')
"

# 重启 worker
docker compose restart worker
```

---

## 8. 升级与备份

### 8.1 升级

```bash
cd /opt/novel-system
git pull origin main
cd docker
docker compose build
docker compose up -d
docker compose exec backend python manage.py migrate --noinput
```

### 8.2 定时备份（crontab）

```bash
crontab -e

# 每天凌晨 3 点备份数据库
0 3 * * * cd /opt/novel-system/docker && \
  docker compose exec -T postgres pg_dump -U novel novel > \
  /opt/novel-system/backups/novel_$(date +\%Y\%m\%d).sql && \
  find /opt/novel-system/backups -mtime +30 -delete

# 每天刷新 sitemap
0 4 * * * cd /opt/novel-system/docker && \
  docker compose exec -T backend python manage.py refresh_sitemaps
```

### 8.3 系统统计

```bash
# 系统总览
curl -H "Authorization: Bearer <TOKEN>" \
  http://服务器IP/api/v1/dashboard/summary/

# 看板数据
curl -H "Authorization: Bearer <TOKEN>" \
  "http://服务器IP/api/v1/dashboard/books-added/?period=month"

curl -H "Authorization: Bearer <TOKEN>" \
  "http://服务器IP/api/v1/dashboard/tasks-completed/?period=month"
```

---

## 附录：Docker Compose 服务说明

| 服务 | 容器名 | 端口 | 说明 |
|------|--------|------|------|
| PostgreSQL 16 | novel-postgres | 5433:5432 | 主数据库 |
| Redis 7 | novel-redis | 6380:6379 | 缓存 + Celery broker |
| Django Backend | novel-backend | 8000:8000 | REST API + Admin |
| Celery Worker | novel-worker | - | 采集任务执行 |
| Celery Beat | novel-beat | - | 定时调度 |
| Flower | novel-flower | 5555:5555 | Celery 监控 UI |
| Vue Frontend | novel-frontend | - | 后台管理 SPA |
| Nginx | novel-nginx | 80:80 | 反向代理 + 多站点路由 |

---

## 附录：一键部署命令

```bash
# 方式一：curl
curl -fsSL https://raw.githubusercontent.com/u4399com-beep/1021/main/quick-deploy.sh | bash

# 方式二：wget
wget -qO- https://raw.githubusercontent.com/u4399com-beep/1021/main/quick-deploy.sh | bash

# 方式三：手动克隆后执行
git clone https://github.com/u4399com-beep/1021.git /opt/novel-system
cd /opt/novel-system && bash quick-deploy.sh
```
