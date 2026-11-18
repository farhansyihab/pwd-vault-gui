# pwd-vault-gui

Antarmuka desktop (Tkinter) untuk backend **pwd-vault**. Menjalankan dan mengelola proses backend, serta menyediakan GUI untuk login, kelola entri kata sandi, dan pembuatan kata sandi acak.

## Prasyarat

- Python 3.12+
- `python3-tk` (paket sistem, install manual: `sudo apt install python3-tk` di Ubuntu/Lubuntu)
- Backend pwd-vault sudah terpasang di `~/Proyek/pwd-vault` dengan virtual environment di `.venv`

## Instalasi

```bash
# 1. Clone / masuk folder proyek
cd pwd-vault-gui

# 2. Buat virtual environment
python3 -m venv .venv

# 3. Aktifkan & pasang dependensi
source .venv/bin/activate
pip install -e .
```

## Menjalankan Tes

```bash
# Dari root proyek, dengan venv aktif
.venv/bin/python -m pytest
```

## Menjalankan Aplikasi

```bash
# Dengan venv aktif
.venv/bin/python3 -m vaultgui
```

Atau langsung dari root proyek tanpa aktivasi manual:

```bash
.venv/bin/python3 -m vaultgui
```

## Penggunaan

1. **Panel Server** (atas):  
   - Tombol **Mulai** / **Hentikan** mengontrol proses backend.  
   - Saat dibuka, GUI mencoba memulai backend otomatis jika belum berjalan.

2. **Login**:  
   - Isi username & password akun yang dibuat via CLI di folder backend.  
   - Klik **Login** atau tekan Enter.  
   - Error 401 → "Username atau password salah".  
   - Error 429 → "Terlalu banyak percobaan. Coba lagi 5 menit."

3. **Daftar Entri** (setelah login):  
   - Melihat daftar entri (provider, username).  
   - Tombol **Logout** untuk keluar.

4. **Auto-lock**:  
   - 5 menit tanpa aktivitas keyboard/mouse → logout otomatis & kembali ke layar login.

5. **Keluar Aplikasi**:  
   - Tutup jendela → konfirmasi hentikan backend (jika GUI yang menyalakannya).

## Struktur Proyek (ringkas)

```
pwd-vault-gui/
├── vaultgui/           # Kode sumber
│   ├── __main__.py     # Entry point
│   ├── config.py       # Konfigurasi host, port, path backend
│   ├── server_manager.py
│   ├── api_client.py
│   ├── worker.py       # Thread pool untuk panggilan jaringan
│   ├── clipboard.py    # Copy + auto-clear clipboard
│   └── ui/             # Tampilan Tkinter
│       ├── app.py
│       ├── login_view.py
│       └── entries_view.py
├── tests/              # Unit test (pytest + httpx.MockTransport)
├── logs/               # Log server (tidak di-commit)
├── .venv/              # Virtual environment (tidak di-commit)
└── requirements.txt
```

## Catatan Keamanan

- Kata sandi **tidak pernah** ditulis ke disk, log, atau stdout.
- Cookie sesi hanya di memori (`httpx.Client`).
- Hanya koneksi ke `http://127.0.0.1:8000`.
- Clipboard dibersihkan otomatis 30 detik setelah copy (jika isi masih sama).
