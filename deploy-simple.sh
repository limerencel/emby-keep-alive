#!/bin/bash

# Emby Keep-Alive 简化部署脚本
# 使用 cron job 而不是复杂的 systemd 服务

set -e

# 配置
SERVICE_USER="emby-alive"
INSTALL_DIR="/opt/emby-alive"
LOG_DIR="/var/log/emby-alive"

echo "🚀 开始部署 Emby Keep-Alive 服务（简化版）..."

# 检查是否以root权限运行
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用 sudo 运行此脚本"
    exit 1
fi

# 1. 创建服务用户
echo "📝 创建服务用户..."
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd --system --shell /bin/bash --home-dir "$INSTALL_DIR" --create-home "$SERVICE_USER"
    echo "✅ 用户 $SERVICE_USER 创建成功"
else
    echo "ℹ️  用户 $SERVICE_USER 已存在"
fi

# 2. 创建目录结构
echo "📁 创建目录结构..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$LOG_DIR"

# 3. 复制文件
echo "📋 复制应用文件..."
cp main.py "$INSTALL_DIR/"
cp emby.json "$INSTALL_DIR/"
cp pyproject.toml "$INSTALL_DIR/"
cp uv.lock "$INSTALL_DIR/"

# 4. 设置权限
echo "🔐 设置文件权限..."
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
chown -R "$SERVICE_USER:$SERVICE_USER" "$LOG_DIR"
chmod 755 "$INSTALL_DIR"
chmod 644 "$INSTALL_DIR"/*.py
chmod 600 "$INSTALL_DIR/emby.json"

# 5. 安装 uv（如果需要）
echo "🐍 检查 uv 安装..."
if ! command -v uv &> /dev/null; then
    echo "📦 安装 uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# 确保 uv 在系统路径中可用
if command -v uv &> /dev/null; then
    UV_PATH=$(which uv)
    echo "✅ 找到 uv: $UV_PATH"
    # 复制到系统目录（而不是符号链接），避免路径访问权限问题
    cp "$UV_PATH" /usr/local/bin/uv
    chmod +x /usr/local/bin/uv
    echo "✅ 创建系统级 uv 链接成功"
    
    # 测试sudo uv是否工作
    if sudo uv --version &>/dev/null; then
        echo "✅ sudo uv 测试成功"
    else
        echo "❌ sudo uv 测试失败，将使用绝对路径"
        # 如果还是不行，直接使用绝对路径
        UV_COMMAND="$UV_PATH"
    fi
else
    echo "❌ uv 安装失败"
    exit 1
fi

# 设置uv命令变量
UV_COMMAND=${UV_COMMAND:-"uv"}

# 6. 安装依赖
echo "📦 安装项目依赖..."
cd "$INSTALL_DIR"
sudo -u "$SERVICE_USER" "$UV_COMMAND" sync
echo "✅ 依赖安装完成"

# 7. 创建运行脚本
echo "📝 创建运行脚本..."
cat > "$INSTALL_DIR/run.sh" << EOF
#!/bin/bash
cd /opt/emby-alive
export PYTHONUNBUFFERED=1
$UV_COMMAND run main.py >> /var/log/emby-alive/emby-alive.log 2>&1
EOF

chmod +x "$INSTALL_DIR/run.sh"
chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/run.sh"

# 8. 设置 cron job
echo "⏰ 设置 cron job..."
# 每天22点到23点之间的随机时间执行
RANDOM_MINUTE=$((RANDOM % 60))
CRON_TIME="$RANDOM_MINUTE 22 * * *"

# 为服务用户添加 cron job
sudo -u "$SERVICE_USER" bash -c "(crontab -l 2>/dev/null || echo '') | grep -v 'emby-alive' | { cat; echo '$CRON_TIME /opt/emby-alive/run.sh'; } | crontab -"

echo "✅ Cron job 设置完成: $CRON_TIME"

# 9. 配置日志轮转
echo "📜 配置日志轮转..."
cat > /etc/logrotate.d/emby-keeper << 'EOF'
/var/log/emby-alive/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 emby-alive emby-alive
}
EOF

# 10. 清理旧的 systemd 服务（如果存在）
echo "🧹 清理旧服务..."
if systemctl is-enabled emby-keeper.timer &>/dev/null; then
    systemctl stop emby-keeper.timer
    systemctl disable emby-keeper.timer
fi
if systemctl is-enabled emby-keeper.service &>/dev/null; then
    systemctl stop emby-keeper.service
    systemctl disable emby-keeper.service
fi

# 删除旧的服务文件
rm -f /etc/systemd/system/emby-keeper.service
rm -f /etc/systemd/system/emby-keeper.timer
systemctl daemon-reload

echo ""
echo "🎉 部署完成！"
echo ""
echo "📊 Cron 任务状态:"
sudo -u "$SERVICE_USER" crontab -l | grep emby-alive
echo ""
echo "📋 常用命令:"
echo "  手动执行:         sudo -u emby-alive $INSTALL_DIR/run.sh"
echo "  查看应用日志:     tail -f $LOG_DIR/emby-alive.log"
echo "  查看 cron 日志:   grep emby-alive /var/log/syslog"
echo "  编辑 cron 任务:   sudo -u emby-alive crontab -e"
echo ""
echo "📁 文件位置:"
echo "  应用目录: $INSTALL_DIR"
echo "  日志目录: $LOG_DIR"
echo "  运行脚本: $INSTALL_DIR/run.sh"
echo ""
echo "🧪 测试运行:"
echo "  sudo -u emby-alive $INSTALL_DIR/run.sh"