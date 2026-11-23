# multi-ai-discord

Sambungkan **dua atau lebih AI** ke satu server Discord, supaya mereka bisa ngobrol dengan manusia dan dengan sesama AI di channel yang sama.

Setiap bot punya token Discord sendiri, persona sendiri, dan model AI sendiri. Bot bergiliran membalas (round-robin) supaya obrolan antar AI tidak jadi spam dan tidak berputar tanpa henti.

## Cara kerja

- Satu proses Python menjalankan semua bot (satu koneksi gateway per bot).
- Setiap AI dihubungi lewat API yang kompatibel dengan OpenAI (`/chat/completions`), jadi bisa pakai OpenAI, 9Router, Ollama, atau layanan sejenis.
- Bot membalas kalau disebut namanya, kalau manusia bicara di channel yang dipantau, atau kalau gilirannya tiba setelah bot lain bicara.
- Pengaman loop: jeda antar balasan per bot, batas giliran bot berurutan (default 10), lalu jeda otomatis 5 menit. Ketik `!reset` di channel untuk membersihkan riwayat percakapan.

## Syarat

- Python 3.10+
- Token bot Discord untuk tiap AI (lihat di bawah)
- API key AI (OpenAI, 9Router, atau yang sejenis)

## Pasang

```bash
git clone https://github.com/Artemis-boy/multi-ai-discord.git
cd multi-ai-discord
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
cp config.example.json config.json
```

Lalu isi `.env` (token dan API key) dan `config.json` (nama bot, channel, model, persona).

## 1. Buat bot Discord

Untuk tiap AI, buat satu aplikasi bot:

1. Buka [Discord Developer Portal](https://discord.com/developers/applications) → **New Application** → beri nama (misalnya `Artemis`).
2. Menu **Bot** → **Reset Token** → salin tokennya (tombol Copy). Masukkan ke `.env`.
3. Di halaman Bot yang sama, nyalakan **Message Content Intent** (wajib, kalau tidak bot tidak bisa membaca isi pesan).
4. Menu **OAuth2 → URL Generator**: centang scope `bot`, lalu permission **View Channels**, **Send Messages**, **Read Message History** (nilai permission: `68608`). Buka URL yang dihasilkan dan pilih servermu.
5. Ulangi untuk bot kedua, ketiga, dan seterusnya.

## 2. Isi config

`config.json` (contoh lengkap di `config.example.json`):

- `name`: nama bot, dipakai untuk mendeteksi kalau namanya disebut di chat.
- `token_env`: nama environment variable di `.env` yang berisi token bot ini.
- `base_url`: alamat API AI. OpenAI: `https://api.openai.com/v1`. 9Router (lokal): `http://localhost:20128/v1`. Ollama: `http://localhost:11434/v1`.
- `api_key_env`: nama environment variable berisi API key.
- `model`: nama model di layanan itu (misalnya `gpt-4o-mini`).
- `system_prompt`: persona bot ini.
- `channels`: daftar ID channel yang dipantau bot ini. Cara dapat ID channel: di Discord, **Settings → Advanced → Developer Mode** nyalakan, lalu klik kanan channel → **Copy Channel ID**.
- `reply_to_humans` / `reply_to_bots`: apakah bot membalas manusia / bot lain.
- `cooldown_s`: jeda minimal antar balasan bot ini.
- `temperature`: kreativitas jawaban (0 = kaku, 1 = liar).

Pengaturan global:

- `max_history`: jumlah pesan terakhir yang dikirim ke AI sebagai konteks (default 20).
- `max_bot_turns`: jumlah balasan bot berurutan sebelum jeda otomatis (default 10).
- `pause_after_max_s`: lama jeda otomatis setelah batas tercapai (default 300 detik).
- `command_prefix`: awalan perintah, default `!` (`!reset` membersihkan riwayat channel).

## 3. Jalankan

```bash
python bot.py
```

Kalau berhasil, log akan menampilkan tiap bot masuk sebagai siapa. Coba kirim pesan di channel yang dipantau, atau sebut nama salah satu bot.

## Tambah bot ketiga, keempat, dan seterusnya

Tambah satu entri di array `bots` di `config.json` dan satu baris token di `.env`. Tidak ada batas jumlah bot di kode ini, tapi makin banyak bot makin ramai channelnya. Dua sampai tiga bot biasanya sudah cukup seru.

## Pakai model lokal / 9Router

Kalau kamu sudah menjalankan 9Router atau Ollama di komputermu, isi `base_url` dengan alamat lokalnya dan `api_key_env` dengan environment variable berisi key-nya (untuk layanan lokal, key boleh diisi apa saja). Model yang dipakai tinggal disesuaikan dengan nama model yang tersedia di layanan itu.

## Keamanan

- **Jangan pernah commit file `.env` atau `config.json` ke git.** Keduanya sudah ada di `.gitignore`. Token Discord dan API key hanya boleh ada di `.env` di komputermu sendiri.
- Jangan bagikan token bot ke orang lain. Siapa pun yang punya token bisa mengendalikan bot itu.
- Bot hanya membalas di channel yang ada di `channels`. Jangan masukkan channel yang tidak kamu mau.

## Tes

Tes logika giliran bicara (tidak butuh token Discord):

```bash
python -m unittest test_conversation -v
```

## Kalau ada masalah

- `401 Unauthorized` saat bot masuk: token di `.env` salah atau sudah di-reset. Salin ulang dari Developer Portal.
- Bot online tapi tidak membalas: pastikan **Message Content Intent** menyala di halaman Bot, dan ID channel di `config.json` benar.
- `API mengembalikan 401/404`: API key salah, atau nama model tidak ada di layanan itu.
- Bot membalas berulang-ulang: naikkan `cooldown_s` atau turunkan `max_bot_turns`.

## Lisensi

MIT. Silakan dipakai, diubah, dan dibagikan.
