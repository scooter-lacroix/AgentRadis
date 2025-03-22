import asyncio
from app.tool.search_engines import GoogleWebSearch

async def test():
    engine = GoogleWebSearch()
    result = await engine.search('test query')
    print(result)
    await engine.cleanup()

if __name__ == "__main__":
    asyncio.run(test()) 