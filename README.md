# Emby Keep-Alive

一个用于保持 Emby 服务器活跃状态的自动化工具，通过模拟真实的观看行为来维持服务器连接和生成播放历史记录。

## ✨ 功能特性

- 🎬 **真实播放模拟** - 模拟完整的观看会话，包括播放开始、进度更新和正常结束
- 🔄 **多服务器支持** - 同时在多个 Emby 服务器上并发执行保活任务
- 📱 **跨平台同步** - 生成的播放历史在桌面和移动客户端都可见
- ⏰ **智能调度** - 支持 cron 定时执行，每天随机时间运行
- 🛡️ **优雅退出** - Ctrl+C 时自动保存当前播放进度
- 📊 **完善日志** - 多层次日志记录，便于监控和调试
- 🔐 **安全配置** - 支持自签名证书，专用用户权限管理

## 🚀 快速开始

### 本地运行

1. **克隆项目**
   ```bash
   git clone https://github.com/limerencel/emby-keep-alive.git
   cd emby-keep-alive
   ```

2. **安装依赖**
   ```bash
   # 使用 uv 安装依赖（推荐）
   uv sync
   
   # 或者使用传统方式
   pip install aiohttp
   ```

3. **配置服务器信息**
   ```bash
   cp emby.copy.json emby.json
   # 编辑 emby.json 填入你的服务器信息
   ```

4. **运行程序**
   ```bash
   # 使用 uv 运行（推荐）
   uv run main.py
   
   # 或者使用传统方式
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
- uv 包管理器
- 网络连接到 Emby 服务器

### 一键部署

1. **安装 uv**（如果未安装）
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **上传文件到服务器**
   ```bash
   git clone https://github.com/limerencel/emby-keep-alive.git
   cd emby-keep-alive
   ```

3. **执行部署脚本**
   ```bash
   chmod +x deploy-simple.sh
   sudo ./deploy-simple.sh
   ```

4. **验证部署**
   ```bash
   # 查看 cron 任务
   sudo -u emby-alive crontab -l
   
   # 手动测试运行
   sudo -u emby-alive /opt/emby-alive/run.sh
   
   # 查看日志
   tail -f /var/log/emby-alive/emby-alive.log
   ```

### 部署后的文件结构

```
/opt/emby-alive/
├── main.py                    # 主程序
├── emby.json                  # 服务器配置
├── run.sh                     # 运行脚本
├── pyproject.toml            # uv 项目配置
├── uv.lock                   # uv 锁定文件
└── .venv/                    # Python虚拟环境

/var/log/emby-alive/
└── emby-alive.log            # 应用程序日志

/etc/logrotate.d/
└── emby-keeper               # 日志轮转配置
```

## ⏰ 调度配置

### 默认调度策略

- **执行时间**: 每天 22:00-22:59 之间的随机分钟执行
- **调度方式**: 使用 cron job 定时执行
- **用户权限**: 以 `emby-alive` 用户身份运行

### 查看和修改 cron 任务

```bash
# 查看当前 cron 任务
sudo -u emby-alive crontab -l

# 编辑 cron 任务（修改执行时间）
sudo -u emby-alive crontab -e

# 示例：改为每天 20:30 执行
# 30 20 * * * /opt/emby-alive/run.sh
```

## 📊 日志管理

### 日志文件说明

| 日志文件 | 内容 | 用途 |
|---------|------|------|
| `emby-alive.log` | 应用程序输出 | 查看播放会话详情 |

### 常用日志命令

```bash
# 实时查看应用日志
tail -f /var/log/emby-alive/emby-alive.log

# 查看最近的日志
tail -100 /var/log/emby-alive/emby-alive.log

# 查看 cron 执行记录
grep emby-alive /var/log/syslog
```

### 日志轮转

- **轮转周期**: 每日轮转
- **保留时间**: 30天
- **压缩**: 自动压缩旧日志
- **权限**: 自动设置正确的文件权限

## 🔧 服务管理

### 基本命令

```bash
# 手动执行一次
sudo -u emby-alive /opt/emby-alive/run.sh

# 查看 cron 任务状态
sudo -u emby-alive crontab -l

# 编辑 cron 任务
sudo -u emby-alive crontab -e

# 清理日志文件
sudo truncate -s 0 /var/log/emby-alive/emby-alive.log
```

### 配置修改

```bash
# 修改Emby服务器配置
sudo nano /opt/emby-alive/emby.json

# 测试配置是否正确
sudo -u emby-alive /opt/emby-alive/run.sh
```

## 🛡️ 安全特性

### 系统安全

- **专用用户**: 使用 `emby-alive` 用户运行，避免权限过高
- **目录隔离**: 限制文件系统访问权限  
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

3. **uv 命令不存在**
   ```
   uv 命令不存在
   ```
   **解决方案**: 
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

4. **权限问题**
   ```
   Permission denied
   ```
   **解决方案**: 确保以 root 权限运行部署脚本
   ```bash
   sudo ./deploy-simple.sh
   ```

5. **播放历史不显示**
   - 确保观看时间超过30秒
   - 检查Emby服务器版本兼容性
   - 查看应用日志确认API调用成功

### 调试模式

如需调试，可以手动运行程序：

```bash
cd /opt/emby-alive
sudo -u emby-alive uv run main.py
```

## 📝 更新日志

### v1.1.0
- ✅ 简化部署流程，使用 cron job 替代复杂的 systemd 服务
- ✅ 优化 uv 依赖管理
- ✅ 简化日志管理
- ✅ 更加稳定和易于维护

### v1.0.0
- ✅ 基础播放会话模拟功能
- ✅ 多服务器并发支持
- ✅ 优雅退出和进度保存
- ✅ 完整的服务器部署方案
- ✅ 随机时间调度
- ✅ 完善的日志管理系统

## 📄 许可证

本项目基于 MIT 许可证开源。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**注意**: 请确保合规使用，仅用于个人学习和测试目的。