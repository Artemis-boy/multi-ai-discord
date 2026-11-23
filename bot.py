"""Jalankan dua atau lebih bot AI di satu server Discord.

Cara pakai:
    cp .env.example .env              # isi token Discord dan API key AI
    cp config.example.json config.json  # isi nama bot, channel, dan model
    python bot.py

Setiap bot punya token Discord sendiri, persona sendiri, dan model AI sendiri.
Bot bergiliran membalas (round-robin) supaya obrolan antar AI tidak jadi spam
dan tidak berputar tanpa henti. Ada pengaman: jeda antar balasan, batas giliran
bot berurutan, dan jeda otomatis setelah batas itu tercapai.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import time

import discord
from dotenv import load_dotenv

from ai_client import AIClient, AIError
from config import ConfigError, load_config, require_env
from conversation import ChannelState, ChatMessage

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("multi-ai-discord")


def user_id_from_token(token: str) -> int:
    """ID user bot tersimpan di segmen pertama token (base64 dari ID)."""
    first = token.split(".")[0]
    first += "=" * (-len(first) % 4)
    return int.from_bytes(base64.urlsafe_b64decode(first), "big")


class AIBot(discord.Client):
    """Satu bot Discord yang dijawab oleh satu AI."""

    def __init__(self, bot_cfg, app_cfg, states, bot_ids, bot_names):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.cfg = bot_cfg
        self.app = app_cfg
        self.states = states            # dict channel_id -> ChannelState
        self.bot_ids = bot_ids          # set id semua bot yang dikonfigurasi
        self.bot_names = bot_names      # channel_id -> [nama bot urutan config]
        self.ai = AIClient(bot_cfg.base_url, require_env(bot_cfg.api_key_env),
                           bot_cfg.model)
        self.token = require_env(bot_cfg.token_env)

    async def on_ready(self):
        log.info("%s masuk sebagai %s (id %s)", self.cfg.name, self.user, self.user.id)

    def _names_in(self, channel_id: int) -> list:
        return self.bot_names.get(channel_id, [])

    def _is_first_bot(self, channel_id: int) -> bool:
        names = self._names_in(channel_id)
        return bool(names) and names[0] == self.cfg.name

    def _my_turn(self, state: ChannelState, channel_id: int) -> bool:
        """Apakah giliran bot ini yang bicara di channel ini?"""
        names = self._names_in(channel_id)
        if not names:
            return False
        return names[state.next_index % len(names)] == self.cfg.name

    def _claim_turn(self, state: ChannelState, channel_id: int) -> None:
        names = self._names_in(channel_id)
        if names:
            state.next_index = (state.next_index + 1) % len(names)

    async def on_message(self, message: discord.Message):
        if message.author.id == self.user.id:
            return
        if message.channel.id not in self.cfg.channels:
            return
        if not message.content.strip():
            return

        state = self.states.setdefault(
            message.channel.id, ChannelState(max_history=self.app.max_history))

        # Perintah reset, hanya dari manusia, hanya dieksekusi bot pertama.
        if (not message.author.bot
                and message.content.strip() == f"{self.app.command_prefix}reset"
                and self._is_first_bot(message.channel.id)):
            state.reset()
            await message.channel.send("Riwayat percakapan di channel ini sudah direset.")
            return

        is_configured_bot = message.author.id in self.bot_ids
        if message.author.bot and not is_configured_bot:
            return  # Abaikan bot lain yang tidak dikonfigurasi.
        if message.author.bot and not self.cfg.reply_to_bots:
            return
        if not message.author.bot and not self.cfg.reply_to_humans:
            return

        # Catat pesan ke riwayat (sekali saja walau semua bot memprosesnya).
        state.add(ChatMessage(author=message.author.display_name,
                              author_id=message.author.id,
                              is_bot=message.author.bot,
                              content=message.content),
                  message.id)

        mentioned = (self.user in message.mentions
                     or self.cfg.name.lower() in message.content.lower())
        if mentioned:
            reply = True
        else:
            # Manusia atau bot lain bicara: hanya bot yang gilirannya yang balas.
            reply = self._my_turn(state, message.channel.id)
        if not reply:
            return

        now = time.time()
        if not state.bot_allowed(self.user.id, now, self.cfg.cooldown_s,
                                 self.app.max_bot_turns,
                                 self.app.pause_after_max_s):
            return

        self._claim_turn(state, message.channel.id)
        state.mark_replied(self.user.id, now)
        try:
            text = await self.ai.chat(
                state.to_llm_messages(self.user.id, self.cfg.system_prompt),
                temperature=self.cfg.temperature)
        except AIError as exc:
            log.warning("%s gagal memanggil AI: %s", self.cfg.name, exc)
            return
        if not text:
            return
        sent = await message.channel.send(text[:2000])
        state.add(ChatMessage(author=self.cfg.name, author_id=self.user.id,
                              is_bot=True, content=text),
                  sent.id)


async def main():
    load_dotenv()
    try:
        app_cfg = load_config()
        states: dict = {}
        bot_ids: set = set()
        bot_names: dict = {}
        clients = []
        for bot_cfg in app_cfg.bots:
            token = require_env(bot_cfg.token_env)
            bot_ids.add(user_id_from_token(token))
            for channel_id in bot_cfg.channels:
                bot_names.setdefault(channel_id, []).append(bot_cfg.name)
            clients.append(AIBot(bot_cfg, app_cfg, states, bot_ids, bot_names))
    except ConfigError as exc:
        log.error("%s", exc)
        return
    log.info("Menjalankan %d bot: %s",
             len(clients), ", ".join(c.cfg.name for c in clients))
    await asyncio.gather(*(client.start(client.token) for client in clients))


if __name__ == "__main__":
    asyncio.run(main())
