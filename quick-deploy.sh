#!/bin/bash
# ============================================================
# novel-system 一键部署脚本
# 用法: curl -fsSL https://raw.githubusercontent.com/u4399com-beep/1021/main/quick-deploy.sh | bash
# 或:   wget -qO- https://raw.githubusercontent.com/u4399com-beep/1021/main/quick-deploy.sh | bash
# ============================================================
set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     novel-system 一键部署脚本 v98                         ║"
echo "║     Django + Vue + Celery + Playwright 小说管理系统        ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# ─── 1. 检查 Docker ───
echo "【1/8】检查 Docker 环境..."
if ! command -v docker &> /dev/null; then
    echo "  ⚠ Docker 未安装，正在安装..."
    curl -fsSL https://get.docker.com | bash
    systemctl enable --now docker
fi
if ! docker compose version &> /dev/null; then
    echo "  ⚠ Docker Compose v2 未找到，请安装 docker-compose-plugin"
    exit 1
fi
echo "  ✓ Docker $(docker --version)"
echo "  ✓ Docker Compose $(docker compose version --short)"

# ─── 2. 克隆项目 ───
echo ""
echo "【2/8】克隆项目..."
INSTALL_DIR="/opt/novel-system"
if [ -d "$INSTALL_DIR" ]; then
    echo "  ⚠ 目录已存在: $INSTALL_DIR，将更新代码..."
    cd "$INSTALL_DIR"
    git pull origin main || true
else
    git clone https://github.com/u4399com-beep/1021.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi
echo "  ✓ 项目已就绪: $(pwd)"

# ─── 3. 配置环境变量 ───
echo ""
echo "【3/8】配置环境变量..."
if [ ! -f .env ]; then
    cp .env.example .env
    # 生成随机密钥
    SECRET=$(openssl rand -hex 32)
    DB_PASS=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 20)
    sed -i "s/change-me-to-a-50-char-random-string/$SECRET/" .env
    sed -i "s/novel_pwd_2024/$DB_PASS/" .env
    echo "  ✓ .env 已生成（密钥已自动随机化）"
else
    echo "  ✓ .env 已存在，跳过"
fi

# ─── 4. 构建镜像 ───
echo ""
echo "【4/8】构建 Docker 镜像（首次约 10-15 分钟）..."
cd docker
docker compose build 2>&1 | tail -5
echo "  ✓ 镜像构建完成"

# ─── 5. 启动服务 ───
echo ""
echo "【5/8】启动服务..."
docker compose up -d
echo "  等待数据库就绪..."
sleep 10
# 等待 postgres 健康
for i in $(seq 1 30); do
    if docker compose exec -T postgres pg_isready -U novel 2>/dev/null; then
        echo "  ✓ PostgreSQL 就绪"
        break
    fi
    sleep 2
done

# ─── 6. 数据库迁移 + 初始化 ───
echo ""
echo "【6/8】数据库迁移 + 初始化种子数据..."
docker compose exec -T backend python manage.py migrate --noinput
docker compose exec -T backend python manage.py collectstatic --noinput
docker compose exec -T backend python manage.py init_default_data
docker compose exec -T backend python manage.py seed_cunshu_la_rules
echo "  ✓ 数据库初始化完成"

# ─── 7. 导入 cunshu.la 规则 ───
echo ""
echo "【7/8】验证服务状态..."
docker compose ps
echo ""

# ─── 8. 完成 ───
echo "【8/8】部署完成！"
echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                    部署成功！                              ║"
echo "╠═══════════════════════════════════════════════════════════╣"
echo "║  后台管理:  http://localhost/admin/                       ║"
echo "║  API 文档:  http://localhost/api/docs/                    ║"
echo "║  默认站点:  http://localhost/                            ║"
echo "║  Flower:    http://localhost:5555/flower                  ║"
echo "║  默认账号:  admin / admin123456                           ║"
echo "║                                                           ║"
echo "║  请立即修改管理员密码:                                    ║"
echo "║  docker compose exec backend python manage.py \\           ║"
echo "║    changepassword admin                                  ║"
echo "╚═══════════════════════════════════════════════════════════╝"
