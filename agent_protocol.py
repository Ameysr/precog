"""Universal agent protocol and adapters. Connect to any agent via standard interface."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

import requests

from config import REQUEST_TIMEOUT
from schemas import TestRunResult


class ChatMessage:
    def __init__(self, role: str, content: str, tool_calls: list[dict] | None = None):
        self.role = role
        self.content = content
        self.tool_calls = tool_calls or []

    def to_dict(self) -> dict:
        d = {"role": self.role, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        return d

    @classmethod
    def user(cls, content: str) -> "ChatMessage":
        return cls("user", content)

    @classmethod
    def assistant(cls, content: str, tool_calls: list[dict] | None = None) -> "ChatMessage":
        return cls("assistant", content, tool_calls)


class AgentResponse:
    def __init__(self, text: str, tool_calls: list[dict] | None = None, raw: dict | None = None):
        self.text = text
        self.tool_calls = tool_calls or []
        self.raw = raw or {}


class AgentProtocol(ABC):
    @abstractmethod
    def chat(self, messages: list[ChatMessage]) -> AgentResponse:
        ...

    @abstractmethod
    def reset(self) -> None:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...


class HTTPChatAdapter(AgentProtocol):
    def __init__(self, endpoint: str, api_key: str = "", model: str = "gpt-4o", headers: dict | None = None):
        self._endpoint = endpoint
        self._api_key = api_key
        self._model = model
        self._extra_headers = headers or {}
        self._session = requests.Session()
        self._conversation_id: str | None = None

    @property
    def name(self) -> str:
        return f"HTTP:{self._endpoint}"

    def chat(self, messages: list[ChatMessage]) -> AgentResponse:
        payload = {
            "model": self._model,
            "messages": [m.to_dict() for m in messages],
        }
        if self._conversation_id:
            payload["conversation_id"] = self._conversation_id

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        headers.update(self._extra_headers)

        try:
            resp = self._session.post(
                self._endpoint,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            return AgentResponse(text=f"[AGENT ERROR] {e}", tool_calls=[], raw={"error": str(e)})

        text = ""
        tool_calls = []

        if "choices" in data and data["choices"]:
            choice = data["choices"][0]
            msg = choice.get("message", {})
            text = msg.get("content", "")
            raw_tools = msg.get("tool_calls", [])
            for tc in raw_tools:
                tool_calls.append({
                    "id": tc.get("id", ""),
                    "type": tc.get("type", "function"),
                    "function": tc.get("function", {}),
                })
        elif "response" in data:
            text = data["response"]
        elif "text" in data:
            text = data["text"]
        elif "output" in data:
            text = data["output"]
        else:
            text = json.dumps(data)

        if "conversation_id" in data:
            self._conversation_id = data["conversation_id"]

        return AgentResponse(text=text, tool_calls=tool_calls, raw=data)

    def reset(self) -> None:
        self._conversation_id = None


class ScriptAdapter(AgentProtocol):
    def __init__(self, handler_fn, name: str = "script"):
        self._handler = handler_fn
        self._name = name
        self._history: list[dict] = []

    @property
    def name(self) -> str:
        return self._name

    def chat(self, messages: list[ChatMessage]) -> AgentResponse:
        for m in messages:
            self._history.append(m.to_dict())

        try:
            result = self._handler(self._history)
        except Exception as e:
            return AgentResponse(text=f"[AGENT ERROR] {e}", tool_calls=[], raw={"error": str(e)})

        if isinstance(result, str):
            return AgentResponse(text=result, tool_calls=[])
        if isinstance(result, dict):
            return AgentResponse(
                text=result.get("text", ""),
                tool_calls=result.get("tool_calls", []),
                raw=result,
            )
        return AgentResponse(text=str(result))

    def reset(self) -> None:
        self._history = []


class LangChainAdapter(AgentProtocol):
    def __init__(self, agent_executor, name: str = "langchain"):
        self._agent = agent_executor
        self._name = name
        self._history: list = []

    @property
    def name(self) -> str:
        return self._name

    def chat(self, messages: list[ChatMessage]) -> AgentResponse:
        try:
            last_msg = messages[-1].content if messages else ""
            config = {"configurable": {"session_id": self._name}}
            result = self._agent.invoke(
                {"messages": [("user", last_msg)]},
                config=config,
            )
            response_text = ""
            tool_calls = []
            if hasattr(result, "messages") and result.messages:
                last = result.messages[-1]
                response_text = getattr(last, "content", "") or ""
                if hasattr(last, "tool_calls"):
                    for tc in last.tool_calls:
                        tool_calls.append({
                            "id": tc.get("id", ""),
                            "type": "function",
                            "function": {"name": tc.get("name", ""), "arguments": json.dumps(tc.get("args", {}))},
                        })
            return AgentResponse(text=response_text, tool_calls=tool_calls)
        except Exception as e:
            return AgentResponse(text=f"[AGENT ERROR] {e}", tool_calls=[], raw={"error": str(e)})

    def reset(self) -> None:
        self._history = []
