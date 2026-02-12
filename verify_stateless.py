import asyncio
import sys
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

# Patch event loop BEFORE importing main/bot
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# Mock dependencies before importing main
with patch('asyncpg.create_pool', new_callable=AsyncMock), \
     patch('pyrogram.Client.start', new_callable=AsyncMock), \
     patch('pyrogram.Client.invoke', new_callable=AsyncMock), \
     patch('pyrogram.Client.set_bot_commands', new_callable=AsyncMock):
    from main import fastapi_app
    import db

client = TestClient(fastapi_app)

async def run_test():
    print("🚀 Starting Verification Test...")
    
    # Mock DB functions
    db.is_update_processed = AsyncMock(return_value=False)
    db.mark_update_processed = AsyncMock()
    
    # Mock bot.app.process_update
    with patch('bot.app.process_update', new_callable=AsyncMock) as mock_process:
        # Simulate a simple message update
        update_payload = {
            "update_id": 123456,
            "message": {
                "message_id": 1,
                "from": {"id": 123, "first_name": "Tester"},
                "chat": {"id": 456, "type": "private"},
                "text": "/start"
            }
        }
        
        print("➡️ Sending webhook request...")
        response = client.post("/webhook", json=update_payload)
        
        print(f"⬅️ Response Status: {response.status_code}")
        assert response.status_code == 200
        
        print("🔍 Checking if bot processed the update...")
        assert mock_process.called
        print("✅ Bot process_update called!")
        
        print("🔍 Checking if update was marked as processed in DB...")
        assert db.mark_update_processed.called
        print("✅ Update marked as processed!")

    print("\n🎉 Verification Test Passed!")

if __name__ == "__main__":
    loop.run_until_complete(run_test())
