from dataclasses import dataclass


@dataclass
class FieldSchema:
    header_name: str
    field: str
    value_options: list[str] | None = None
