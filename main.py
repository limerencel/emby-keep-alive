import aiohttp
import asyncio
import random
import json
import signal
import sys
from datetime import datetime

# 全局变量用于存储活跃的播放会话
active_sessions = []

# 优雅退出处理函数
async def graceful_shutdown():
    """在程序退出前保存所有活跃会话的进度"""
    if not active_sessions:
        return
    
    print(f"\n{datetime.now():%F %T} 检测到中断信号，正在保存播放进度...")
    
    # 并发保存所有会话的进度
    save_tasks = []
    for session_info in active_sessions:
        task = save_session_progress(session_info)
        save_tasks.append(task)
    
    if save_tasks:
        await asyncio.gather(*save_tasks, return_exceptions=True)
        print(f"{datetime.now():%F %T} 播放进度已保存，程序退出")

async def save_session_progress(session_info):
    """保存单个会话的播放进度"""
    try:
        url = session_info['url']
        headers = session_info['headers']
        user_id = session_info['user_id']
        movie = session_info['movie']
        play_session_id = session_info['play_session_id']
        current_position = session_info['current_position']
        
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            # 步骤1: 发送暂停信号（模拟用户暂停）
            pause_progress_data = {
                "UserId": user_id,
                "ItemId": movie['Id'],
                "MediaSourceId": movie['Id'],
                "PositionTicks": current_position * 10_000_000,
                "PlayMethod": "DirectStream",  # 改为DirectStream，更接近真实客户端
                "PlaySessionId": play_session_id,
                "IsPaused": True,  # 标记为暂停状态
                "CanSeek": True,
                "VolumeLevel": 100,
                "IsMuted": False,
                "AudioStreamIndex": 0,
                "SubtitleStreamIndex": -1,
                "PlaybackRate": 1.0,
                "MaxStreamingBitrate": 140000000
            }
            
            async with session.post(f"{url}/Sessions/Playing/Progress", json=pause_progress_data, headers=headers) as response:
                if response.status in [200, 204]:
                    print(f"{datetime.now():%F %T} [{url}] 播放已暂停: {current_position//60}:{current_position%60:02d}")
            
            # 步骤2: 等待一下，然后发送停止播放
            await asyncio.sleep(0.5)
            
            stop_data = {
                "UserId": user_id,
                "ItemId": movie['Id'],
                "MediaSourceId": movie['Id'],
                "PositionTicks": current_position * 10_000_000,
                "PlaySessionId": play_session_id,
                "PlayMethod": "DirectStream",  # 保持一致
                "Failed": False,  # 明确指定没有失败
                "NextMediaType": "Video"
            }
            
            async with session.post(f"{url}/Sessions/Playing/Stopped", json=stop_data, headers=headers) as response:
                if response.status in [200, 204]:
                    print(f"{datetime.now():%F %T} [{url}] 播放会话已正常结束")
            
            # 步骤3: 更新用户播放位置（使用正确的API）
            await asyncio.sleep(0.5)
            
            user_data_update = {
                "PlaybackPositionTicks": current_position * 10_000_000,
                "PlayedPercentage": min(100.0, (current_position * 100.0) / (movie.get('RunTimeTicks', 7200 * 10_000_000) // 10_000_000))
            }
            
            async with session.post(f"{url}/Users/{user_id}/Items/{movie['Id']}/UserData", 
                                  json=user_data_update, headers=headers) as response:
                if response.status in [200, 204]:
                    print(f"{datetime.now():%F %T} [{url}] 用户播放位置已更新")
                    
    except Exception as e:
        print(f"{datetime.now():%F %T} 保存进度时出错: {e}")

# 异步版本 - 修复布尔值类型问题
async def async_keep_alive(url, username, password):
    # 设置连接器，禁用SSL验证（某些自建服务器可能需要）
    connector = aiohttp.TCPConnector(ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            # 异步登录
            login_data = {
                "Username": username, 
                "Pw": password
            }
            
            login_headers = {
                "X-Emby-Authorization": 'Emby UserId="", Client="EmbyClient", Device="Windows", DeviceId="async-keep-alive", Version="4.8.0"',
                "Content-Type": "application/json"
            }
            
            async with session.post(
                f"{url}/Users/AuthenticateByName",
                json=login_data,
                headers=login_headers
            ) as response:
                if response.status != 200:
                    raise Exception(f"登录失败: HTTP {response.status}")
                auth = await response.json()
            
            token = auth['AccessToken']
            user_id = auth['User']['Id']
            
            headers = {
                "X-MediaBrowser-Token": token,
                "Content-Type": "application/json"
            }
            
            print(f"{datetime.now():%F %T} [{url}] 登录成功，用户: {auth['User']['Name']}")
            
            # 异步获取电影列表
            params = {
                'Recursive': 'true',  # 字符串而不是布尔值
                'IncludeItemTypes': 'Movie',
                'Limit': '50'  # 字符串而不是数字
            }
            
            async with session.get(
                f"{url}/Users/{user_id}/Items",
                params=params,
                headers=headers
            ) as response:
                if response.status != 200:
                    raise Exception(f"获取电影列表失败: HTTP {response.status}")
                data = await response.json()
                items = data.get('Items', [])
            
            if not items:
                print(f"{datetime.now():%F %T} [{url}] 没有找到电影")
                return
            
            movie = random.choice(items)
            runtime_ticks = movie.get('RunTimeTicks', 7200 * 10_000_000)
            runtime_seconds = runtime_ticks // 10_000_000
            
            print(f"{datetime.now():%F %T} [{url}] 选中: {movie['Name']} (时长: {runtime_seconds//60}分钟)")
            
            # 生成播放会话ID
            play_session_id = f"play-{random.randint(100000, 999999)}"
            
            # 将会话信息添加到全局列表，用于中断时保存进度
            session_info = {
                'url': url,
                'headers': headers,
                'user_id': user_id,
                'movie': movie,
                'play_session_id': play_session_id,
                'current_position': 0
            }
            active_sessions.append(session_info)
            
            # 异步开始播放 - 添加必要字段确保历史记录
            play_data = {
                "UserId": user_id,  # 关键：用户ID
                "ItemId": movie['Id'],
                "MediaSourceId": movie['Id'],  # 关键：媒体源ID
                "PlayMethod": "DirectPlay",
                "PositionTicks": 0,
                "PlaySessionId": play_session_id,  # 关键：播放会话ID
                "CanSeek": True,
                "IsPaused": False,
                "VolumeLevel": 100,
                "IsMuted": False,
                "AudioStreamIndex": 0,
                "SubtitleStreamIndex": -1,
                "PlaybackStartTimeTicks": datetime.now().timestamp() * 10_000_000,  # 添加开始时间
                "MaxStreamingBitrate": 140000000,  # 添加流媒体比特率
                "PlaybackOrder": "Default"  # 添加播放顺序
            }
            
            async with session.post(
                f"{url}/Sessions/Playing", 
                json=play_data,
                headers=headers
            ) as response:
                if response.status not in [200, 204]:
                    response_text = await response.text()
                    print(f"{datetime.now():%F %T} [{url}] 播放请求警告: HTTP {response.status}, 响应: {response_text}")
                else:
                    print(f"{datetime.now():%F %T} [{url}] 播放会话已建立: {play_session_id}")
            
            # 异步等待并发送进度更新
            watch_duration = random.randint(300, min(1800, runtime_seconds))
            print(f"{datetime.now():%F %T} [{url}] 开始观看 {watch_duration}秒...")
            
            elapsed = 0
            update_interval = 60  # 每60秒更新一次
            
            # 记录开始时间，用于计算实际播放时间
            start_time = datetime.now().timestamp()
            session_info['start_time'] = start_time
            
            while elapsed < watch_duration and not shutdown_requested:
                sleep_time = min(update_interval, watch_duration - elapsed)
                
                # 分段睡眠，每秒检查一次中断信号
                for _ in range(int(sleep_time)):
                    if shutdown_requested:
                        break
                    await asyncio.sleep(1)
                    # 实时更新当前位置
                    current_time = datetime.now().timestamp()
                    session_info['current_position'] = int(current_time - start_time)
                
                if shutdown_requested:
                    break
                    
                elapsed += sleep_time
                position_ticks = elapsed * 10_000_000
                
                # 更新会话的当前位置
                session_info['current_position'] = elapsed
                
                # 异步发送进度更新 - 完整数据确保历史记录
                progress_data = {
                    "UserId": user_id,  # 关键：用户ID
                    "ItemId": movie['Id'],
                    "MediaSourceId": movie['Id'],  # 关键：媒体源ID
                    "PositionTicks": position_ticks,
                    "PlayMethod": "DirectPlay",
                    "PlaySessionId": play_session_id,  # 关键：会话ID
                    "IsPaused": False,
                    "CanSeek": True,
                    "VolumeLevel": 100,
                    "IsMuted": False,
                    "AudioStreamIndex": 0,
                    "SubtitleStreamIndex": -1,
                    "PlaybackRate": 1.0,  # 播放速率
                    "MaxStreamingBitrate": 140000000
                }
                
                try:
                    async with session.post(
                        f"{url}/Sessions/Playing/Progress",
                        json=progress_data,
                        headers=headers
                    ) as response:
                        if response.status in [200, 204]:
                            print(f"{datetime.now():%F %T} [{url}] 进度: {elapsed//60}:{elapsed%60:02d}")
                        else:
                            response_text = await response.text()
                            print(f"{datetime.now():%F %T} [{url}] 进度更新失败: HTTP {response.status}, 响应: {response_text}")
                except Exception as e:
                    print(f"{datetime.now():%F %T} [{url}] 进度更新异常: {e}")
            
            # 异步停止播放 - 完整数据确保历史记录保存
            stop_data = {
                "UserId": user_id,  # 关键：用户ID
                "ItemId": movie['Id'],
                "MediaSourceId": movie['Id'],  # 关键：媒体源ID
                "PositionTicks": watch_duration * 10_000_000,
                "PlaySessionId": play_session_id,  # 关键：会话ID
                "PlayMethod": "DirectPlay"
            }
            
            async with session.post(
                f"{url}/Sessions/Playing/Stopped",
                json=stop_data,
                headers=headers
            ) as response:
                if response.status in [200, 204]:
                    print(f"{datetime.now():%F %T} [{url}] 播放完成，历史记录已保存")
                else:
                    response_text = await response.text()
                    print(f"{datetime.now():%F %T} [{url}] 停止播放警告: HTTP {response.status}, 响应: {response_text}")
            
            # 额外：确保播放状态被正确记录
            try:
                # 有些Emby版本需要额外的用户播放数据更新
                user_data_update = {
                    "ItemId": movie['Id'],
                    "UserId": user_id,
                    "PositionTicks": watch_duration * 10_000_000,
                    "PlaybackPositionTicks": watch_duration * 10_000_000
                }
                
                async with session.post(
                    f"{url}/Users/{user_id}/PlayedItems/{movie['Id']}",
                    json=user_data_update,
                    headers=headers
                ) as response:
                    if response.status in [200, 204]:
                        print(f"{datetime.now():%F %T} [{url}] 用户播放数据已更新")
                    # 如果失败也不要紧，主要的历史记录应该已经通过上面的API保存了
            except Exception as e:
                # 这个是额外的尝试，失败了也没关系
                pass
            
        except Exception as e:
            print(f"{datetime.now():%F %T} [{url}] 错误: {e}")
            raise e

# 全局变量用于控制程序退出
shutdown_requested = False

# 信号处理函数
def signal_handler(signum, frame):
    """处理 Ctrl+C 信号"""
    global shutdown_requested
    print(f"\n{datetime.now():%F %T} 接收到中断信号 (Ctrl+C)...")
    shutdown_requested = True

# 异步主函数
async def main():
    try:
        # 设置信号处理
        signal.signal(signal.SIGINT, signal_handler)
        print(f"{datetime.now():%F %T} 信号处理已设置 (按 Ctrl+C 可优雅退出)")
        
        CFG = json.load(open("./emby.json"))
        
        print(f"{datetime.now():%F %T} 准备同时在 {len(CFG['servers'])} 个服务器上开始播放...")
        
        # 并发处理所有服务器
        tasks = []
        for i, (server, username, password) in enumerate(zip(CFG['servers'], CFG['usernames'], CFG['passwords']), 1):
            print(f"{datetime.now():%F %T} 创建任务 {i}: {server}")
            task = async_keep_alive(server, username, password)
            tasks.append(task)
        
        print(f"{datetime.now():%F %T} 开始并发执行所有任务...")
        
        try:
            # 同时执行所有任务，捕获异常
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 如果收到中断信号，保存进度
            if shutdown_requested:
                await graceful_shutdown()
                return
            
            # 显示结果
            success_count = 0
            for i, result in enumerate(results, 1):
                if isinstance(result, Exception):
                    print(f"{datetime.now():%F %T} 服务器 {i} 失败: {result}")
                else:
                    print(f"{datetime.now():%F %T} 服务器 {i} 成功完成")
                    success_count += 1
            
            print(f"{datetime.now():%F %T} 完成！成功: {success_count}/{len(results)}")
            
        except asyncio.CancelledError:
            print(f"{datetime.now():%F %T} 任务被取消，正在清理...")
            await graceful_shutdown()
        except KeyboardInterrupt:
            print(f"{datetime.now():%F %T} 键盘中断，正在清理...")
            await graceful_shutdown()
        
    except FileNotFoundError:
        print("错误: 找不到 emby.json 文件")
    except json.JSONDecodeError:
        print("错误: emby.json 格式不正确")
    except Exception as e:
        print(f"程序错误: {e}")

# 运行异步程序
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{datetime.now():%F %T} 程序已退出")
    except Exception as e:
        print(f"程序异常退出: {e}")