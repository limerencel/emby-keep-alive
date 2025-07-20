#!/bin/bash

# Emby Keep-Alive Scheduler
# 在指定时间范围内随机选择一个时间运行保活程序

# 配置
SCRIPT_DIR="/opt/emby-keeper"
PYTHON_SCRIPT="$SCRIPT_DIR/main.py"
PYTHON_ENV="$SCRIPT_DIR/.venv/bin/python"
LOG_DIR="/var/log/emby-keeper"
LOG_FILE="$LOG_DIR/scheduler.log"

# 确保日志目录存在
mkdir -p "$LOG_DIR"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 检查是否已经有实例在运行
if pgrep -f "emby.*main.py" > /dev/null; then
    log "INFO: Emby keeper is already running, skipping this execution"
    exit 0
fi

# 时间范围配置 (24小时制)
START_HOUR=${START_HOUR:-22}  # 默认22点
END_HOUR=${END_HOUR:-23}      # 默认23点

# 计算当前时间
CURRENT_HOUR=$(date +%H)
CURRENT_MINUTE=$(date +%M)

# 检查是否在执行时间窗口内
if [ "$CURRENT_HOUR" -ge "$START_HOUR" ] && [ "$CURRENT_HOUR" -le "$END_HOUR" ]; then
    # 在时间窗口内，计算随机延迟
    if [ "$CURRENT_HOUR" -eq "$END_HOUR" ]; then
        # 如果是最后一小时，只能延迟到整点
        MAX_DELAY_MINUTES=$((60 - CURRENT_MINUTE))
    else
        # 否则可以延迟到下一小时
        MAX_DELAY_MINUTES=$((120 - CURRENT_MINUTE))
    fi
    
    # 生成随机延迟 (0到MAX_DELAY_MINUTES分钟)
    if [ "$MAX_DELAY_MINUTES" -gt 0 ]; then
        DELAY_MINUTES=$((RANDOM % MAX_DELAY_MINUTES))
        log "INFO: Scheduling execution in $DELAY_MINUTES minutes"
        sleep $((DELAY_MINUTES * 60))
    fi
    
    # 执行保活程序
    log "INFO: Starting Emby keep-alive process"
    
    # 切换到脚本目录
    cd "$SCRIPT_DIR" || {
        log "ERROR: Cannot change to script directory: $SCRIPT_DIR"
        exit 1
    }
    
    # 运行Python脚本，重定向输出到日志
    if [ -f "$PYTHON_ENV" ]; then
        "$PYTHON_ENV" "$PYTHON_SCRIPT" >> "$LOG_DIR/emby-keeper.log" 2>&1
        EXIT_CODE=$?
    else
        python3 "$PYTHON_SCRIPT" >> "$LOG_DIR/emby-keeper.log" 2>&1
        EXIT_CODE=$?
    fi
    
    if [ $EXIT_CODE -eq 0 ]; then
        log "INFO: Emby keep-alive completed successfully"
    else
        log "ERROR: Emby keep-alive failed with exit code: $EXIT_CODE"
    fi
    
else
    log "INFO: Current time ($CURRENT_HOUR:$CURRENT_MINUTE) is outside execution window ($START_HOUR:00-$END_HOUR:59)"
fi