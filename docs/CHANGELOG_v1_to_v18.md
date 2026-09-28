# v1-v18 迭代版本变更说明

> 本文档汇总 v1-v18 每个迭代版本的功能变化、新增 API、新增配置项和验证方法。

---

## v1: Hyperbrowser 多 region 切换

### 变更
- `crawler_engine/anti_detection/pool.py`：`get_hyperbrowser_session()` 增加 `region` 参数
- 新增 `HYPERBROWSER_REGIONS` 常量：`("auto", "us", "eu", "asia", "cn", "in", "br")`
- 缓存按 region 分组，请求 `auto` 可命中任意 region 的缓存会话

### 用法
```python
from crawler_engine.anti_detection.pool import get_hyperbrowser_session
session = get_hyperbrowser_session(region="cn")  # 优先用中国区 IP
session = get_hyperbrowser_session(region="auto")  # 自动选择
```

### 验证
```bash
docker compose exec backend python -c "
from crawler_engine.anti_detection.pool import HYPERBROWSER_REGIONS
print(HYPERBROWSER_REGIONS)
"
```

---

## v2: 代理池自动剔除低成功率代理

### 模型新增字段（ProxyPool）
- `auto_disable_enabled` (Bool, default=True)
- `min_success_rate` (Float, default=0.30)
- `min_sample_count` (Int, default=5)
- `auto_disabled_at` (DateTime)
- `auto_disabled_reason` (CharField)

### 新方法
- `ProxyPool.record_success()` — 计数 + 自动剔除判定
- `ProxyPool.record_failure()` — 同上
- `ProxyPool.reactivate()` — 重新启用已自动剔除的代理

### 新 API
- `POST /api/v1/crawler/proxy-pool/{id}/reactivate/`
- `POST /api/v1/crawler/proxy-pool/sweep_disabled/` — 立即扫一遍所有代理，剔除低于阈值的

### 使用方式
采集任务每次抓取成功/失败后调用 `record_success()/record_failure()`。当达到 `min_sample_count` 且成功率 < `min_success_rate`，代理会被自动 `is_active=False` 并标记 `auto_disabled_reason`。

---

## v3: EPUB 内嵌水印图片

### 变更
- `apps/file_download/engine.py` 新增 `_build_watermark_svg(site, book)` 生成透明 SVG 水印
- EPUB 增加 `images/watermark.svg` item + CSS overlay 类 `.watermark-layer`
- 每个章节页首部插入 `<div class="watermark-layer"><img src="images/watermark.svg" /></div>`
- 水印含 site 名 + sha256(host|book_id|slug|timestamp) 前 16 位
- EPUB metadata 同时增加 `watermark` 字段

### 用法
```python
from apps.file_download.engine import build_download, build_epub
record = build_download(book, template, site=site)
# build_epub(book, template, site=site)
```

### 验证
EPUB 文件解压后查看：
- 应包含 `EPUB/images/watermark.svg`
- 任意章节 XHTML 含 `<div class="watermark-layer">`

---

## v4: 任务调度优先级与并发限制

### 模型新增字段（CrawlerTask）
- `priority` (Int, default=50, 0-100)
- `max_concurrent_per_class` (Int, default=3)
- `exclusive` (Bool, default=False)

### 新模块
- `apps/crawler_tasks/concurrency.py`
  - `acquire_slot(task)` — 获取执行槽位
  - `release_slot(task)` — 释放
  - `get_active_count()` — 诊断
- settings 新增 `CRAWLER.MAX_CONCURRENT_TASKS = 8`

### Celery tasks 改造
`run_crawler_task` 在执行前调用 `acquire_slot()`，无槽位时延后 30 秒重试，执行结束 finally 块调用 `release_slot()`。

### 新 API
- `GET /api/v1/tasks/concurrency_status/` — 返回当前并发状态

---

## v5: 混淆效果对比工具 (diff)

### 新模块
- `apps/obfuscator/diff_tool.py`
  - `render_twice(site, html)` — 同一 HTML 渲染两次，对比字节差异
  - `render_visual_diff(site, html)` — 返回 HTML diff 表

### 新 API
- `POST /api/v1/obfuscator/preview/diff/` — 字节级 diff
- `POST /api/v1/obfuscator/preview/visual-diff/` — HTML diff 表

