
import httpx
from deepteam.test_case.test_case import RTTurn

TARGET_URL = "http://127.0.0.1:8000/chat"


async def model_callback(input: str, turns=None) -> RTTurn:

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            TARGET_URL,
            json={"message": input},
        )

        response.raise_for_status()
        result = response.json()

        return RTTurn(
            role="assistant",
            content=result["response"],
        )
