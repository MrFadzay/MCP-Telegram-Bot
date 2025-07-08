from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class ToolCall:
    server_name: str
    tool_name: str
    arguments: Dict[str, Any]

@dataclass
class ToolInfo:
    server_name: str
    tool_name: str
    description: str
    input_schema: Dict[str, Any]