### 验证
启用某站点的混淆配置后：
```bash
curl -X POST http://localhost/api/v1/obfuscator/preview/diff/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"text":"<div class=\"title\">测试</div>", "site_id":1}'
# 应看到 byte_similarity < 1.0，证明每次渲染结构不同
```

---

## v6: 分卷管理后台页面

### 新模型（v6 增补）
- `apps/novel/models.Volume`
- `apps/novel/views.VolumeViewSet` API

### 新 API
- `GET/POST /api/v1/novels/volumes/` — CRUD
- `POST /api/v1/novels/volumes/{id}/assign_chapters/` — 批量分配章节
- `POST /api/v1/novels/volumes/{id}/auto_split_by_count/` — 自动均分（参数：`{count, prefix}`）
- `GET /api/v1/novels/books/{id}/disorder_check/` — 检查乱序是否破坏分卷边界

### 前端
- `frontend/src/api/obfuscator.js` 增加 `volumeApi` + `disorderCheckApi`

---

## v7: 章节内容分页采集实现

### 变更
- `crawler_engine/pipeline.py:_crawl_chapter()` 现在按 `next_page` 配置自动跟随分页
- 单章最大 20 页（安全上限）
- 多页内容用 `\n\n` 分隔拼接
- Chapter 模型字段 `source_paged` + `source_page_count` 已存
- 新增辅助函数 `_resolve_next_page(current_url, html, next_spec_dict)`

### 配置示例
```json
{
  "content": {"type": "css", "expr": "div.content"},
  "next_page": {"type": "css", "expr": "a.next::attr(href)"}
}
```

---

## v8: 站点级缓存控制

### 新模块
- `apps/sites/cache_control.py`
  - `apply_cache_headers(response, site, page_type)` — 按 Site 配置加 Cache-Control
  - `DEFAULT_CACHE_TIMES` 字典：home/category/book_detail/chapter/rss/sitemap

### 默认时长
| 类型 | 秒 |
|------|---|
| home | 60 |
| category | 300 |
| book_detail | 600 |
| chapter | 1800 |
| rss | 600 |
| sitemap | 3600 |
| static | 86400 (immutable) |

Site 可通过 `cache_<page_type>_seconds` 字段覆盖（需自行添加到 Site 模型）。

---

## v9: 关键词命中率统计

### 模型新增字段
- `CategoryKeyword.hit_count` (Int)
- `CategoryKeyword.last_hit_at` (DateTime)
- `CategoryKeyword.last_hit_book_id` (Int)
- `FinishedPattern.hit_count` (Int)
- `FinishedPattern.last_hit_at` (DateTime)

### 新方法
- `CategoryKeyword.record_hit(book_id)` — 命中时调用
- `FinishedPattern.record_hit()` — 完结判断命中时调用

### 触发点
- `apps/smart_classifier/engine.classify_book(title, intro, snippet, top_n, book_id)` — 当传入 book_id 时记录命中
- `apps/smart_classifier/engine.detect_finished()` — 命中规则时记录

---

## v10: 采集任务批量执行

### 新 API
- `POST /api/v1/tasks/batch_run/` — Body: `{task_ids: [1,2,3]}` → `{started: [...], skipped: [...]}`
- `POST /api/v1/tasks/batch_pause/` — Body: `{task_ids: [...]}` → `{paused: [...]}`
- `POST /api/v1/tasks/batch_stop/` — Body: `{task_ids: [...]}` → `{stopped: [...]}`

### 用例
当需要一次启动 50 个采集任务时，避免逐个调用 `run/` 端点造成的 N 次 HTTP 请求：
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task_ids":[1,2,3,4,5,6,7,8,9,10]}' \
  http://localhost/api/v1/tasks/batch_run/
