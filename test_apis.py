import asyncio
import traceback
from app.database import async_session
from app.routers.book_api import dashboard_stats
from app.routers.member_api import list_members

async def run():
    async with async_session() as db:
        print("--- Testing Stats API ---")
        try:
            await dashboard_stats(db)
            print('✓ Stats Success')
        except Exception as e:
            traceback.print_exc()
            
        print("\n--- Testing Members API ---")
        try:
            await list_members(db)
            print('✓ Members Success')
        except Exception as e:
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())
