"""Tes logika giliran bicara tanpa butuh Discord.

Jalankan:  python -m unittest test_conversation -v
"""
import unittest

from conversation import ChannelState, ChatMessage


def msg(author, content, is_bot=False):
    return ChatMessage(author=author, author_id=abs(hash(author)) % 10_000,
                       is_bot=is_bot, content=content)


class TestChannelState(unittest.TestCase):
    def test_bot_turns_reset_oleh_manusia(self):
        s = ChannelState(max_history=10)
        s.add(msg("BotA", "halo", is_bot=True), 1)
        s.add(msg("BotB", "hai", is_bot=True), 2)
        self.assertEqual(s.bot_turns, 2)
        s.add(msg("Ikram", "pagi"), 3)
        self.assertEqual(s.bot_turns, 0)

    def test_pesan_yang_sama_tidak_dihitung_dua_kali(self):
        s = ChannelState(max_history=10)
        m = msg("BotA", "halo", is_bot=True)
        self.assertTrue(s.add(m, 99))
        self.assertFalse(s.add(m, 99))
        self.assertEqual(len(s.history), 1)
        self.assertEqual(s.bot_turns, 1)

    def test_batas_giliran_bot_lalu_jeda(self):
        s = ChannelState(max_history=10)
        now = 1000.0
        for i in range(10):
            s.add(msg("BotA", "x", is_bot=True), i)
        self.assertFalse(s.bot_allowed(1, now, 0.0, 10, 300.0))
        self.assertGreater(s.paused_until, now)
        # Masih dalam jeda: tetap tidak boleh.
        self.assertFalse(s.bot_allowed(1, now + 10, 0.0, 10, 300.0))
        # Jeda selesai: ronde baru, boleh lagi.
        self.assertTrue(s.bot_allowed(1, now + 301, 0.0, 10, 300.0))

    def test_cooldown_per_bot(self):
        s = ChannelState(max_history=10)
        now = 1000.0
        self.assertTrue(s.bot_allowed(1, now, 8.0, 10, 300.0))
        s.mark_replied(1, now)
        self.assertFalse(s.bot_allowed(1, now + 5, 8.0, 10, 300.0))
        self.assertTrue(s.bot_allowed(1, now + 9, 8.0, 10, 300.0))
        # Bot lain tidak kena cooldown bot pertama.
        self.assertTrue(s.bot_allowed(2, now + 5, 8.0, 10, 300.0))

    def test_to_llm_messages(self):
        s = ChannelState(max_history=10)
        s.add(msg("Ikram", "halo"), 1)
        s.add(msg("Artemis", "hai Ikram", is_bot=True), 2)
        own_id = abs(hash("Artemis")) % 10_000
        out = s.to_llm_messages(own_id, "Kamu Artemis.")
        self.assertEqual(out[0], {"role": "system", "content": "Kamu Artemis."})
        self.assertEqual(out[1]["role"], "user")
        self.assertEqual(out[1]["content"], "Ikram: halo")
        self.assertEqual(out[2]["role"], "assistant")

    def test_reset(self):
        s = ChannelState(max_history=10)
        s.add(msg("BotA", "halo", is_bot=True), 1)
        s.reset()
        self.assertEqual(len(s.history), 0)
        self.assertEqual(s.bot_turns, 0)
        self.assertEqual(s.paused_until, 0.0)


if __name__ == "__main__":
    unittest.main()
