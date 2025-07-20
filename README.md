# Emby Keep-Alive

一个用于保持 Emby 服务器活跃状态的自动化工具，通过模拟真实的观看行为来维持服务器连接和生成播放历史记录。

## ✨ 功能特性

- 🎬 **真实播放模拟** - 模拟完整的观看会话，包括播放开始、进度更新和正常结束
- 🔄 **多服务器支持** - 同时在多个 Emby 服务器上并发执行保活任务
- 📱 **跨平台同步** - 生成的播放历史在桌面和移动客户端都可见
- ⏰ **智能调度** - 支持随机时间执行，避免固定模式被检测
- 🛡️ **优雅退出** - Ctrl+C 时自动保存当前播放进度
- 📊 **完善日志** - 多层次日志记录，便于监控和调试
- 🔐 **安全配置** - 支持自签名证书，专用用户权限管理

## 🚀 快速开始

### 本地运行

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd emby-alive
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置服务器信息**
   ```bash
   cp emby.copy.json emby.json
   # 编辑 emby.json 填入你的服务器信息
   ```

4. **运行程序**
   ```bash
   python main.py
   ```

### 配置文件格式

`emby.json` 配置文件示例：
```json
{
    "servers": [
        "https://emby.example1.com:8096/",
        "https://emby.example2.com/",
        "http://192.168.1.100:8096/"
    ],
    "usernames": ["user1", "user2", "user3"],
    "passwords": ["pass1", "pass2", "pass3"]
}
```

## 🖥️ 服务器部署

### 系统要求

- Linux 服务器 (Ubuntu/CentOS/Debian)
- Python 3.8+
- systemd 支持
- 网络连接到 Emby 服务器

### 一键部署

1. **上传文件到服务器**
   ```bash
   scp main.py emby.json deploy.sh emby-keeper-scheduler.sh \
       emby-keeper.service emby-keeper.timer emby-keeper-logrotate \
       user@your-server:/tmp/
   ```

2. **执行部署脚本**
   ```bash
   cd /tmp
   chmod +x deploy.sh emby-keeper-scheduler.sh
   sudo ./deploy.sh
   ```

3. **验证部署**
   ```bash
   systemctl status emby-keeper.timer
   systemctl list-timers emby-keeper.timer
   ```

### 部署后的文件结构

```
/opt/emby-alive/
├── main.py                    # 主程序
├── emby.json                  # 服务器配置
├── emby-keeper-scheduler.sh   # 调度脚本
└── .venv/                     # Python虚拟环境

/var/log/emby-alive/
├── emby-alive.log            # 应用程序日志
├── scheduler.log             # 调度器日志
├── service.log               # systemd服务日志
└── service-error.log         # systemd错误日志

/etc/systemd/system/
├── emby-keeper.service       # systemd服务
└── emby-keeper.timer         # systemd定时器

/etc/logrotate.d/
└── emby-keeper-logrotate     # 日志轮转配置
```

## ⏰ 调度配置

### 默认调度策略

- **执行时间**: 每天 22:00-23:00 之间随机时间
- **随机延迟**: 最多1小时的随机延迟
- **防重复**: 自动检测并避免重复执行

### 自定义时间窗口

可以通过环境变量调整执行时间窗口：

```bash
# 修改为 20:00-22:00 执行
sudo systemctl edit emby-keeper.service
```

添加以下内容：
```ini
[Service]
Environment=START_HOUR=20
Environment=END_HOUR=22
```

## 📊 日志管理

### 日志文件说明

| 日志文件 | 内容 | 用途 |
|---------|------|------|
| `emby-alive.log` | 应用程序输出 | 查看播放会话详情 |
| `scheduler.log` | 调度器状态 | 监控执行时间和状态 |
| `service.log` | systemd服务日志 | 系统级别的服务状态 |
| `service-error.log` | systemd错误日志 | 系统级别的错误信息 |

### 常用日志命令

```bash
# 实时查看应用日志
tail -f /var/log/emby-alive/emby-alive.log

# 实时查看调度日志
tail -f /var/log/emby-alive/scheduler.log

# 查看系统服务日志
journalctl -u emby-keeper.service -f

# 查看最近的执行记录
journalctl -u emby-keeper.service --since "1 day ago"
```

### 日志轮转

- **轮转周期**: 每日轮转
- **保留时间**: 30天
- **压缩**: 自动压缩旧日志
- **权限**: 自动设置正确的文件权限

## 🔧 服务管理

### 基本命令

```bash
# 查看服务状态
systemctl status emby-keeper.timer

# 查看下次执行时间
systemctl list-timers emby-keeper.timer

# 手动执行一次
systemctl start emby-keeper.service

# 停止定时任务
systemctl stop emby-keeper.timer

# 重启定时任务
systemctl restart emby-keeper.timer

# 禁用服务
systemctl disable emby-keeper.timer
```

### 配置修改

```bash
# 修改Emby服务器配置
sudo nano /opt/emby-alive/emby.json

# 修改服务配置后重载
sudo systemctl daemon-reload
sudo systemctl restart emby-keeper.timer
```

## 🛡️ 安全特性

### 系统安全

- **专用用户**: 使用 `emby-alive` 用户运行，避免权限过高
- **目录隔离**: 限制文件系统访问权限
- **资源限制**: 限制内存使用和CPU占用
- **网络安全**: 支持自签名SSL证书

### 配置文件安全

- **权限控制**: `emby.json` 设置为 600 权限，仅所有者可读写
- **敏感信息**: 密码等敏感信息不会出现在日志中
- **备份建议**: 定期备份配置文件到安全位置

## 🔍 故障排除

### 常见问题

1. **SSL证书错误**
   ```
   [SSL: CERTIFICATE_VERIFY_FAILED]
   ```
   **解决方案**: 程序已自动禁用SSL验证，支持自签名证书

2. **登录失败**
   ```
   登录失败: HTTP 401
   ```
   **解决方案**: 检查 `emby.json` 中的用户名和密码是否正确

3. **服务无法启动**
   ```
   Failed to start emby-keeper.service
   ```
   **解决方案**: 检查文件权限和Python环境
   ```bash
   sudo journalctl -u emby-keeper.service -n 50
   ```

4. **播放历史不显示**
   - 确保观看时间超过30秒
   - 检查Emby服务器版本兼容性
   - 查看应用日志确认API调用成功

### 调试模式

如需调试，可以手动运行程序：

```bash
cd /opt/emby-alive
sudo -u emby-alive python3 main.py
```

## 📝 更新日志

### v1.0.0
- ✅ 基础播放会话模拟功能
- ✅ 多服务器并发支持
- ✅ 优雅退出和进度保存
- ✅ 完整的服务器部署方案
- ✅ 随机时间调度
- ✅ 完善的日志管理系统
