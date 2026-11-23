"""Status percakapan per channel: riwayat, giliran bicara, dan pengaman loop.

Modul ini murni logika Python, tidak butuh Discord, jadi bisa diuji tanpa token.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class ChatMessage:
    """Satu pesan di channel."""

    author: str
    author_id: int
    is_bot: bool
    content: str


@dataclass
class ChannelState:
    """Status satu channel yang dipakai bersama oleh semua bot."""

    max_history: int = 20
    history: deque = field(default_factory=deque)
    bot_turns: int = 0
    paused_until: float = 0.0
    last_reply_at: dict = field(default_factory=dict)
    next_index: int = 0
    _seen_ids: set = field(default_factory=set)
    _seen_order: deque = field(default_factory=deque)

    def __post_init__(self):
        self.history = deque(self.history, maxlen=self.max_history)

    def add(self, message: ChatMessage, message_id: int) -> bool:
        """Catat pesan sekali saja (berdasarkan ID). False kalau sudah dicatat."""
        if message_id in self._seen_ids:
            return False
        self._seen_ids.add(message_id)
        self._seen_order.append(message_id)
        if len(self._seen_order) > 200:
            self._seen_ids.discard(self._seen_order.popleft())
        self.history.append(message)
        if message.is_bot:
            self.bot_turns += 1
        else:
            self.bot_turns = 0
        return True

    def reset(self) -> None:
        self.history.clear()
        self.bot_turns = 0
        self.paused_until = 0.0
        self.last_reply_at.clear()
        self.next_index = 0
        self._seen_ids.clear()
        self._seen_order.clear()

    def bot_allowed(self, bot_id: int, now: float, cooldown_s: float,
                    max_bot_turns: int, pause_s: float) -> bool:
        """Cek pengaman: jeda antar balasan dan batas giliran bot berurutan."""
        if now < self.paused_until:
            return False
        if self.paused_until:
            # Jeda selesai, mulai ronde baru.
            self.paused_until = 0.0
            self.bot_turns = 0
        if self.bot_turns >= max_bot_turns:
            self.paused_until = now + pause_s
            return False
        last = self.last_reply_at.get(bot_id, 0.0)
        if now - last < cooldown_s:
            return False
        return True

    def mark_replied(self, bot_id: int, now: float) -> None:
        self.last_reply_at[bot_id] = now

    def to_llm_messages(self, own_id: int, system_prompt: str) -> list:
        """Ubah riwayat jadi format chat completions untuk bot dengan own_id."""
        messages = [{"role": "system", "content": system_prompt}]
        for msg in self.history:
            role = "assistant" if msg.author_id == own_id else "user"
            messages.append({"role": role, "content": f"{msg.author}: {msg.content}"})
        return messages
