# 运维手动验证指南

> 本指南配合 `scripts/` 下的三个端到端测试脚本，用于在 Docker 部署后验证系统的关键功能是否正常工作。

---

## 准备

确保系统已经按 `docs/DEPLOYMENT.md` 完成部署，所有容器健康：

```bash
cd /opt/novel-system/docker
docker compose ps
# 应该看到 8 个服务全部 Up / healthy
```

进入 backend 容器执行测试脚本：

```bash
docker compose exec backend bash
# 容器内：
cd /app
ls /app/../scripts/   # 应该看到 test_*.py
```

---

## 1. 验证采集引擎各 Tier

### 1.1 配置 API Key

编辑宿主机 `.env`：

```bash
vim /opt/novel-system/.env
```

填入：

```env
FIRECRAWL_API_KEY=fc-xxxxxxxxxxxxxxxxxxxxxxxx
BROWSER_USE_OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
HYPERBROWSER_API_KEY=hb-xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
BROWSER_USE_MODEL=gpt-4o-mini
```

重启 backend + worker 让新 env 生效：

```bash
cd /opt/novel-system/docker
docker compose up -d backend worker
```

### 1.2 命令行验证 Tier 状态

```bash
docker compose exec backend python /app/../scripts/test_engine_e2e.py --status
```

预期输出：

```
=== Crawler Engine Status ===
  httpx          installed=True configured=True
  firecrawl      installed=True  configured=True
  browser-use    installed=True  configured=True
  playwright     installed=True  configured=True  hyperbrowser=True
```

如果某 Tier 的 `configured=False`，说明对应的 API Key 没正确传入容器，检查 `.env` 与 `docker-compose.yml` 的 `x-backend-env`。

### 1.3 实测 URL

```bash
# 自动 fallback（按顺序：httpx → firecrawl → browser-use → playwright）
docker compose exec backend python /app/../scripts/test_engine_e2e.py https://www.qidian.com/all

# 单 Tier 测试
docker compose exec backend python /app/../scripts/test_engine_e2e.py https://www.qidian.com/all --tier firecrawl

# 所有 Tier 都试一遍（即使某个已成功）
docker compose exec backend python /app/../scripts/test_engine_e2e.py https://www.qidian.com/all --all
```

预期：

```
[1/3] 采集引擎 Tier 状态
[2/3] Hyperbrowser 代理池状态
  API Key: 已配置
  活跃会话数: 0

[3/3] 实测 URL: https://www.qidian.com/all
  ✓ httpx           523ms  size=  12345  err=
→ 结果: 至少一个 Tier 成功
```

### 1.4 浏览器后台验证

打开 `http://localhost/admin/system` → 「采集引擎」tab：

- 看到 4 个 Tier 的状态表
- 填入测试 URL，点「单 Tier 测试」/ 「完整 fallback 测试」
- 测试结果展示在表格中（含耗时、HTML 大小、错误）

切换到「代理池」tab：添加代理、批量检测、查看成功率。

切换到「Hyperbrowser」tab：看到 API Key 状态、活跃会话列表、手动创建会话按钮。

---

## 2. 验证 RBAC 用户与权限

### 2.1 命令行端到端测试

```bash
docker compose exec backend python /app/../scripts/test_rbac_e2e.py
```

预期输出（关键部分）：

