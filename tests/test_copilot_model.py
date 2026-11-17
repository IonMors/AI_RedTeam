import asyncio
from copilot import CopilotClient

async def main():
    client = CopilotClient()

    try:
        await client.start()
        print("SUCCESS: Copilot SDK connected")

        session = await client.create_session()

        response = await session.send_and_wait(
            "Reply with exactly: Copilot SDK is working"
        )

        print("Response:", response)


    finally:
        await client.stop()

asyncio.run(main())