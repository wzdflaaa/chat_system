"""大模型客户端模块：使用工厂模式创建不同供应商客户端。"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Generator, Protocol

import requests


class LLMClient(Protocol):
    """统一的大模型客户端接口。"""

    def chat(self, prompt: str, history: list[dict[str, str]]) -> str: ...
    def stream_chat(self, prompt: str, history: list[dict[str, str]]) -> Generator[str, None, None]: ...


@dataclass
class MockLLMClient:
    """默认 mock 客户端，便于离线演示和测试。"""

    def chat(self, prompt: str, history: list[dict[str, str]]) -> str:
        context_hint = f"（已收到{len(history)}条历史消息）"
        return f"这是一个模拟回复：你说的是『{prompt}』{context_hint}。"

    def stream_chat(self, prompt: str, history: list[dict[str, str]]) -> Generator[str, None, None]:
        text = self.chat(prompt, history)
        for i in range(0, len(text), 6):
            yield text[i : i + 6]


@dataclass
class OpenAICompatibleClient:
    """OpenAI 兼容 API 客户端（可用于 DeepSeek/通义等兼容接口）。"""

    base_url: str
    api_key: str
    model: str

    def _build_messages(self, prompt: str, history: list[dict[str, str]]) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        for msg in history:
            role = (msg.get("role") or "").strip()
            content = (msg.get("content") or "").strip()
            if role in ("user", "assistant", "system") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ValueError("未配置 DEEPSEEK_API_KEY，无法调用真实 API。")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat(self, prompt: str, history: list[dict[str, str]]) -> str:
        messages = self._build_messages(prompt, history)
        url = self.base_url.rstrip("/") + "/chat/completions"

        resp = requests.post(
            url,
            json={"model": self.model, "messages": messages, "stream": False},
            headers=self._headers(),
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def stream_chat(self, prompt: str, history: list[dict[str, str]]) -> Generator[str, None, None]:
        messages = self._build_messages(prompt, history)
        url = self.base_url.rstrip("/") + "/chat/completions"

        with requests.post(
            url,
            json={"model": self.model, "messages": messages, "stream": True},
            headers=self._headers(),
            timeout=60,
            stream=True,
        ) as resp:
            resp.raise_for_status()

            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if not line.startswith("data: "):
                    continue

                payload = line[6:].strip()
                if payload == "[DONE]":
                    break

                try:
                    obj = json.loads(payload)
                    delta = obj["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except Exception:
                    # 忽略不规范事件，避免整个流中断
                    continue


class LLMClientFactory:
    """工厂模式：根据模型名创建具体客户端。"""

    @staticmethod
    def create(model_name: str) -> LLMClient:
        if model_name == "mock":
            return MockLLMClient()

        if model_name == "deepseek":
            api_key = os.getenv("DEEPSEEK_API_KEY", "")
            base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
            return OpenAICompatibleClient(
                base_url=base_url,
                api_key=api_key,
                model="deepseek-chat",
            )

        raise ValueError(f"未知模型：{model_name}")
