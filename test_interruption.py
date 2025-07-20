import aiohttp
import asyncio
import json
from datetime import datetime

async def test_interruption_behavior(url, username, password):
    """
    测试中断对播放记录的影响
    """
    connector = aiohttp.TCPConnector(ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            # 登录
            login_data = {"Username": username, "Pw": password}
            login_headers = {
                "X-Emby-Authorization": 'Emby UserId="", Client="TestClient", Device="Windows", DeviceId="test-interrupt", Version="4.8.0"',
                "Content-Type": "application/json"
            }
            
            async with session.post(f"{url}/Users/AuthenticateByName", json=login_data, headers=login_headers) as response:
                auth = await response.json()
            
            token = auth['AccessToken']
            user_id = auth['User']['Id']
            headers = {"X-MediaBrowser-Token": token, "Content-Type": "application/json"}
            
            # 获取一个电影
            params = {'Recursive': 'true', 'IncludeItemTypes': 'Movie', 'Limit': '1'}
            async with session.get(f"{url}/Users/{user_id}/Items", params=params, headers=headers) as response:
                data = await response.json()
                movie = data['Items'][0]
            
            print(f"测试电影: {movie['Name']}")
            
            # 检查初始播放位置
            async with session.get(f"{url}/Users/{user_id}/Items/{movie['Id']}", headers=headers) as response:
                initial_data = await response.json()
                initial_position = initial_data.get('UserData', {}).get('PlaybackPositionTicks', 0) // 10_000_000
                print(f"初始播放位置: {initial_position}秒")
            
            # 开始播放
            play_session_id = f"test-{datetime.now().strftime('%H%M%S')}"
            play_data = {
                "UserId": user_id,
                "ItemId": movie['Id'],
                "MediaSourceId": movie['Id'],
                "PlayMethod": "DirectPlay",
                "PositionTicks": initial_position * 10_000_000,
                "PlaySessionId": play_session_id,
                "CanSeek": True,
                "IsPaused": False
            }
            
            await session.post(f"{url}/Sessions/Playing", json=play_data, headers=headers)
            print("播放会话已建立")
            
            # 模拟播放并定期保存
            print("开始模拟播放，每30秒保存一次进度...")
            print("你可以在任何时候按 Ctrl+C 来测试中断效果")
            
            elapsed = 0
            save_interval = 30
            
            try:
                while elapsed < 300:  # 最多5分钟
                    await asyncio.sleep(save_interval)
                    elapsed += save_interval
                    
                    position_ticks = (initial_position + elapsed) * 10_000_000
                    
                    progress_data = {
                        "UserId": user_id,
                        "ItemId": movie['Id'],
                        "MediaSourceId": movie['Id'],
                        "PositionTicks": position_ticks,
                        "PlaySessionId": play_session_id,
                        "PlayMethod": "DirectPlay",
                        "IsPaused": False
                    }
                    
                    await session.post(f"{url}/Sessions/Playing/Progress", json=progress_data, headers=headers)
                    print(f"✓ 已保存进度: {initial_position + elapsed}秒")
                    
            except KeyboardInterrupt:
                print(f"\n⚠️  检测到中断！最后保存的位置: {initial_position + elapsed - save_interval}秒")
                
                # 检查实际保存的位置
                await asyncio.sleep(1)
                async with session.get(f"{url}/Users/{user_id}/Items/{movie['Id']}", headers=headers) as response:
                    final_data = await response.json()
                    final_position = final_data.get('UserData', {}).get('PlaybackPositionTicks', 0) // 10_000_000
                    print(f"📱 服务器记录的位置: {final_position}秒")
                    
                    if final_position == initial_position + elapsed - save_interval:
                        print("✅ 验证成功：服务器保存了最后一次成功更新的位置")
                    else:
                        print(f"❓ 位置不匹配，可能有其他因素影响")
                
                return
            
            print("测试完成（未中断）")
            
        except Exception as e:
            print(f"测试出错: {e}")

async def main():
    try:
        CFG = json.load(open("./emby.json"))
        
        print("=== Emby 播放中断测试 ===")
        print("这个测试会验证播放记录的保存机制")
        print("你可以在任何时候按 Ctrl+C 来模拟中断\n")
        
        # 只测试第一个服务器
        server = CFG['servers'][0]
        username = CFG['usernames'][0]
        password = CFG['passwords'][0]
        
        await test_interruption_behavior(server, username, password)
        
    except Exception as e:
        print(f"程序错误: {e}")

if __name__ == "__main__":
    asyncio.run(main())