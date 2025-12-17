from typing import Literal

from pydantic import BaseModel, field_validator


class ChatMessage(BaseModel):
	"""A single chat message."""

	role: Literal["user", "assistant"]
	content: str

	@field_validator("content")
	@classmethod
	def content_not_empty(cls, v: str) -> str:
		if not v.strip():
			raise ValueError("Message content cannot be empty")
		return v


class ChatRequest(BaseModel):
	"""Chat request payload."""

	messages: list[ChatMessage]

	@field_validator("messages")
	@classmethod
	def messages_not_empty(cls, v: list[ChatMessage]) -> list[ChatMessage]:
		if not v:
			raise ValueError("At least one message is required")
		return v


class ChatResponse(BaseModel):
	"""Chat response payload."""

	messages: list[ChatMessage]

