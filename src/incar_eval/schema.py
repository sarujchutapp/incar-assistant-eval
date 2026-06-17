"""The intent/slot schema the assistant is prompted against.

Slice 1 carries a single intent (`set_climate`) to keep the tracer bullet thin;
slice 2 expands this to the full frozen v1 ontology (six intents + two
abstention labels) from benchmark_spec.md §6.1.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class IntentSpec:
    name: str
    slots: tuple[str, ...]
    description: str


SCHEMA: dict[str, IntentSpec] = {
    "set_climate": IntentSpec(
        name="set_climate",
        slots=("temp", "zone"),
        description="Set cabin temperature. temp in degrees C; zone in {driver, passenger, all}.",
    ),
}


def schema_text() -> str:
    """Render the schema as the NL description block for the prompt."""
    return "\n".join(
        f"- {spec.name}({', '.join(spec.slots)}): {spec.description}"
        for spec in SCHEMA.values()
    )
