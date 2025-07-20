#!/bin/bash

# Emby Keep-Alive 服务部署脚本
# 使用方法: sudo ./deploy.sh

set -e

# 配置
SERVICE_USER="emby-keeper"
SERVICE_GROUP="emby-keeper"
INSTALL_DIR="/opt/emby-keeper"
LOG_DIR="/var/log/emby-keeper"

echo "🚀 开始部署 Emby Keep-Alive 服务..."

# 检查是否以root权限运行
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用 sudo 运行此脚本"
    exit 1
fi

# 1. 创建服务用户
echo "📝 创建服务用户..."
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd --system --shell /bin/false --home-dir "$INSTALL_DIR" --create-home "$SERVICE_USER"
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
cp emby-keeper-scheduler.sh "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/emby-keeper-scheduler.sh"

# 4. 设置权限
echo "🔐 设置文件权限..."
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$LOG_DIR"
chmod 755 "$INSTALL_DIR"
chmod 644 "$INSTALL_DIR"/*.py
chmod 600 "$INSTALL_DIR/emby.json"  # 保护配置文件

# 5. 安装Python依赖
echo "🐍 安装Python依赖..."
if command -v python3-venv &> /dev/null; then
    sudo -u "$SERVICE_USER" python3 -m venv "$INSTALL_DIR/.venv"
    sudo -u "$SERVICE_USER" "$INSTALL_DIR/.venv/bin/pip" install aiohttp
    echo "✅ Python虚拟环境创建成功"
else
    echo "⚠️  python3-venv 未安装，将使用系统Python"
    pip3 install aiohttp
fi

# 6. 安装systemd服务
echo "⚙️  安装systemd服务..."
cp emby-keeper.service /etc/systemd/system/
cp emby-keeper.timer /etc/systemd/system/
systemctl daemon-reload

# 7. 配置日志轮转
echo "📜 配置日志轮转..."
cp emby-keeper-logrotate /etc/logrotate.d/emby-keeper

# 8. 启用并启动服务
echo "🔄 启用服务..."
systemctl enable emby-keeper.timer
systemctl start emby-keeper.timer

# 9. 显示状态
echo ""
echo "🎉 部署完成！"
echo ""
echo "📊 服务状态:"
systemctl status emby-keeper.timer --no-pager -l
echo ""
echo "📅 下次执行时间:"
systemctl list-timers emby-keeper.timer --no-pager
echo ""
echo "📋 常用命令:"
echo "  查看服务状态: systemctl status emby-keeper.timer"
echo "  查看日志:     journalctl -u emby-keeper.service -f"
echo "  查看应用日志: tail -f $LOG_DIR/emby-keeper.log"
echo "  手动执行:     systemctl start emby-keeper.service"
echo "  停止服务:     systemctl stop emby-keeper.timer"
echo ""
echo "📁 文件位置:"
echo "  应用目录: $INSTALL_DIR"
echo "  日志目录: $LOG_DIR"
echo "  配置文件: $INSTALL_DIR/emby.json"