```
【1/4】 验证内置角色与权限目录
  权限目录大小: 18
  数据库中的 Permission 数: 18
  数据库中的 Role 数: 4
    - super_admin     perms=18  users=1  system=True
    - editor          perms=10  users=0  system=True
    - operator        perms= 6  users=0  system=True
    - viewer          perms= 5  users=0  system=True

【2/4】 创建测试用户
  ✓ editor:    username=test_editor  password=xxxxxxxxxxxxxxxx  roles=['editor']
  ✓ operator:  username=test_operator  password=xxxxxxxxxxxxxxxx  roles=['operator']

【3/4】 JWT Token 中权限验证
  editor   permissions (10): ['novel.view', 'novel.edit', 'novel.delete', 'rule.view', 'rule.edit', 'cleaner.edit', 'classifier.edit', 'download.manage', 'seo.view', 'system.view']
  operator permissions (6):  ['novel.view', 'rule.view', 'task.view', 'task.run', 'seo.view', 'system.view']

【4/4】 菜单可见性模拟（前端会按此过滤）
  ─── EDITER (test_editor) ───
    ✓ /admin/dashboard    requires=(none)
    ✓ /admin/novels       requires=novel.view
    ✓ /admin/rules       requires=rule.view
    ✓ /admin/cleaner     requires=cleaner.edit
    ✓ /admin/classifier  requires=classifier.edit
    ✓ /admin/downloads   requires=download.manage
    ✓ /admin/seo         requires=seo.view
    ✓ /admin/system      requires=system.view
    ✗ /admin/sites       requires=site.manage
    ✗ /admin/themes      requires=site.manage
    ✗ /admin/tasks       requires=task.view
    ✗ /admin/users       requires=user.manage

  ─── OPERATOR (test_operator) ───
    ✓ /admin/dashboard    requires=(none)
    ✓ /admin/novels       requires=novel.view
    ✓ /admin/rules       requires=rule.view
    ✓ /admin/tasks       requires=task.view
    ✓ /admin/seo         requires=seo.view
    ✓ /admin/system      requires=system.view
    ✗ /admin/cleaner     requires=cleaner.edit
    ✗ /admin/classifier  requires=classifier.edit
    ✗ /admin/sites       requires=site.manage
    ✗ /admin/themes      requires=site.manage
    ✗ /admin/downloads   requires=download.manage
    ✗ /admin/users       requires=user.manage

→ 断言:
  ✓ editor 可编辑规则、不可管理用户 — 符合预期
  ✓ operator 可运行任务、不可编辑规则 — 符合预期

=== RBAC 端到端测试通过 ===
```

### 2.2 浏览器后台验证

1. 用 `admin` 登录后台 → 「用户与权限」tab
2. 看到 4 个内置角色
3. 「用户」tab → 「新建用户」
   - 用户名：`alice_editor`
   - 密码：`Alice@2024`
   - 角色：勾选 `editor`
   - 保存
4. 退出 admin，用 `alice_editor` 登录
5. 左侧菜单应该只有：工作台、小说管理、采集规则、内容清洗、智能分类、文件下载、SEO 检测、系统设置
6. **不应看到**：站群管理、主题模板、采集任务、用户与权限
7. 「角色」tab → 新建一个角色 `Content Reviewer`，只勾选 `novel.view` 和 `seo.view`
8. 把 alice_editor 切换到这个新角色，刷新页面 → 菜单进一步缩减

### 2.3 清理测试用户

```bash
docker compose exec backend python /app/../scripts/test_rbac_e2e.py --cleanup
```

---

## 3. 验证站点 + SEO 审计

### 3.1 命令行端到端测试

```bash
docker compose exec backend python /app/../scripts/test_seo_e2e.py
```

预期输出：

```
【1/4】 创建一个 SEO 配置很差的测试站点
  ✓ 站点: seo-test-bad.example.com

【2/4】 第一次审计（修复前）
  ─── 修复前 ───
  综合评分: 25.0/100
  Summary: errors=2 warnings=5 ok=0

    [✗] site_title          error    首页标题未设置
        → 在站点设置中填写 SEO 标题
    [✗] site_description     error    首页描述未设置
        → 填写 description meta
    [!] site_keywords       warning  首页关键词未设置
        → 填写 keywords meta
    [!] canonical_domain    warning  未设置 canonical 域名
        → 填写 canonical 域名以避免重复内容惩罚
    [!] geo_region         warning  GEO 地区未设置
        → 建议设置 geo_region（如 CN / US）
    ... (more)

  ✓ 修复前评分 = 25.0 (< 60，符合"差配置"预期)

【3/4】 按建议修复 TDK / GEO / canonical / robots / sitemap
  ✓ 设置 site_title = '墨香书阁 - 免费小说在线阅读'
  ✓ 设置 site_description = 100+ 字描述
  ...

【4/4】 第二次审计（修复后）
  ─── 修复后 ───
  综合评分: 100.0/100
  Summary: errors=0 warnings=0 ok=12

→ 评分提升: 25.0 → 100.0 (+75.0点)
→ 修复后 0 errors，符合预期

【5/5】 生成 sitemap.xml + rss.xml
  ✓ sitemap: /app/media/sitemaps/seo-test-bad.example.com.xml
  ✓ rss: 长度 1234 bytes

=== SEO 端到端测试通过 ===
```

