import aiohttp
import asyncio
import random
import json
from datetime import datetime

async def create_proper_playback_session(url, username, password):
    """
    创建真正的播放会话，确保历史记录正确生成
    """
    connector = aiohttp.TCPConnector(ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            # 登录
            login_data = {"Username": username, "Pw": password}
            login_headers = {
                "X-Emby-Authorization": 'Emby UserId="", Client="EmbyClient", Device="Windows", DeviceId="fixed-playback-001", Version="4.8.0"',
                "Content-Type": "application/json"
            }
            
            async with session.post(f"{url}/Users/AuthenticateByName", json=login_data, headers=login_headers) as response:
                if response.status != 200:
                    raise Exception(f"登录失败: HTTP {response.status}")
                auth = await response.json()
            
            token = auth['AccessToken']
            user_id = auth['User']['Id']
            headers = {"X-MediaBrowser-Token": token, "Content-Type": "application/json"}
            
            print(f"{datetime.now():%F %T} [{url}] 登录成功，用户: {auth['User']['Name']}")
            
            # 获取电影列表
            params = {'Recursive': 'true', 'IncludeItemTypes': 'Movie', 'Limit': '50'}
            async with session.get(f"{url}/Users/{user_id}/Items", params=params, headers=headers) as response:
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
            
            # 步骤1: 首先标记为"正在播放" - 这是关键步骤
            play_session_id = f"fixed-{random.randint(100000, 999999)}"
            
            # 重要：先发送播放开始事件，使用更完整的数据
            start_play_data = {
                "UserId": user_id,
                "ItemId": movie['Id'],
                "MediaSourceId": movie['Id'],
                "PlayMethod": "DirectPlay",
                "PositionTicks": 0,
                "PlaySessionId": play_session_id,
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
            
            print(f"{datetime.now():%F %T} [{url}] 建立播放会话: {play_session_id}")
            async with session.post(f"{url}/Sessions/Playing", json=start_play_data, headers=headers) as response:
                if response.status not in [200, 204]:
                    response_text = await response.text()
                    print(f"{datetime.now():%F %T} [{url}] 播放开始警告: HTTP {response.status}, 响应: {response_text}")
                else:
                    print(f"{datetime.now():%F %T} [{url}] 播放会话建立成功")
            
            # 步骤2: 立即发送一个进度ping来确认会话
            await asyncio.sleep(1)
            ping_data = {
                "UserId": user_id,
                "ItemId": movie['Id'],
                "MediaSourceId": movie['Id'],
                "PositionTicks": 0,
                "PlayMethod": "DirectPlay",
                "PlaySessionId": play_session_id,
                "IsPaused": False,
                "CanSeek": True,
                "VolumeLevel": 100,
                "IsMuted": False
            }
            
            async with session.post(f"{url}/Sessions/Playing/Progress", json=ping_data, headers=headers) as response:
                if response.status in [200, 204]:
                    print(f"{datetime.now():%F %T} [{url}] 会话确认成功")
                else:
                    print(f"{datetime.now():%F %T} [{url}] 会话确认失败: HTTP {response.status}")
            
            # 步骤3: 模拟观看过程 - 缩短测试时间
            watch_duration = 120  # 固定2分钟测试
            print(f"{datetime.now():%F %T} [{url}] 开始观看 {watch_duration}秒...")
            
            elapsed = 0
            update_interval = 30  # 更频繁的更新
            
            while elapsed < watch_duration:
                await asyncio.sleep(min(update_interval, watch_duration - elapsed))
                elapsed += min(update_interval, watch_duration - elapsed)
                
                position_ticks = elapsed * 10_000_000
                
                # 发送详细的进度更新
                progress_data = {
                    "UserId": user_id,
                    "ItemId": movie['Id'],
                    "MediaSourceId": movie['Id'],
                    "PositionTicks": position_ticks,
                    "PlayMethod": "DirectPlay",
                    "PlaySessionId": play_session_id,
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
                    async with session.post(f"{url}/Sessions/Playing/Progress", json=progress_data, headers=headers) as response:
                        if response.status in [200, 204]:
                            print(f"{datetime.now():%F %T} [{url}] 进度: {elapsed//60}:{elapsed%60:02d}")
                        else:
                            response_text = await response.text()
                            print(f"{datetime.now():%F %T} [{url}] 进度更新失败: HTTP {response.status}, 响应: {response_text}")
                except Exception as e:
                    print(f"{datetime.now():%F %T} [{url}] 进度更新异常: {e}")
            
            # 步骤4: 正确结束播放会话
            final_position_ticks = watch_duration * 10_000_000
            
            # 发送最终进度更新
            final_progress_data = {
                "UserId": user_id,
                "ItemId": movie['Id'],
                "MediaSourceId": movie['Id'],
                "PositionTicks": final_position_ticks,
                "PlayMethod": "DirectPlay",
                "PlaySessionId": play_session_id,
                "IsPaused": False,
                "CanSeek": True,
                "VolumeLevel": 100,
                "IsMuted": False,
                "AudioStreamIndex": 0,
                "SubtitleStreamIndex": -1,
                "PlaybackRate": 1.0
            }
            
            async with session.post(f"{url}/Sessions/Playing/Progress", json=final_progress_data, headers=headers) as response:
                if response.status in [200, 204]:
                    print(f"{datetime.now():%F %T} [{url}] 最终进度更新成功")
            
            # 发送停止播放
            stop_data = {
                "UserId": user_id,
                "ItemId": movie['Id'],
                "MediaSourceId": movie['Id'],
                "PositionTicks": final_position_ticks,
                "PlaySessionId": play_session_id,
                "PlayMethod": "DirectPlay",
                "Failed": False,  # 明确指定播放没有失败
                "NextMediaType": "Video"  # 添加媒体类型
            }
            
            async with session.post(f"{url}/Sessions/Playing/Stopped", json=stop_data, headers=headers) as response:
                if response.status in [200, 204]:
                    print(f"{datetime.now():%F %T} [{url}] 播放正常结束")
                else:
                    response_text = await response.text()
                    print(f"{datetime.now():%F %T} [{url}] 停止播放警告: HTTP {response.status}, 响应: {response_text}")
            
            # 步骤5: 确保用户数据正确更新 - 这是关键步骤
            await asyncio.sleep(1)
            
            # 方法1: 更新用户播放数据
            user_data_payload = {
                "PlaybackPositionTicks": final_position_ticks,
                "PlayedPercentage": (watch_duration * 100.0) / runtime_seconds,
                "Played": False,  # 部分观看，不是完全播放
                "Key": "PlaybackPositionTicks",
                "Value": str(final_position_ticks)
            }
            
            try:
                async with session.post(f"{url}/Users/{user_id}/Items/{movie['Id']}/UserData", 
                                      json=user_data_payload, headers=headers) as response:
                    if response.status in [200, 204]:
                        print(f"{datetime.now():%F %T} [{url}] 用户数据更新成功")
                    else:
                        response_text = await response.text()
                        print(f"{datetime.now():%F %T} [{url}] 用户数据更新失败: HTTP {response.status}, 响应: {response_text}")
            except Exception as e:
                print(f"{datetime.now():%F %T} [{url}] 用户数据更新异常: {e}")
            
            # 方法2: 尝试直接标记为已播放项目
            try:
                played_item_data = {
                    "Id": movie['Id'],
                    "UserId": user_id,
                    "PositionTicks": final_position_ticks,
                    "DatePlayed": datetime.now().isoformat() + "Z"
                }
                
                async with session.post(f"{url}/Users/{user_id}/PlayedItems/{movie['Id']}", 
                                      json=played_item_data, headers=headers) as response:
                    if response.status in [200, 204]:
                        print(f"{datetime.now():%F %T} [{url}] 播放项目记录成功")
                    else:
                        # 这个API可能不存在，不用担心
                        pass
            except Exception as e:
                # 这个是额外尝试，失败了也没关系
                pass
            
            print(f"{datetime.now():%F %T} [{url}] 播放会话完成，请检查客户端的'继续观看'")
            
        except Exception as e:
            print(f"{datetime.now():%F %T} [{url}] 错误: {e}")
            raise e

async def main():
    try:
        CFG = json.load(open("./emby.json"))
        
        print(f"{datetime.now():%F %T} 开始修复版播放测试...")
        
        # 只测试第一个服务器
        server = CFG['servers'][0]
        username = CFG['usernames'][0]
        password = CFG['passwords'][0]
        
        await create_proper_playback_session(server, username, password)
        
        print(f"{datetime.now():%F %T} 测试完成！")
        print("请现在检查手机客户端的'继续观看'部分")
        
    except Exception as e:
        print(f"程序错误: {e}")

if __name__ == "__main__":
    asyncio.run(main())