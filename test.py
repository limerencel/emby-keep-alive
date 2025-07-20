import aiohttp
import asyncio
import random
import json
from datetime import datetime

async def async_keep_alive(url, username, password):
    connector = aiohttp.TCPConnector(ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            # 登录
            login_data = {"Username": username, "Pw": password}
            login_headers = {
                "X-Emby-Authorization": 'Emby UserId="", Client="Python", Device="async-keep-alive", DeviceId="async-001", Version="0.1"',
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
            
            # 修复：开始播放 - 添加必要的字段
            play_data = {
                "UserId": user_id,  # 添加用户ID
                "ItemId": movie['Id'],
                "MediaSourceId": movie['Id'],  # 添加媒体源ID
                "PlayMethod": "DirectPlay",
                "PositionTicks": 0,
                "CanSeek": True,  # 布尔值在某些版本中是必需的
                "PlaySessionId": f"play-{random.randint(1000, 9999)}"  # 添加播放会话ID
            }
            
            # 调试：打印请求数据
            print(f"{datetime.now():%F %T} [{url}] 播放请求数据: {json.dumps(play_data, indent=2)}")
            
            async with session.post(f"{url}/Sessions/Playing", json=play_data, headers=headers) as response:
                response_text = await response.text()
                if response.status not in [200, 204]:
                    print(f"{datetime.now():%F %T} [{url}] 播放请求失败: HTTP {response.status}, 响应: {response_text}")
                    # 尝试不同的端点
                    async with session.post(f"{url}/Users/{user_id}/PlayingItems/{movie['Id']}", 
                                          json={"PositionTicks": 0}, headers=headers) as alt_response:
                        if alt_response.status in [200, 204]:
                            print(f"{datetime.now():%F %T} [{url}] 使用备用端点播放成功")
                        else:
                            print(f"{datetime.now():%F %T} [{url}] 备用端点也失败: HTTP {alt_response.status}")
                else:
                    print(f"{datetime.now():%F %T} [{url}] 播放开始成功")
            
            # 观看进度模拟
            watch_duration = random.randint(300, min(1800, runtime_seconds))
            print(f"{datetime.now():%F %T} [{url}] 开始观看 {watch_duration}秒...")
            
            elapsed = 0
            update_interval = 60
            session_id = play_data.get("PlaySessionId")
            
            while elapsed < watch_duration:
                await asyncio.sleep(min(update_interval, watch_duration - elapsed))
                elapsed += min(update_interval, watch_duration - elapsed)
                position_ticks = elapsed * 10_000_000
                
                # 修复：进度更新 - 完整的数据结构
                progress_data = {
                    "UserId": user_id,
                    "ItemId": movie['Id'],
                    "MediaSourceId": movie['Id'],
                    "PositionTicks": position_ticks,
                    "PlayMethod": "DirectPlay",
                    "IsPaused": False,  # 明确指定播放状态
                    "CanSeek": True,
                    "PlaySessionId": session_id,
                    "VolumeLevel": 100,  # 音量级别
                    "IsMuted": False    # 是否静音
                }
                
                try:
                    # 尝试多个可能的端点
                    endpoints_to_try = [
                        f"/Sessions/Playing/Progress",
                        f"/Users/{user_id}/PlayingItems/{movie['Id']}/Progress",
                        f"/Sessions/Playing/Ping"  # 有些服务器只需要ping
                    ]
                    
                    progress_updated = False
                    for endpoint in endpoints_to_try:
                        if progress_updated:
                            break
                            
                        try:
                            async with session.post(f"{url}{endpoint}", json=progress_data, headers=headers) as response:
                                if response.status in [200, 204]:
                                    print(f"{datetime.now():%F %T} [{url}] 进度: {elapsed//60}:{elapsed%60:02d} (使用端点: {endpoint})")
                                    progress_updated = True
                                    break
                                else:
                                    response_text = await response.text()
                                    print(f"{datetime.now():%F %T} [{url}] 端点 {endpoint} 失败: HTTP {response.status}, 响应: {response_text[:200]}")
                        except Exception as e:
                            print(f"{datetime.now():%F %T} [{url}] 端点 {endpoint} 异常: {e}")
                    
                    if not progress_updated:
                        # 尝试简化的数据结构
                        simple_data = {"ItemId": movie['Id'], "PositionTicks": position_ticks}
                        async with session.post(f"{url}/Sessions/Playing/Progress", json=simple_data, headers=headers) as response:
                            if response.status in [200, 204]:
                                print(f"{datetime.now():%F %T} [{url}] 进度: {elapsed//60}:{elapsed%60:02d} (简化数据)")
                            else:
                                print(f"{datetime.now():%F %T} [{url}] 所有进度更新方法都失败")
                
                except Exception as e:
                    print(f"{datetime.now():%F %T} [{url}] 进度更新异常: {e}")
            
            # 停止播放
            stop_data = {
                "UserId": user_id,
                "ItemId": movie['Id'],
                "MediaSourceId": movie['Id'],
                "PositionTicks": watch_duration * 10_000_000,
                "PlaySessionId": session_id
            }
            
            async with session.post(f"{url}/Sessions/Playing/Stopped", json=stop_data, headers=headers) as response:
                if response.status in [200, 204]:
                    print(f"{datetime.now():%F %T} [{url}] 播放完成")
                else:
                    response_text = await response.text()
                    print(f"{datetime.now():%F %T} [{url}] 停止播放警告: HTTP {response.status}, 响应: {response_text}")
            
        except Exception as e:
            print(f"{datetime.now():%F %T} [{url}] 错误: {e}")
            raise e

# 添加调试功能的版本
async def debug_emby_api(url, username, password):
    """调试 Emby API 响应的函数"""
    connector = aiohttp.TCPConnector(ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            # 登录
            login_data = {"Username": username, "Pw": password}
            login_headers = {
                "X-Emby-Authorization": 'Emby UserId="", Client="Python", Device="debug", DeviceId="debug-001", Version="0.1"',
                "Content-Type": "application/json"
            }
            
            async with session.post(f"{url}/Users/AuthenticateByName", json=login_data, headers=login_headers) as response:
                auth = await response.json()
            
            token = auth['AccessToken']
            user_id = auth['User']['Id']
            headers = {"X-MediaBrowser-Token": token, "Content-Type": "application/json"}
            
            print(f"调试 {url}:")
            print(f"  用户ID: {user_id}")
            print(f"  Token: {token[:20]}...")
            
            # 检查 Sessions 端点
            try:
                async with session.get(f"{url}/Sessions", headers=headers) as response:
                    if response.status == 200:
                        sessions = await response.json()
                        print(f"  当前会话数: {len(sessions)}")
                    else:
                        print(f"  Sessions 端点不可用: HTTP {response.status}")
            except Exception as e:
                print(f"  Sessions 检查失败: {e}")
            
            # 检查服务器信息
            try:
                async with session.get(f"{url}/System/Info", headers=headers) as response:
                    if response.status == 200:
                        info = await response.json()
                        print(f"  服务器版本: {info.get('Version', 'Unknown')}")
                        print(f"  服务器名称: {info.get('ServerName', 'Unknown')}")
                    else:
                        print(f"  系统信息不可用: HTTP {response.status}")
            except Exception as e:
                print(f"  系统信息检查失败: {e}")
                
        except Exception as e:
            print(f"调试 {url} 失败: {e}")

async def main():
    try:
        CFG = json.load(open("./emby.json"))
        
        # 先运行调试
        print("=== 调试信息 ===")
        for server, username, password in zip(CFG['servers'], CFG['usernames'], CFG['passwords']):
            await debug_emby_api(server, username, password)
        
        print("\n=== 开始播放模拟 ===")
        print(f"{datetime.now():%F %T} 准备同时在 {len(CFG['servers'])} 个服务器上开始播放...")
        
        tasks = []
        for i, (server, username, password) in enumerate(zip(CFG['servers'], CFG['usernames'], CFG['passwords']), 1):
            print(f"{datetime.now():%F %T} 创建任务 {i}: {server}")
            task = async_keep_alive(server, username, password)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = 0
        for i, result in enumerate(results, 1):
            if isinstance(result, Exception):
                print(f"{datetime.now():%F %T} 服务器 {i} 失败: {result}")
            else:
                print(f"{datetime.now():%F %T} 服务器 {i} 成功完成")
                success_count += 1
        
        print(f"{datetime.now():%F %T} 完成！成功: {success_count}/{len(results)}")
        
    except FileNotFoundError:
        print("错误: 找不到 emby.json 文件")
    except json.JSONDecodeError:
        print("错误: emby.json 格式不正确")
    except Exception as e:
        print(f"程序错误: {e}")

if __name__ == "__main__":
    asyncio.run(main())