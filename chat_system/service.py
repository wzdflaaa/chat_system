"""业务门面层：使用门面模式向 Web 层提供统一接口。"""
from __future__ import annotations

from chat_system.llm import LLMClientFactory
from chat_system.repository import ChatRepository


class ChatFacade:
    """门面模式（Facade）：统一编排会话、消息、LLM 调用流程。

    Web 层只需调用此类，不需要知道 Repository 与 LLM 的内部细节。
    """

    def __init__(self) -> None:
        self.repo = ChatRepository()

    def create_conversation(self, user_id: int, title: str, model_name: str = 'mock') -> int:
        return self.repo.create_conversation(user_id, title, model_name)

    def list_conversations(self, user_id: int) -> list[dict]:
        return self.repo.list_conversations(user_id)

    def list_messages(self, conversation_id: int) -> list[dict]:
        return self.repo.list_messages(conversation_id)

    def send_user_message(self, conversation_id: int, content: str) -> int:
        return self.repo.add_message(conversation_id, 'user', content)

    def stream_assistant_reply(self, conversation_id: int, prompt: str) -> tuple[str, list[str]]:
        conversation = self.repo.get_conversation(conversation_id)
        if not conversation:
            raise ValueError('会话不存在')
        history = [
            {'role': m['role'], 'content': m['content']}
            for m in self.repo.list_messages(conversation_id)
            if m['role'] in ('user', 'assistant', 'system')
        ]
        client = LLMClientFactory.create(conversation['model_name'])

        chunks: list[str] = []
        for chunk in client.stream_chat(prompt, history):
            chunks.append(chunk)
        full_text = ''.join(chunks)

        self.repo.add_message(conversation_id, 'assistant', full_text)
        return full_text, chunks

    def update_message(self, message_id: int, content: str) -> None:
        self.repo.update_message(message_id, content)

    def delete_message(self, message_id: int) -> None:
        self.repo.delete_message(message_id)
