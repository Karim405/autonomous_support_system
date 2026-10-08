"""
Conversational Memory & Context Handling (Session 6):
- Tracks multi-turn dialogue history
- Preserves critical context across turns: active_order_id, customer_id, pending_action
- Summarizes or windows long chats to prevent context overflow
"""

from typing import List, Dict, Any, Optional

class ConversationMemoryManager:
    def __init__(self, max_buffer_turns: int = 10):
        self.max_buffer_turns = max_buffer_turns
        self.messages: List[Dict[str, str]] = []
        self.session_context: Dict[str, Any] = {
            "customer_id": None,
            "active_order_id": None,
            "pending_action": None,  # e.g., 'CANCEL_ORDER_CONFIRMATION'
            "last_intent": None
        }

    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})
        self._trim_history()

    def add_assistant_message(self, content: str):
        self.messages.append({"role": "assistant", "content": content})
        self._trim_history()

    def set_context(self, key: str, value: Any):
        if value is not None:
            self.session_context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        return self.session_context.get(key, default)

    def _trim_history(self):
        if len(self.messages) > self.max_buffer_turns * 2:
            self.messages = self.messages[-self.max_buffer_turns * 2:]

    def get_chat_history_str(self) -> str:
        lines = []
        for msg in self.messages:
            prefix = "Customer: " if msg["role"] == "user" else "Assistant: "
            lines.append(prefix + msg["content"])
        return "\n".join(lines)

    def clear(self):
        self.messages.clear()
        self.session_context = {
            "customer_id": None,
            "active_order_id": None,
            "pending_action": None,
            "last_intent": None
        }
