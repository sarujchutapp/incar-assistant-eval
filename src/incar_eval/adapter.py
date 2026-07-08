"""Target adapter: drive the model-under-test for one case.

Builds the car-assistant prompt from the shared skill (``skill.md``) + schema,
calls the model through the model-client port, and parses the raw response into
a normalized ``ToolCall``. All model-output handling lives here.
"""

import json
from pathlib import Path

from .client import ModelClient
from .models import CarState, GoldRecord, ResponseMode, ToolCall
from .schema import schema_text

#: Single source of truth for the car-assistant prompt. The SkillOpt seed skill
#: (integrations/skillopt/.../skills/initial.md) is a copy of this file.
SYSTEM_PROMPT = (Path(__file__).parent / "skill.md").read_text(encoding="utf-8").strip()


def build_query_prompt(utterance: str, car_state: CarState | None = None) -> str:
    context = f"Vehicle is {car_state.vehicle_motion}.\n" if car_state is not None else ""
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Available intents:\n{schema_text()}\n\n"
        f"{context}"
        f'Driver said: "{utterance}"'
    )


def build_prompt(record: GoldRecord) -> str:
    return build_query_prompt(record.utterance, record.car_state)


def _parse_mode(value: str) -> ResponseMode:
    # Tolerate non-conforming model output (e.g. mode "none" on an abstention):
    # fall back to EXECUTE rather than crash ingestion.
    try:
        return ResponseMode(value)
    except ValueError:
        return ResponseMode.EXECUTE


def parse_tool_call(raw: str) -> ToolCall:
    data = json.loads(raw)
    return ToolCall(
        intent=data["intent"],
        slots=data.get("slots", {}),
        mode=_parse_mode(data.get("mode", "execute")),
        eyes_free=data.get("eyes_free", True),
    )


def run_case(record: GoldRecord, client: ModelClient) -> ToolCall:
    return parse_tool_call(client.complete(build_prompt(record)))
