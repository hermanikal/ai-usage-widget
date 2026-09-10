# Prompt untuk Codex atau Claude Code

Copy prompt berikut ke Codex atau Claude Code setelah repository ini di-clone. Prompt ini sengaja meminta konfigurasi lokal tanpa menaruh kredensial, IP privat, atau history usage ke Git.

```text
Saya ingin menyiapkan repository AI Usage Widget ini di Mac saya untuk penggunaan pribadi.

Tujuan:
- Jalankan API lokal untuk widget Scriptable iPhone.
- Pakai Claude monitoring saja, ChatGPT saja, atau keduanya sesuai konfigurasi yang tersedia.
- Jangan publish, commit, push, atau mengubah remote Git tanpa persetujuan eksplisit saya.

Tolong lakukan langkah berikut:
1. Baca README.md dan docs/PIPELINE.md sepenuhnya.
2. Cek status Git dan pastikan .env, data/, logs/, dan .venv/ tidak pernah di-stage.
3. Buat virtual environment .venv dan install requirements.txt.
4. Jika belum ada .env, copy .env.example menjadi .env, lalu generate API key acak minimal 32 karakter dan simpan hanya di .env. Jangan tampilkan key lengkap di respons, log, atau commit.
5. Default-kan AI_USAGE_BIND_HOST=127.0.0.1. Jangan ubah ke 0.0.0.0 atau membuka firewall/port forwarding tanpa persetujuan saya.
6. Validasi API:
   - Jalankan server secara lokal.
   - Test /health.
   - Test /api/claude-usage dengan header X-API-Key.
   - Jika CHATGPT_USAGE_COMMAND belum dikonfigurasi, laporkan bahwa endpoint ChatGPT sengaja unavailable; jangan membuat OAuth scraper, browser-cookie extractor, atau meminta kredensial ChatGPT.
   - Jika CHATGPT_USAGE_COMMAND sudah ada, test /api/chatgpt-usage dan cek projection-nya.
7. Beri instruksi Scriptable yang singkat dan spesifik:
   - widget/claude_usage_widget.js untuk Claude-only
   - widget/chatgpt_usage_widget.js untuk ChatGPT-only
   - widget/ai_usage_widget.js untuk gabungan
   Ingatkan saya untuk mengisi CONFIG.baseUrl dan CONFIG.apiKey hanya di salinan lokal Scriptable, bukan di file repository.
8. Jalankan checks berikut dan laporkan hasil ringkasnya:
   - python3 -m py_compile src/usage_api.py
   - node --check untuk semua file di widget/
   - scripts/pre-push-audit.sh
9. Jika saya meminta service persistent, gunakan install-launchagent.sh hanya setelah menunjukkan path target dan meminta persetujuan saya.

Batasan keamanan:
- Jangan pernah hardcode atau menampilkan API key, OAuth token, cookie browser, Telegram token/chat ID, alamat IP privat, atau usage history.
- Jika mengaktifkan laporan Telegram, simpan `TELEGRAM_BOT_TOKEN` dan `TELEGRAM_CHAT_ID` hanya di `.env`; uji dahulu dengan `./run-telegram-report.sh --preview`.
- Jangan expose API ke internet publik. Jika iPhone membutuhkan akses, rekomendasikan Tailscale/private VPN atau reverse proxy HTTPS dengan access control.
- Jangan menganggap projection sebagai quota resmi atau jaminan akses.

Di akhir, rangkum: mode provider yang berhasil aktif, endpoint yang berhasil diuji, widget yang harus saya pakai, dan tindakan manual tersisa.
```

## Prompt khusus: menambahkan adapter ChatGPT

Gunakan ini hanya bila sudah memiliki collector lokal yang sah dan user-authorized.

```text
Saya sudah memiliki collector ChatGPT lokal yang sah dan berizin. Tolong hubungkan ke AI Usage Widget melalui CHATGPT_USAGE_COMMAND.

Collector harus dieksekusi hanya di mesin lokal dan menulis satu JSON object ke stdout sesuai examples/chatgpt-snapshot.example.json: plan, updated_at, dan windows; tiap window untuk projection wajib punya label, used_percent, reset_at (ISO-8601 dengan timezone), dan window_hours.

Jangan membaca/menyalin cookie browser, OAuth token, API key, atau kredensial ke repository, .env.example, log, maupun respons. Jangan gunakan shell=True. Simpan secret collector di keychain atau config lokal yang di-ignore Git.

Setelah konfigurasi, uji GET /api/chatgpt-usage secara lokal dengan X-API-Key dan validasi bahwa proyeksi serta fallback error aman. Jangan commit atau push perubahan tanpa persetujuan saya.
```
