TOOL_DESCRIPTION_TEMPLATE = """
Доступные инструменты:
{tools_list}

Если вам нужно использовать инструмент, ответьте JSON-объектом в формате:
{{"tool_call": {{"server_name": "...", "tool_name": "...", "arguments": {{...}}}}}}

Пример использования инструмента brave_web_search:
{{"tool_call": {{"server_name": "brave-search", "tool_name": "brave_web_search", "arguments": {{"query": "последние новости"}}}}}}

Пример использования инструмента brave_local_search:
{{"tool_call": {{"server_name": "brave-search", "tool_name": "brave_local_search", "arguments": {{"query": "пицца рядом со мной"}}}}}}

Пример вывода всех доступных инструментов:
{{"tool_call": {{"server_name": "meta", "tool_name": "list_mcp_tools", "arguments": {{}}}}}}

В противном случае, ответьте обычной строкой.
"""

TOOL_INFO_TEMPLATE = "- Сервер: {server_name}, Инструмент: {tool_name}\n  Описание: {description}\n  Схема ввода: {input_schema}"

AVAILABLE_TOOLS_RESPONSE_TEMPLATE = """Доступные MCP инструменты:
{tools_list}
"""

NO_TOOLS_AVAILABLE_RESPONSE = "В настоящее время нет доступных MCP инструментов."