```

---

## v11: 数据库性能优化

### Book 新增索引
```python
models.Index(fields=["slug", "is_published"]),
models.Index(fields=["-rating"]),
models.Index(fields=["-updated_at"]),
models.Index(fields=["source_site", "is_deleted"]),
models.Index(fields=["finished_at"]),
models.Index(fields=["status", "is_published", "-rating"], name="book_status_rating_idx"),
```

### 部署后迁移
```bash
docker compose exec backend python manage.py makemigrations novel
docker compose exec backend python manage.py migrate
```

---

## v12: 主题模板 SEO 检测

### 新模块
- `apps/seo/theme_seo_check.py`
  - `check_theme_files(theme_code)` — 检查主题 HTML 文件
  - `check_all_themes()` — 批量检查所有 5 套主题
  - `REQUIRED_SEO_PATTERNS` — 12 项检查（title/description/keywords/viewport/canonical/og:*/geo/schema.org）

### 新 API
- `GET /api/v1/seo/theme-check/` — 检查所有主题
- `GET /api/v1/seo/theme-check/<theme_code>/` — 检查单个主题

### 返回结构
```json
{
  "theme_code": "simple_reading",
  "files_total": 3,
  "files_present": 3,
  "issues_count": 0,
  "issues": [],
  "score": 100.0
}
```

---

## v13: EPUB 元数据完善

### 新增 EPUB DC metadata
- `DC:description` (book.intro[:500])
- `DC:contributor` (author.intro[:200])
- `DC:source` (book.source_site)
- `DC:relation` (book.source_url)
- `DC:publisher` (site.name)
- `DC:rights` ("All rights reserved by ...")
- `DC:subject` (first category name)
- `DC:date` (created_at ISO 8601)

### 验证
用 `unzip -p book.epub EPUB/content.opf | grep -i "dc:"` 查看元数据。

---

## v14: RSS 输出集成混淆

### 变更
- `apps/seo/rss.py:render_site_rss(site, books, obfuscate=False)` 新增 `obfuscate` 参数
- `render_book_chapter_rss(site, book, obfuscate=False)` 同上

### 用法
当站点已启用 ObfuscationProfile 且希望 RSS 内容也获得同等的混淆处理：
```python
xml = render_site_rss(site, books, obfuscate=True)
```
所有 `<title>`、`<description>`、`<category>` 文本会经过 `apply_text_only()` 处理。

---

## v15: 采集任务历史执行统计

### 新模块
- `apps/crawler_tasks/stats.py`
  - `overall_stats()` — 总任务数 / 状态分布 / 今日完成 / 今日失败
  - `runs_per_day(days=30)` — 过去 N 天每日执行统计
  - `top_active_tasks(limit=10)` — 最活跃的 N 个任务
  - `recent_log_summary(task_id, hours, limit)` — 日志聚合

### 新 API
- `GET /api/v1/tasks/stats/?days=30` — 全局统计
- `GET /api/v1/tasks/recent_logs/?hours=24&task_id=1&limit=50` — 日志聚合

---

## v16: 验证码识别集成 (2captcha / OCR)

### 新模块
- `crawler_engine/captcha_solver.py`
  - `solve_with_2captcha(image_bytes, timeout)` — 提交到 2captcha，轮询结果
  - `solve_with_ocr(image_bytes)` — 本地 Tesseract OCR
  - `solve_captcha(image_bytes, prefer)` — 主入口，自动 fallback
  - `diagnostics()` — 配置状态

### settings 配置
```python
CRAWLER = {
    ...
    "CAPTCHA_2CAPTCHA_KEY": os.environ.get("CAPTCHA_2CAPTCHA_KEY", ""),
    "CAPTCHA_2CAPTCHA_ENDPOINT": os.environ.get("CAPTCHA_2CAPTCHA_ENDPOINT", "https://2captcha.com/in.php"),
}
```

### 新 API
- `GET /api/v1/crawler/captcha/status/` — 配置状态
- `POST /api/v1/crawler/captcha/solve/` — Body: `{image: "base64...", prefer: "2captcha"|"ocr"}` → `{solved, text, backend_used}`

### 系统依赖
Tesseract 需要：
```bash
apt install tesseract-ocr tesseract-ocr-chi-sim
```

### .env 新增
```env
CAPTCHA_2CAPTCHA_KEY=
CAPTCHA_2CAPTCHA_ENDPOINT=https://2captcha.com/in.php
```

---

## v17: 综合端到端测试脚本

### 新文件
- `scripts/test_v1_to_v16.py` — 一次跑完 v1-v16 共 35+ 项断言

### 运行
```bash
docker compose exec backend python /app/../scripts/test_v1_to_v16.py
```

预期输出：
```
✓ v1-v16 综合端到端测试全部通过
```

---

## v18: 部署文档（本文档）

本文档汇总 v1-v17 全部变化，运维人员升级时可对照本表。

---

## 全局新增端点一览

| 端点 | 用途 | 引入版本 |
|------|------|---------|
| `POST /api/v1/crawler/proxy-pool/{id}/reactivate/` | 重启自动剔除的代理 | v2 |
| `POST /api/v1/crawler/proxy-pool/sweep_disabled/` | 批量剔除 | v2 |
| `GET /api/v1/tasks/concurrency_status/` | 当前并发状态 | v4 |
| `POST /api/v1/obfuscator/preview/diff/` | 混淆效果对比 | v5 |
| `POST /api/v1/obfuscator/preview/visual-diff/` | 可视化 diff | v5 |
| `POST /api/v1/novels/volumes/{id}/assign_chapters/` | 批量分配章节到分卷 | v6 |
| `POST /api/v1/novels/volumes/{id}/auto_split_by_count/` | 自动均分 | v6 |
| `GET /api/v1/novels/books/{id}/disorder_check/` | 乱序检查 | v6 |
| `POST /api/v1/tasks/batch_run/` | 批量启动 | v10 |
| `POST /api/v1/tasks/batch_pause/` | 批量暂停 | v10 |
| `POST /api/v1/tasks/batch_stop/` | 批量停止 | v10 |
| `GET /api/v1/seo/theme-check/` | 主题 SEO 检测 | v12 |
| `GET /api/v1/seo/theme-check/<code>/` | 单主题检测 | v12 |
| `GET /api/v1/tasks/stats/` | 任务统计 | v15 |
| `GET /api/v1/tasks/recent_logs/` | 日志聚合 | v15 |
| `GET /api/v1/crawler/captcha/status/` | 验证码配置 | v16 |
| `POST /api/v1/crawler/captcha/solve/` | 验证码识别 | v16 |

---

## 新增 .env 配置

```env
# v4: 并发限制（默认 8）
MAX_CONCURRENT_TASKS=8

