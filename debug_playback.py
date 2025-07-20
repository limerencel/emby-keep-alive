import aiohttp
import asyncio
import json
from datetime import datetime

async def debug_real_vs_api_playback(url, username, password):
    """
    调试真实播放和API播放的差异
    这个工具会检查当前活跃会话，然后模拟API播放，再对比差异
    """
    connector = aiohttp.TCPConnector(ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            # 登录
            login_data = {"Username": username, "Pw": password}
            login_headers = {
                "X-Emby-Authorization": 'Emby UserId="", Client="DebugTool", Device="debug-playback", DeviceId="debug-002", Version="1.0"',
                "Content-Type": "application/json"
            }
            
            async with session.post(f"{url}/Users/AuthenticateByName", json=login_data, headers=login_headers) as response:
                if response.status != 200:
                    raise Exception(f"登录失败: HTTP {response.status}")
                auth = await response.json()
            
            token = auth['AccessToken']
            user_id = auth['User']['Id']
            headers = {"X-MediaBrowser-Token": token, "Content-Type": "application/json"}
            
            print(f"\n=== 调试服务器: {url} ===")
            print(f"用户: {auth['User']['Name']} (ID: {user_id})")
            
            # 1. 检查当前活跃会话
            print("\n1. 检查当前活跃会话:")
            async with session.get(f"{url}/Sessions", headers=headers) as response:
                if response.status == 200:
                    sessions = await response.json()
                    print(f"   当前活跃会话数: {len(sessions)}")
                    for i, sess in enumerate(sessions):
                        print(f"   会话 {i+1}: {sess.get('Client', 'Unknown')} - {sess.get('DeviceName', 'Unknown')}")
                        if sess.get('NowPlayingItem'):
                            item = sess['NowPlayingItem']
                            print(f"     正在播放: {item.get('Name', 'Unknown')}")
                            print(f"     播放位置: {sess.get('PlayState', {}).get('PositionTicks', 0) // 10_000_000}秒")
                else:
                    print(f"   无法获取会话信息: HTTP {response.status}")
            
            # 2. 检查用户播放历史
            print("\n2. 检查用户播放历史:")
            try:
                # 获取最近播放的项目
                params = {
                    'Recursive': 'true',
                    'IncludeItemTypes': 'Movie',
                    'Limit': '5',
                    'SortBy': 'DatePlayed',
                    'SortOrder': 'Descending',
                    'Filters': 'IsPlayed,IsResumable'
                }
                async with session.get(f"{url}/Users/{user_id}/Items", params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get('Items', [])
                        print(f"   最近播放的电影数量: {len(items)}")
                        for item in items[:3]:  # 只显示前3个
                            user_data = item.get('UserData', {})
                            played_percentage = user_data.get('PlayedPercentage', 0)
                            position_ticks = user_data.get('PlaybackPositionTicks', 0)
                            print(f"   - {item['Name']}: {played_percentage:.1f}% ({position_ticks // 10_000_000}秒)")
                    else:
                        print(f"   无法获取播放历史: HTTP {response.status}")
            except Exception as e:
                print(f"   播放历史检查失败: {e}")
            
            # 3. 获取一个电影进行测试
            print("\n3. 选择测试电影:")
            params = {'Recursive': 'true', 'IncludeItemTypes': 'Movie', 'Limit': '1'}
            async with session.get(f"{url}/Users/{user_id}/Items", params=params, headers=headers) as response:
                if response.status != 200:
                    print("   无法获取电影列表")
                    return
                data = await response.json()
                items = data.get('Items', [])
                if not items:
                    print("   没有找到电影")
                    return
                
                movie = items[0]
                print(f"   测试电影: {movie['Name']}")
                print(f"   电影ID: {movie['Id']}")
                
                # 检查电影的当前用户数据
                user_data = movie.get('UserData', {})
                print(f"   当前播放位置: {user_data.get('PlaybackPositionTicks', 0) // 10_000_000}秒")
                print(f"   播放百分比: {user_data.get('PlayedPercentage', 0):.1f}%")
                print(f"   是否已播放: {user_data.get('Played', False)}")
            
            # 4. 模拟API播放并检查差异
            print("\n4. 开始API播放测试:")
            
            # 记录播放前的状态
            print("   播放前状态检查...")
            async with session.get(f"{url}/Users/{user_id}/Items/{movie['Id']}", headers=headers) as response:
                if response.status == 200:
                    before_data = await response.json()
                    before_user_data = before_data.get('UserData', {})
                    print(f"   播放前位置: {before_user_data.get('PlaybackPositionTicks', 0) // 10_000_000}秒")
                
            # 开始播放
            play_session_id = f"debug-{datetime.now().strftime('%H%M%S')}"
            play_data = {
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
                "SubtitleStreamIndex": -1
            }
            
            print(f"   发送播放开始请求 (会话ID: {play_session_id})...")
            async with session.post(f"{url}/Sessions/Playing", json=play_data, headers=headers) as response:
                response_text = await response.text()
                print(f"   播放开始响应: HTTP {response.status}")
                if response.status not in [200, 204]:
                    print(f"   响应内容: {response_text}")
                
            # 等待一下，然后检查会话是否出现
            await asyncio.sleep(2)
            print("   检查播放会话是否建立...")
            async with session.get(f"{url}/Sessions", headers=headers) as response:
                if response.status == 200:
                    sessions = await response.json()
                    found_session = False
                    for sess in sessions:
                        if sess.get('PlayState', {}).get('PlaySessionId') == play_session_id:
                            found_session = True
                            print(f"   ✓ 找到播放会话: {sess.get('Client', 'Unknown')}")
                            break
                    if not found_session:
                        print("   ✗ 未找到对应的播放会话")
                
            # 发送进度更新
            test_position = 300  # 5分钟
            progress_data = {
                "UserId": user_id,
                "ItemId": movie['Id'],
                "MediaSourceId": movie['Id'],
                "PositionTicks": test_position * 10_000_000,
                "PlayMethod": "DirectPlay",
                "PlaySessionId": play_session_id,
                "IsPaused": False,
                "CanSeek": True,
                "VolumeLevel": 100,
                "IsMuted": False
            }
            
            print(f"   发送进度更新 ({test_position}秒)...")
            async with session.post(f"{url}/Sessions/Playing/Progress", json=progress_data, headers=headers) as response:
                print(f"   进度更新响应: HTTP {response.status}")
                if response.status not in [200, 204]:
                    response_text = await response.text()
                    print(f"   响应内容: {response_text}")
            
            # 停止播放
            stop_data = {
                "UserId": user_id,
                "ItemId": movie['Id'],
                "MediaSourceId": movie['Id'],
                "PositionTicks": test_position * 10_000_000,
                "PlaySessionId": play_session_id,
                "PlayMethod": "DirectPlay"
            }
            
            print("   发送停止播放请求...")
            async with session.post(f"{url}/Sessions/Playing/Stopped", json=stop_data, headers=headers) as response:
                print(f"   停止播放响应: HTTP {response.status}")
                if response.status not in [200, 204]:
                    response_text = await response.text()
                    print(f"   响应内容: {response_text}")
            
            # 等待一下，然后检查播放位置是否更新
            await asyncio.sleep(2)
            print("   检查播放位置是否更新...")
            async with session.get(f"{url}/Users/{user_id}/Items/{movie['Id']}", headers=headers) as response:
                if response.status == 200:
                    after_data = await response.json()
                    after_user_data = after_data.get('UserData', {})
                    after_position = after_user_data.get('PlaybackPositionTicks', 0) // 10_000_000
                    print(f"   播放后位置: {after_position}秒")
                    
                    if after_position == test_position:
                        print("   ✓ 播放位置已正确更新")
                    else:
                        print(f"   ✗ 播放位置未更新 (期望: {test_position}秒, 实际: {after_position}秒)")
                        
                        # 尝试手动更新用户数据
                        print("   尝试手动更新用户播放数据...")
                        user_data_update = {
                            "PlaybackPositionTicks": test_position * 10_000_000,
                            "PlayedPercentage": (test_position * 100) / (movie.get('RunTimeTicks', 7200 * 10_000_000) // 10_000_000)
                        }
                        
                        async with session.post(f"{url}/Users/{user_id}/Items/{movie['Id']}/UserData", 
                                              json=user_data_update, headers=headers) as response:
                            print(f"   用户数据更新响应: HTTP {response.status}")
                            if response.status in [200, 204]:
                                print("   ✓ 用户数据手动更新成功")
                            else:
                                response_text = await response.text()
                                print(f"   用户数据更新失败: {response_text}")
                
        except Exception as e:
            print(f"调试过程出错: {e}")

async def main():
    try:
        CFG = json.load(open("./emby.json"))
        
        print("=== Emby 播放历史调试工具 ===")
        print("这个工具会帮助找出API播放和真实播放的差异\n")
        
        # 只测试第一个服务器
        server = CFG['servers'][0]
        username = CFG['usernames'][0]
        password = CFG['passwords'][0]
        
        await debug_real_vs_api_playback(server, username, password)
        
        print("\n=== 调试完成 ===")
        print("请检查以上输出，特别注意:")
        print("1. 播放会话是否正确建立")
        print("2. 进度更新是否成功")
        print("3. 播放位置是否正确保存")
        print("4. 然后在手机客户端检查'继续观看'是否出现")
        
    except Exception as e:
        print(f"调试工具错误: {e}")

if __name__ == "__main__":
    asyncio.run(main())