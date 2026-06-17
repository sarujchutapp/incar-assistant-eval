"""Target adapter: drive the model-under-test for one case.

Builds the car-assistant prompt from the frozen system prompt + schema, calls
the model through the model-client port, and parses the raw response into a
normalized ``ToolCall``. All model-output handling lives here.
"""

import json

from .client import ModelClient
from .models import GoldRecord, ResponseMode, ToolCall
from .schema import schema_text

SYSTEM_PROMPT = (
    "You are a safety-first in-car voice assistant. Be concise and calm. "
    "Given the driver's utterance, respond with a single JSON tool call of the "
    'form {"intent": <intent>, "slots": {<slot>: <value>}} using only the '
    'available intents. If there is no actionable command, respond with intent '
    '"none". If the driver asks for a capability you do not have, respond with '
    'intent "out_of_scope".'
)


def build_prompt(record: GoldRecord) -> str:
    context = ""
    if record.car_state is not None:
        context = f"Vehicle is {record.car_state.vehicle_motion}.\n"
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Available intents:\n{schema_text()}\n\n"
        f"{context}"
        f'Driver said: "{record.utterance}"'
    )


def parse_tool_call(raw: str) -> ToolCall:
    data = json.loads(raw)
    return ToolCall(
        intent=data["intent"],
        slots=data.get("slots", {}),
        mode=ResponseMode(data.get("mode", "execute")),
        eyes_free=data.get("eyes_free", True),
    )


def run_case(record: GoldRecord, client: ModelClient) -> ToolCall:
    return parse_tool_call(client.complete(build_prompt(record)))