# v16: 验证码识别
CAPTCHA_2CAPTCHA_KEY=
CAPTCHA_2CAPTCHA_ENDPOINT=https://2captcha.com/in.php
```

---

## 新增 Python 依赖

```text
# v16: Captcha OCR
pytesseract==0.3.13   # 需要系统 tesseract-ocr
```

系统依赖：
```bash
apt install tesseract-ocr tesseract-ocr-chi-sim
```

---

## 新增 Django settings

```python
CRAWLER = {
    ...
    "MAX_CONCURRENT_TASKS": 8,
    "CAPTCHA_2CAPTCHA_KEY": os.environ.get("CAPTCHA_2CAPTCHA_KEY", ""),
    "CAPTCHA_2CAPTCHA_ENDPOINT": os.environ.get("CAPTCHA_2CAPTCHA_ENDPOINT", "https://2captcha.com/in.php"),
}
```

---

## 新增管理命令

无新增管理命令。所有 v1-v17 改动均通过 API 触发。

---

## 升级流程

```bash
# 1. 拉取新代码
cd /opt/novel-system && git pull

# 2. 重建镜像
cd docker && docker compose build

# 3. 重启服务
docker compose up -d

# 4. 跑数据库迁移（v11 增加了索引）
docker compose exec backend python manage.py makemigrations novel crawler smart_classifier crawler_tasks
docker compose exec backend python manage.py migrate

# 5. 跑综合测试验证
docker compose exec backend python /app/../scripts/test_v1_to_v16.py

# 6. 浏览器验证
# - 后台 → 混淆与伪原创 → 预览测试 → 看每次渲染结构不同
# - 后台 → SEO 检测 → 主题 SEO 检测
# - 后台 → 采集任务 → 详情 → 看到定时调度卡片
```

---

## 后续待办（下一轮迭代）

剩余路线图：
- [ ] Hyperbrowser 多 region 自动选择（按站点地理位置智能路由）
- [ ] 代理池 24 小时窗口自动剔除（按时间段聚合成功率）
- [ ] EPUB 加密保护（DRM 试水）
- [ ] 任务调度优先级抢占式（高优先级可踢掉低优先级）
- [ ] 验证码自动识别集成到 Playwright tier（自动 WAF bypass）
- [ ] 主题模板插件系统（用户可上传自定义主题）
- [ ] 数据库读写分离（PostgreSQL replica）
- [ ] 全文搜索（PostgreSQL pg_trgm 已配置，可加搜索 API）