### 3.2 浏览器后台验证

1. 用 admin 登录 → 「站群管理」→ 「新建」
   - 域名：`site1.localhost`
   - 站名：`测试站 1`
   - 主题：选 simple_reading
   - SEO 标题：留空
   - SEO 描述：留空
   - canonical：留空
   - GEO：留空
   - 保存
2. 切到「SEO 检测」tab → 刷新检测
3. 该站点评分应低于 60 分，错误数 ≥ 2
4. 回「站群管理」→ 编辑该站点 → 按建议填写：
   - SEO 标题：`测试站 - 免费小说阅读`
   - SEO 描述：`测试站 1 提供玄幻、奇幻、武侠等全类型小说，免费在线阅读与下载。`
   - SEO 关键词：`小说,阅读,免费,玄幻,奇幻`
   - canonical：`site1.localhost`
   - GEO 地区：`CN`
   - GEO 语言：`zh-CN`
   - robots.txt：`User-agent: *\nAllow: /\n`
   - 启用 Sitemap：✓
   - 保存
5. 回「SEO 检测」→ 刷新检测 → 评分应 ≥ 90 分，错误数 = 0
6. 点击「重新生成 sitemap」按钮
7. 浏览器访问 `http://site1.localhost/sitemap.xml`（需 hosts 绑定）→ 看到 XML

### 3.3 测试 sitemap 自动定时刷新

```bash
# 在宿主机 crontab 中添加：
crontab -e

# 加入：
0 3 * * * cd /opt/novel-system/docker && docker compose exec -T backend \
  python manage.py refresh_sitemaps >> /var/log/novel-sitemaps.log 2>&1
```

---

## 4. 验证定时调度

### 4.1 启用 Celery Beat 容器

`docker-compose.yml` 中已包含 `beat` 容器，确保它启动：

```bash
docker compose ps beat
# Up 状态
```

### 4.2 命令行启用调度

```bash
# 创建一个测试任务（用现有规则）
# 然后用 curl 启用调度
docker compose exec backend python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')
django.setup()
from apps.crawler_tasks.models import CrawlerTask
t = CrawlerTask.objects.first()
if t:
    t.schedule_enabled = True
    t.schedule_cron = '0 3 * * *'  # 每天 3 点
    t.save()
    from apps.crawler_tasks.schedule import sync_schedule
    sync_schedule(t)
    print(f'✓ 任务 {t.id} 调度已启用: cron=0 3 * * *')
"
```

### 4.3 浏览器后台验证

1. 后台 → 「采集任务」→ 选择一个任务 → 详情页
2. 右侧出现「定时调度（Cron）」卡片
3. 启用「启用调度」开关
4. Cron 表达式：`0 3 * * *`
5. 点击「保存调度」→ 应显示「调度已启用」
6. 点击「预览下次 5 次」→ 显示未来 5 次运行时间
7. 「下次执行」字段显示在数据库中

### 4.4 验证 beat 是否调度

```bash
# 查看 beat 容器日志
docker compose logs beat --tail 50
# 应该看到类似：
# Scheduler: Sending due task crawler_task_1 (apps.crawler_tasks.tasks.run_crawler_task)

# 查看 django_celery_beat 的 PeriodicTask 表
docker compose exec backend python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
for p in PeriodicTask.objects.all():
    print(f'{p.name}: enabled={p.enabled} cron={p.crontab} args={p.args}')
"
```

