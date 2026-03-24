"""大模型客户端模块：使用工厂模式创建不同供应商客户端。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Generator, Protocol

import requests


class LLMClient(Protocol):
    """统一的大模型客户端接口。"""

    def chat(self, prompt: str, history: list[dict[str, str]]) -> str:
        ...

    def stream_chat(self, prompt: str, history: list[dict[str, str]]) -> Generator[str, None, None]:
        ...


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

    def chat(self, prompt: str, history: list[dict[str, str]]) -> str:
        messages = history + [{'role': 'user', 'content': prompt}]
        url = self.base_url.rstrip('/') + '/chat/completions'
        resp = requests.post(
            url,
            json={'model': self.model, 'messages': messages, 'stream': False},
            headers={'Authorization': f'Bearer {self.api_key}'},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data['choices'][0]['message']['content']

    def stream_chat(self, prompt: str, history: list[dict[str, str]]) -> Generator[str, None, None]:
        messages = history + [{'role': 'user', 'content': prompt}]
        url = self.base_url.rstrip('/') + '/chat/completions'
        with requests.post(
            url,
            json={'model': self.model, 'messages': messages, 'stream': True},
            headers={'Authorization': f'Bearer {self.api_key}'},
            timeout=60,
            stream=True,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith('data: '):
                    continue
                payload = line[6:]
                if payload.strip() == '[DONE]':
                    break
                yield payload


class LLMClientFactory:
    """工厂模式：根据模型名创建具体客户端。

    好处：
    1. 上层业务不关心具体类实例化细节。
    2. 新增供应商时，只需扩展工厂映射与客户端类。
    """

    @staticmethod
    def create(model_name: str) -> LLMClient:
        if model_name == 'mock':
            return MockLLMClient()

        if model_name == 'deepseek':
            api_key = os.getenv('DEEPSEEK_API_KEY', '')
            base_url = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
            return OpenAICompatibleClient(base_url=base_url, api_key=api_key, model='deepseek-chat')

        # 其他模型的入口（可选扩展）：
        # - qwen
        # - chatglm
        # - ernie
        raise ValueError(f'未知模型：{model_name}')
