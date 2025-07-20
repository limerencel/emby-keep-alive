import aiohttp
import asyncio
import json
from datetime import datetime

async def analyze_real_client_behavior(url, username, password):
    """
    分析真实客户端的行为模式
    这个工具会检查真实播放会话的详细信息
    """
    connector = aiohttp.TCPConnector(ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            # 登录
            login_data = {"Username": username, "Pw": password}
            login_headers = {
                "X-Emby-Authorization": 'Emby UserId="", Client="AnalysisTool", Device="debug-analysis", DeviceId="analysis-001", Version="1.0"',
                "Content-Type": "application/json"
            }
            
            async with session.post(f"{url}/Users/AuthenticateByName", json=login_data, headers=login_headers) as response:
                if response.status != 200:
                    raise Exception(f"登录失败: HTTP {response.status}")
                auth = await response.json()
            
            token = auth['AccessToken']
            user_id = auth['User']['Id']
            headers = {"X-MediaBrowser-Token": token, "Content-Type": "application/json"}
            
            print(f"\n=== 分析服务器: {url} ===")
            print(f"用户: {auth['User']['Name']} (ID: {user_id})")
            
            # 1. 检查当前活跃会话的详细信息
            print("\n1. 当前活跃会话详细分析:")
            async with session.get(f"{url}/Sessions", headers=headers) as response:
                if response.status == 200:
                    sessions = await response.json()
                    print(f"   活跃会话数: {len(sessions)}")
                    
                    for i, sess in enumerate(sessions):
                        print(f"\n   会话 {i+1}:")
                        print(f"     客户端: {sess.get('Client', 'Unknown')}")
                        print(f"     设备: {sess.get('DeviceName', 'Unknown')}")
                        print(f"     用户ID: {sess.get('UserId', 'Unknown')}")
                        print(f"     会话ID: {sess.get('Id', 'Unknown')}")
                        
                        # 检查播放状态
                        play_state = sess.get('PlayState', {})
                        if play_state:
                            print(f"     播放状态:")
                            print(f"       位置: {play_state.get('PositionTicks', 0) // 10_000_000}秒")
                            print(f"       是否暂停: {play_state.get('IsPaused', 'Unknown')}")
                            print(f"       播放会话ID: {play_state.get('PlaySessionId', 'Unknown')}")
                            print(f"       播放方法: {play_state.get('PlayMethod', 'Unknown')}")
                            print(f"       音量: {play_state.get('VolumeLevel', 'Unknown')}")
                            print(f"       静音: {play_state.get('IsMuted', 'Unknown')}")
                        
                        # 检查正在播放的项目
                        now_playing = sess.get('NowPlayingItem')
                        if now_playing:
                            print(f"     正在播放:")
                            print(f"       名称: {now_playing.get('Name', 'Unknown')}")
                            print(f"       ID: {now_playing.get('Id', 'Unknown')}")
                            print(f"       类型: {now_playing.get('Type', 'Unknown')}")
                            print(f"       媒体源ID: {now_playing.get('MediaSources', [{}])[0].get('Id', 'Unknown') if now_playing.get('MediaSources') else 'Unknown'}")
                
            # 2. 检查用户播放历史的详细信息
            print("\n2. 用户播放历史详细分析:")
            try:
                # 获取最近播放的项目
                params = {
                    'Recursive': 'true',
                    'IncludeItemTypes': 'Movie',
                    'Limit': '3',
                    'SortBy': 'DatePlayed',
                    'SortOrder': 'Descending',
                    'Filters': 'IsPlayed,IsResumable'
                }
                async with session.get(f"{url}/Users/{user_id}/Items", params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get('Items', [])
                        print(f"   最近播放的电影数量: {len(items)}")
                        
                        for item in items:
                            user_data = item.get('UserData', {})
                            print(f"\n   电影: {item['Name']}")
                            print(f"     ID: {item['Id']}")
                            print(f"     播放位置: {user_data.get('PlaybackPositionTicks', 0) // 10_000_000}秒")
                            print(f"     播放百分比: {user_data.get('PlayedPercentage', 0):.1f}%")
                            print(f"     是否已播放: {user_data.get('Played', False)}")
                            print(f"     播放次数: {user_data.get('PlayCount', 0)}")
                            print(f"     最后播放时间: {user_data.get('LastPlayedDate', 'Unknown')}")
                            print(f"     是否收藏: {user_data.get('IsFavorite', False)}")
                            
                            # 检查更多用户数据字段
                            print(f"     用户数据键: {list(user_data.keys())}")
                    else:
                        print(f"   无法获取播放历史: HTTP {response.status}")
            except Exception as e:
                print(f"   播放历史检查失败: {e}")
            
            # 3. 检查用户活动日志
            print("\n3. 用户活动日志分析:")
            try:
                # 尝试获取用户活动
                async with session.get(f"{url}/System/ActivityLog/Entries", params={'Limit': '10'}, headers=headers) as response:
                    if response.status == 200:
                        activities = await response.json()
                        entries = activities.get('Items', [])
                        print(f"   最近活动数量: {len(entries)}")
                        
                        for entry in entries[:5]:  # 只显示前5个
                            if 'playback' in entry.get('Name', '').lower() or 'play' in entry.get('Name', '').lower():
                                print(f"   - {entry.get('Date', 'Unknown')}: {entry.get('Name', 'Unknown')}")
                                print(f"     详情: {entry.get('ShortOverview', 'Unknown')}")
                    else:
                        print(f"   无法获取活动日志: HTTP {response.status}")
            except Exception as e:
                print(f"   活动日志检查失败: {e}")
            
            # 4. 检查服务器配置和功能
            print("\n4. 服务器配置分析:")
            try:
                async with session.get(f"{url}/System/Configuration", headers=headers) as response:
                    if response.status == 200:
                        config = await response.json()
                        print(f"   服务器名称: {config.get('ServerName', 'Unknown')}")
                        print(f"   启用播放历史: {config.get('EnablePlaybackHistory', 'Unknown')}")
                        print(f"   启用用户活动日志: {config.get('EnableActivityLogging', 'Unknown')}")
                    else:
                        print(f"   无法获取服务器配置: HTTP {response.status}")
            except Exception as e:
                print(f"   服务器配置检查失败: {e}")
                
        except Exception as e:
            print(f"分析过程出错: {e}")

async def test_enhanced_api_playback(url, username, password):
    """
    测试增强的API播放，尝试更完整的播放流程
    """
    connector = aiohttp.TCPConnector(ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            # 登录
            login_data = {"Username": username, "Pw": password}
            login_headers = {
                "X-Emby-Authorization": 'Emby UserId="", Client="EmbyClient", Device="Windows", DeviceId="enhanced-test", Version="4.8.0"',
                "Content-Type": "application/json"
            }
            
            async with session.post(f"{url}/Users/AuthenticateByName", json=login_data, headers=login_headers) as response:
                if response.status != 200:
                    raise Exception(f"登录失败: HTTP {response.status}")
                auth = await response.json()
            
            token = auth['AccessToken']
            user_id = auth['User']['Id']
            headers = {"X-MediaBrowser-Token": token, "Content-Type": "application/json"}
            
            print(f"\n=== 增强API播放测试: {url} ===")
            
            # 获取一个电影
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
            
            # 步骤1: 创建播放会话 - 使用更完整的数据
            play_session_id = f"enhanced-{datetime.now().strftime('%H%M%S')}"
            
            # 更完整的播放开始数据
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
                "SubtitleStreamIndex": -1,
                "PlaybackStartTimeTicks": datetime.now().timestamp() * 10_000_000,
                "MaxStreamingBitrate": 140000000,
                "PlaybackOrder": "Default",
                # 添加更多字段
                "RepeatMode": "RepeatNone",
                "PlaybackRate": 1.0,
                "LiveStreamId": None,
                "PlaylistItemId": None
            }
            
            print(f"   创建播放会话: {play_session_id}")
            async with session.post(f"{url}/Sessions/Playing", json=play_data, headers=headers) as response:
                print(f"   播放开始响应: HTTP {response.status}")
                if response.status not in [200, 204]:
                    response_text = await response.text()
                    print(f"   响应内容: {response_text}")
            
            # 步骤2: 短暂播放
            await asyncio.sleep(5)  # 播放5秒
            
            # 步骤3: 发送进度更新
            progress_data = {
                "UserId": user_id,
                "ItemId": movie['Id'],
                "MediaSourceId": movie['Id'],
                "PositionTicks": 5 * 10_000_000,  # 5秒
                "PlayMethod": "DirectPlay",
                "PlaySessionId": play_session_id,
                "IsPaused": False,
                "CanSeek": True,
                "VolumeLevel": 100,
                "IsMuted": False,
                "AudioStreamIndex": 0,
                "SubtitleStreamIndex": -1,
                "PlaybackRate": 1.0,
                "MaxStreamingBitrate": 140000000,
                "RepeatMode": "RepeatNone"
            }
            
            print("   发送进度更新...")
            async with session.post(f"{url}/Sessions/Playing/Progress", json=progress_data, headers=headers) as response:
                print(f"   进度更新响应: HTTP {response.status}")
            
            # 步骤4: 模拟用户手动停止播放（而不是程序结束）
            # 这可能是关键差异！
            
            # 4a: 先暂停
            pause_data = progress_data.copy()
            pause_data["IsPaused"] = True
            
            print("   发送暂停信号...")
            async with session.post(f"{url}/Sessions/Playing/Progress", json=pause_data, headers=headers) as response:
                print(f"   暂停响应: HTTP {response.status}")
            
            await asyncio.sleep(1)
            
            # 4b: 然后停止播放
            stop_data = {
                "UserId": user_id,
                "ItemId": movie['Id'],
                "MediaSourceId": movie['Id'],
                "PositionTicks": 5 * 10_000_000,
                "PlaySessionId": play_session_id,
                "PlayMethod": "DirectPlay",
                "Failed": False,  # 明确指定没有失败
                "NextMediaType": "Video"
            }
            
            print("   发送停止播放...")
            async with session.post(f"{url}/Sessions/Playing/Stopped", json=stop_data, headers=headers) as response:
                print(f"   停止播放响应: HTTP {response.status}")
                if response.status not in [200, 204]:
                    response_text = await response.text()
                    print(f"   响应内容: {response_text}")
            
            # 步骤5: 额外的用户数据更新尝试
            await asyncio.sleep(1)
            
            # 5a: 更新播放位置
            print("   更新用户播放位置...")
            position_update = {
                "PlaybackPositionTicks": 5 * 10_000_000,
                "PlayedPercentage": 5.0  # 假设这是一个很短的测试
            }
            
            async with session.post(f"{url}/Users/{user_id}/Items/{movie['Id']}/UserData", 
                                  json=position_update, headers=headers) as response:
                print(f"   位置更新响应: HTTP {response.status}")
                if response.status not in [200, 204]:
                    response_text = await response.text()
                    print(f"   响应内容: {response_text}")
            
            # 5b: 尝试标记为播放过的项目
            print("   标记为播放项目...")
            played_data = {
                "DatePlayed": datetime.now().isoformat() + "Z"
            }
            
            async with session.post(f"{url}/Users/{user_id}/PlayedItems/{movie['Id']}", 
                                  json=played_data, headers=headers) as response:
                print(f"   播放标记响应: HTTP {response.status}")
                if response.status not in [200, 204]:
                    response_text = await response.text()
                    print(f"   响应内容: {response_text}")
            
            print("   增强API播放测试完成")
            print("   请等待几秒后检查客户端的'继续观看'部分")
            
        except Exception as e:
            print(f"增强测试出错: {e}")

async def main():
    try:
        CFG = json.load(open("./emby.json"))
        
        print("=== Emby 真实客户端 vs API 对比分析 ===")
        
        # 只测试第一个服务器
        server = CFG['servers'][0]
        username = CFG['usernames'][0]
        password = CFG['passwords'][0]
        
        # 1. 分析当前状态
        await analyze_real_client_behavior(server, username, password)
        
        print("\n" + "="*50)
        input("请现在在真实客户端（手机或网页）开始播放一个电影几秒钟，然后按回车继续...")
        
        # 2. 再次分析，看看真实播放后的变化
        print("\n=== 真实播放后的状态 ===")
        await analyze_real_client_behavior(server, username, password)
        
        print("\n" + "="*50)
        print("现在测试增强的API播放...")
        
        # 3. 测试增强的API播放
        await test_enhanced_api_playback(server, username, password)
        
        print("\n=== 分析完成 ===")
        print("请对比真实客户端播放和API播放的差异")
        
    except Exception as e:
        print(f"分析工具错误: {e}")

if __name__ == "__main__":
    asyncio.run(main())