---

## 5. 验证 EPUB 封面嵌入

### 5.1 前提

数据库中有至少一本书，且：
- `book.cover` 有本地上传图，或
- `book.cover_url` 有可访问的封面 URL

### 5.2 命令行触发 EPUB 生成

```bash
docker compose exec backend python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')
django.setup()
from apps.novel.models import Book
from apps.file_download.models import DownloadTemplate
from apps.file_download.engine import build_epub

book = Book.objects.first()
tpl = DownloadTemplate.objects.filter(output_format='epub').first() or DownloadTemplate.objects.first()
print(f'Generating EPUB for {book.title} (cover={book.cover or book.cover_url})')
path = build_epub(book, tpl)
print(f'✓ EPUB saved to: {path}')
print(f'  Size: {path.stat().st_size} bytes')

# 验证封面是否嵌入
import zipfile
with zipfile.ZipFile(path, 'r') as z:
    files = z.namelist()
    print(f'  Files in EPUB:')
    for f in files:
        print(f'    - {f}')
    has_cover = any('cover' in f.lower() for f in files)
    print(f'  封面已嵌入: {has_cover}')
"
```

预期输出包含 `EPUB/cover.jpg` 或 `EPUB/images/cover.webp`。

### 5.3 浏览器后台验证

1. 后台 → 文件下载 → 「生成下载记录」按钮（或选一本书点「下载 EPUB」）
2. 下载记录列表 → 下载文件
3. 用 Calibre / Apple Books 打开 → 应看到封面

---

## 6. 一键运行所有 e2e 测试

把以下存为 `scripts/run_all_e2e.sh`：

```bash
#!/bin/bash
set -e
cd /opt/novel-system/docker

echo "===================="
echo "Test 1: Crawler Engine"
echo "===================="
docker compose exec -T backend python /app/../scripts/test_engine_e2e.py --status

echo ""
echo "===================="
echo "Test 2: RBAC"
echo "===================="
docker compose exec -T backend python /app/../scripts/test_rbac_e2e.py --cleanup

echo ""
echo "===================="
echo "Test 3: SEO Audit"
echo "===================="
docker compose exec -T backend python /app/../scripts/test_seo_e2e.py --cleanup

echo ""
echo "===================="
echo "All tests passed."
echo "===================="
```

赋予执行权限并运行：

```bash
chmod +x scripts/run_all_e2e.sh
./scripts/run_all_e2e.sh
```

---

## 故障排查

| 症状 | 原因 | 解决 |
|------|------|------|
| e2e 脚本找不到模块 | 容器内 sys.path 缺少 backend | 检查脚本顶部已自动插入 `BACKEND_DIR` |
| Firecrawl/Browser Use 显示未安装 | requirements 没装全 | `docker compose build backend worker` 重建镜像 |
| RBAC 测试断言失败 | `init_default_data` 没运行 | `docker compose exec backend python manage.py init_default_data` |
| SEO 修复后评分仍低 | 字段长度不在阈值内 | 检查 `apps/seo/engine.py` 中各 check 的阈值 |
| Beat 不调度任务 | beat 容器未启动 | `docker compose up -d beat` |
| EPUB 没封面 | book.cover 与 book.cover_url 都为空 | 给 book 设置 cover_url 或上传 cover |

---

## 后续路线图

- [x] 采集任务 cron 定时调度（已实现，本文档 4 节验证）
- [x] EPUB 封面嵌入（已实现，本文档 5 节验证）
- [x] Hyperbrowser 代理池（已实现，本文档 1.4 节验证）
- [ ] Hyperbrowser 多 region 代理池切换
- [ ] 代理池自动剔除低成功率代理
- [ ] EPUB 内嵌水印图片
- [ ] 任务调度优先级（多任务并发限制）
