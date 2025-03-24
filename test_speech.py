import asyncio
from app.agent.speech import SpeechAgent

async def test():
    # Initialize the speech agent
    agent = SpeechAgent()

    # Test text-to-speech
    result = await agent.run("speak", text="Hello, this is a test.")
    print(result)

    # Test speech-to-text
    result = await agent.run("listen")
    print(result)

    # Clean up
    await agent.cleanup()

if __name__ == "__main__":
    asyncio.run(test())
