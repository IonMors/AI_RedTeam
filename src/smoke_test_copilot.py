from typing import Literal

from pydantic import BaseModel

from copilot_model import CopilotModel


class ProbeResponse(BaseModel):
    status: Literal["SUCCESS"]


def main():
    # This is a live request and consumes the signed-in account's Copilot allowance.
    model = CopilotModel()
    print("Testing Copilot custom model...")
    result = model.generate(
        "Return JSON with status set to SUCCESS.", schema=ProbeResponse
    )
    print("Model:", model.get_model_name())
    print("Structured response:", result)
    print("Copilot custom model test PASSED")


if __name__ == "__main__":
    main()