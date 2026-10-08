#!/bin/bash
# ============================================================
# novel-system 一键升级脚本
# 用法: curl -fsSL https://raw.githubusercontent.com/u4399com-beep/1021/main/quick-upgrade.sh | bash
# ============================================================
set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     novel-system 一键升级脚本 v322                        ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

INSTALL_DIR="/opt/novel-system"

# ─── 1. 检查安装目录 ───
echo "【1/6】检查安装目录..."
if [ ! -d "$INSTALL_DIR" ]; then
    echo "  ✗ 未找到 $INSTALL_DIR，请先运行一键部署:"
    echo "    curl -fsSL https://raw.githubusercontent.com/u4399com-beep/1021/main/quick-deploy.sh | bash"
    exit 1
fi
echo "  ✓ 安装目录: $INSTALL_DIR"

# ─── 2. 拉取最新代码 ───
echo ""
echo "【2/6】拉取最新代码..."
cd "$INSTALL_DIR"
git fetch origin main
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)
if [ "$LOCAL" = "$REMOTE" ]; then
    echo "  ✓ 已是最新版本 ($LOCAL)"
    echo "  如需强制更新，请运行: git pull origin main --force"
    # 继续执行后续步骤确保一致
else
    git pull origin main
    echo "  ✓ 代码已更新: $LOCAL → $REMOTE"
fi

# ─── 3. 重建 Docker 镜像 ───
echo ""
echo "【3/6】重建 Docker 镜像..."
cd docker
docker compose build --no-cache backend worker 2>&1 | tail -5
echo "  ✓ 镜像重建完成"

# ─── 4. 重启服务 ───
echo ""
echo "【4/6】重启服务..."
docker compose up -d --force-recreate backend worker beat flower
echo "  等待数据库就绪..."
sleep 10
for i in $(seq 1 30); do
    if docker compose exec -T postgres pg_isready -U novel 2>/dev/null; then
        echo "  ✓ PostgreSQL 就绪"
        break
    fi
    sleep 2
done

# ─── 5. 数据库迁移 + 更新 ───
echo ""
echo "【5/6】数据库迁移 + 更新种子数据..."
docker compose exec -T backend python manage.py makemigrations --noinput
docker compose exec -T backend python manage.py migrate --noinput
docker compose exec -T backend python manage.py collectstatic --noinput
docker compose exec -T backend python manage.py init_default_data
docker compose exec -T backend python manage.py seed_cunshu_la_rules
echo "  ✓ 数据库迁移完成"

# ─── 6. 验证服务 ───
echo ""
echo "【6/6】验证服务状态..."
docker compose ps
echo ""

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                    升级成功！                              ║"
echo "╠═══════════════════════════════════════════════════════════╣"
echo "║  后台管理:  http://localhost/admin/                       ║"
echo "║  API 文档:  http://localhost/api/docs/                    ║"
echo "║  三层架构状态: http://localhost/api/v1/crawler/          ║"
echo "║              three-tier/status/                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "新增功能 (v319-v322):"
echo "  ✓ HTTP + iv8 + CloakBrowser 三层架构"
echo "  ✓ 6 层浏览器指纹隐藏 (WebGL/Canvas/Audio/Navigator/Screen/Font)"
echo "  ✓ iv8 住宅 IP 代理池"
echo "  ✓ 章节并发抓取提速"
echo "  ✓ yckceo/Legado 书源转换器"
echo "  ✓ 封面图重新获取功能"
echo ""
echo "配置说明:"
echo "  三层架构: CRAWLER_THREE_TIER_ENABLED=true (默认启用)"
echo "  iv8 代理: IV8_API_KEY=your-key (.env 中配置)"
echo "  CloakBrowser: 自动启用 (无需配置)"
