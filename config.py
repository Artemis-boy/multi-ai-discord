"""Muat dan validasi config.json. Semua rahasia (token) dibaca dari environment."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass


class ConfigError(Exception):
    """Error konfigurasi yang bisa dijelaskan ke pengguna."""


@dataclass
class BotConfig:
    name: str
    token_env: str
    base_url: str
    api_key_env: str
    model: str
    system_prompt: str
    channels: list
    reply_to_humans: bool = True
    reply_to_bots: bool = True
    cooldown_s: float = 8.0
    temperature: float = 0.7


@dataclass
class AppConfig:
    bots: list
    max_history: int = 20
    max_bot_turns: int = 10
    pause_after_max_s: float = 300.0
    command_prefix: str = "!"


def load_config(path: str = "config.json") -> AppConfig:
    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError as exc:
        raise ConfigError(
            f"File {path} tidak ditemukan. Salin config.example.json menjadi "
            f"config.json lalu isi.") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"File {path} bukan JSON yang valid: {exc}") from exc

    bots = []
    for i, item in enumerate(raw.get("bots", [])):
        try:
            bots.append(BotConfig(**item))
        except TypeError as exc:
            raise ConfigError(f"Bot ke-{i + 1} di config.json tidak lengkap: {exc}") from exc
    if not bots:
        raise ConfigError("config.json tidak berisi bot sama sekali.")
    if len({b.name for b in bots}) != len(bots):
        raise ConfigError("Nama bot di config.json harus unik.")
    return AppConfig(
        bots=bots,
        max_history=raw.get("max_history", 20),
        max_bot_turns=raw.get("max_bot_turns", 10),
        pause_after_max_s=raw.get("pause_after_max_s", 300.0),
        command_prefix=raw.get("command_prefix", "!"),
    )


def require_env(name: str) -> str:
    """Ambil environment variable, error jelas kalau belum diisi."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(f"Environment variable {name} belum diisi. Cek file .env.")
    return value
