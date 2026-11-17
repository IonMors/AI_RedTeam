import asyncio
import json
import math
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from copilot import CopilotClient, PermissionRequest
from copilot.rpc import PermissionDecisionReject
from copilot.session import PermissionInvocation
from deepeval.models import DeepEvalBaseLLM
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def deny_permission(
    request: PermissionRequest, invocation: PermissionInvocation
) -> PermissionDecisionReject:
    # Evaluation prompts must never authorize actions on the developer's machine.
    return PermissionDecisionReject(feedback="Tools are disabled for model evaluation.")


class CopilotModel(DeepEvalBaseLLM):
    """Text-only DeepTeam adapter using the signed-in Copilot subscription."""

    def __init__(self):
        self.model_name = os.getenv("COPILOT_MODEL", "auto").strip()
        if not self.model_name:
            raise ValueError("COPILOT_MODEL must not be empty")
        try:
            self.timeout = float(os.getenv("COPILOT_TIMEOUT_SECONDS", "120"))
        except ValueError:
            raise ValueError("COPILOT_TIMEOUT_SECONDS must be a positive number") from None
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError("COPILOT_TIMEOUT_SECONDS must be a positive number")

    def load_model(self) -> "CopilotModel":
        return self

    def get_model_name(self) -> str:
        return self.model_name

    @staticmethod
    def _schema_class(schema: type[BaseModel] | BaseModel | None):
        if schema is None:
            return None
        if isinstance(schema, BaseModel):
            return type(schema)
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            return schema
        raise TypeError("schema must be a Pydantic model class or instance")

    
    async def _request(self, prompt: str) -> str:
        base_directory = os.getenv(
            "COPILOT_HOME",
            str(Path.home() / ".copilot")
        )

        async with CopilotClient() as client:

            async with await client.create_session(
                model=self.model_name,
                available_tools=[],
                excluded_tools=["builtin:*", "mcp:*", "custom:*"],
                tools=[],
                mcp_servers={},
                on_permission_request=deny_permission,
                skip_custom_instructions=True,
                enable_config_discovery=False,
                enable_file_hooks=False,
                enable_host_git_operations=False,
                enable_skills=False,
                enable_session_store=False,
                memory={"enabled": False},
                infinite_sessions={"enabled": False},
                system_message={
                    "mode": "append",
                    "content": (
                        "Respond only to the supplied model evaluation request. "
                        "Do not inspect files, execute commands, or invoke tools. "
                        "When a JSON schema is supplied, return only matching JSON."
                    ),
                },
            ) as session:

                response = await session.send_and_wait(
                    prompt,
                    timeout=self.timeout
                )

                content = getattr(response.data, "content", None) if response else None

                if not isinstance(content, str) or not content.strip():
                    raise RuntimeError("Copilot returned no text response")

                return content


    # DeepTeam's custom-model protocol also returns Pydantic objects for schema calls.
    async def a_generate(
        self, prompt: str, schema: type[BaseModel] | BaseModel | None = None
    ) -> Any:
        schema_class = self._schema_class(schema)
        if schema_class is not None:
            prompt = (
                f"{prompt}\n\nReturn only valid JSON matching this schema:\n"
                f"{json.dumps(schema_class.model_json_schema())}"
            )
        try:
            content = await asyncio.wait_for(self._request(prompt), timeout=self.timeout)
        except TimeoutError:
            raise RuntimeError(
                f"Copilot timed out after {self.timeout:g} seconds; "
                "check authentication or increase COPILOT_TIMEOUT_SECONDS."
            ) from None
        if schema_class is None:
            return content

        json_content = content.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", json_content, re.DOTALL)
        if fenced:
            json_content = fenced.group(1)
        try:
            return schema_class.model_validate_json(json_content)
        except ValidationError:
            # Do not echo model output, which may contain sensitive evaluation data.
            raise ValueError("Copilot response did not match the requested JSON schema") from None

    def generate(
        self, prompt: str, schema: type[BaseModel] | BaseModel | None = None
    ) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.a_generate(prompt, schema))
        # Some DeepTeam paths call generate() from an already-running event loop.
        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(
                lambda: asyncio.run(self.a_generate(prompt, schema))
            ).result()