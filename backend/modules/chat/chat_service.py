from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from os import environ as env
from typing import Final

from openai.types.responses import ResponseInputParam, ToolParam

from backend.models import SensorData
from backend.state import AppState

MODEL = env.get("MODEL", "gpt-4o-mini")

SYSTEM_PROMPT: Final = """
You are FireGuard, a functional device for monitoring and alerting fire hazards.
Keep response concise, refrain from answering outside of your domain.

You have access to the system's sensors, which is polled periodically every few
seconds. When presenting sensor data, format it as a markdown table for clarity.
"""

# Type alias for tool handler functions
ToolHandler = Callable[[AppState, dict[str, object]], str]


@dataclass
class Tool:
	"""Represents a tool with its OpenAI definition and handler."""

	definition: ToolParam
	handler: ToolHandler


def get_sensor_data_by_time(
	state: AppState, time_delta_seconds: float | None = None, limit: int | None = None
) -> list[SensorData]:
	"""Retrieve sensor data by time delta or limit."""
	with state.get_db() as db:
		query = db.query(SensorData).order_by(SensorData.timestamp.desc())

		if time_delta_seconds is not None:
			cutoff = datetime.now() - timedelta(seconds=time_delta_seconds)
			query = query.filter(SensorData.timestamp >= cutoff)
		elif limit is not None:
			query = query.limit(limit)
		else:
			# Default limit if neither specified
			query = query.limit(10)

		return query.all()


def format_temperature_table(data: list[SensorData]) -> str:
	"""Format temperature data as a markdown table."""
	if not data:
		return "No temperature data available."

	rows = ["| Timestamp | Temperature (°C) |", "|-----------|------------------|"]
	for reading in data:
		timestamp = reading.timestamp.strftime("%Y-%m-%d %H:%M:%S")
		rows.append(f"| {timestamp} | {reading.temperature:.2f} |")

	return "\n".join(rows)


def format_gas_table(data: list[SensorData]) -> str:
	"""Format gas data as a markdown table."""
	if not data:
		return "No gas data available."

	rows = ["| Timestamp | Gas Level |", "|-----------|-----------|"]
	for reading in data:
		timestamp = reading.timestamp.strftime("%Y-%m-%d %H:%M:%S")
		rows.append(f"| {timestamp} | {reading.gas:.2f} |")

	return "\n".join(rows)


SENSOR_PARAMS: Final = {
	"type": "object",
	"properties": {
		"timeDelta": {
			"type": ["number", "null"],
			"description": """
				Optional time interval (in seconds) to retrieve data from. Should be
				omitted if `limit` is used to avoid conflict.
			""",
		},
		"limit": {
			"type": ["number", "null"],
			"description": """
				Optional maximum number of latest data points to retrieve, fallback to
				a predefined limit. Should be omitted if `timeDelta` is used to avoid
				conflict.
			""",
		},
	},
	"required": ["timeDelta", "limit"],
	"additionalProperties": False,
}


def handle_get_temperature(state: AppState, arguments: dict[str, object]) -> str:
	"""Handle get_temperature tool call."""
	time_delta = arguments.get("timeDelta")
	limit_val = arguments.get("limit")

	# Type narrowing for time_delta
	time_delta_float: float | None = None
	if isinstance(time_delta, (int, float)):
		time_delta_float = float(time_delta)

	# Type narrowing for limit
	limit: int | None = None
	if isinstance(limit_val, (int, float)):
		limit = int(limit_val)

	data = get_sensor_data_by_time(state, time_delta_float, limit)
	return format_temperature_table(data)


def handle_get_gas(state: AppState, arguments: dict[str, object]) -> str:
	"""Handle get_gas tool call."""
	time_delta = arguments.get("timeDelta")
	limit_val = arguments.get("limit")

	# Type narrowing for time_delta
	time_delta_float: float | None = None
	if isinstance(time_delta, (int, float)):
		time_delta_float = float(time_delta)

	# Type narrowing for limit
	limit: int | None = None
	if isinstance(limit_val, (int, float)):
		limit = int(limit_val)

	data = get_sensor_data_by_time(state, time_delta_float, limit)
	return format_gas_table(data)


TOOL_REGISTRY: Final[dict[str, Tool]] = {
	"get_temperature": Tool(
		definition={
			"type": "function",
			"name": "get_temperature",
			"description": "Retrieve the temperature sensor reading",
			"parameters": SENSOR_PARAMS,
			"strict": True,
		},
		handler=handle_get_temperature,
	),
	"get_gas": Tool(
		definition={
			"type": "function",
			"name": "get_gas",
			"description": "Retrieve the gas/smoke sensor reading",
			"parameters": SENSOR_PARAMS,
			"strict": True,
		},
		handler=handle_get_gas,
	),
}

# Build tools list from registry for OpenAI API
TOOLS: Final[list[ToolParam]] = [tool.definition for tool in TOOL_REGISTRY.values()]


def handle_tool_call(
	state: AppState, tool_name: str, arguments: dict[str, object]
) -> str:
	"""Execute a tool call using the registry and return the result."""
	tool = TOOL_REGISTRY.get(tool_name)
	if tool is None:
		return f"Unknown tool: {tool_name}"

	return tool.handler(state, arguments)


@dataclass
class ChatResult:
	"""Result of a chat interaction."""

	messages: list[dict[str, str]]
	tool_calls: list[dict[str, object]]


def chat(state: AppState, messages: list[dict[str, str]]) -> ChatResult:
	"""
	Process chat messages and return new assistant messages with tool call info.

	Args:
		state: Application state with OpenAI client and database access
		messages: List of messages in OpenAI format [{role, content}, ...]

	Returns:
		ChatResult with new messages and tool calls
	"""
	client = state.openai_client

	# Build input with system prompt
	inputs: ResponseInputParam = [
		{"role": "system", "content": SYSTEM_PROMPT},
		*messages,
	]

	new_messages: list[dict[str, str]] = []
	tool_calls: list[dict[str, object]] = []
	max_iterations = 20

	for _ in range(max_iterations):
		response = client.responses.create(
			model=MODEL,
			tools=TOOLS,
			input=inputs,
		)

		has_tool_calls = False

		for output in response.output:
			if output.type == "function_call":
				has_tool_calls = True

				# Parse and execute tool call
				arguments = json.loads(output.arguments)
				result = handle_tool_call(state, output.name, arguments)

				# Track tool call for frontend
				tool_calls.append(
					{
						"name": output.name,
						"arguments": arguments,
						"output": result,
					}
				)

				# Add tool call and result to inputs for next iteration
				inputs.append(output)
				inputs.append(
					{
						"type": "function_call_output",
						"call_id": output.call_id,
						"output": result,
					}
				)

			elif output.type == "message":
				# Extract text content from message
				content_parts = []
				for cnt in output.content:
					if cnt.type == "output_text":
						content_parts.append(cnt.text)
					elif cnt.type == "refusal":
						content_parts.append(cnt.refusal)

				message_content = "\n\n".join(content_parts)
				new_message = {"role": output.role, "content": message_content}

				inputs.append(new_message)
				new_messages.append(new_message)

		# If no tool calls, we're done
		if not has_tool_calls:
			break

	return ChatResult(messages=new_messages, tool_calls=tool_calls)
