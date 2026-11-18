# PROJECT: Antarmuka Desktop pwd-vault (pwd-vault-gui)

---

# 1. RULES (wajib dipatuhi)

## Teknologi

- Lubuntu, Python 3.12, folder proyek ini terpisah dari backend, dengan virtual environment sendiri di `.venv`
- GUI memakai Tkinter dengan ttk (modul bawaan Python). Paket sistem `python3-tk` saya pasang sendiri. Jangan memasang PyQt, PySide, Kivy, Electron, atau toolkit lain
- Klien HTTP: `httpx` (mode sinkron, dipanggil dari thread latar)
- Library yang sudah disetujui: `httpx`, `pytest`. Library lain: tanyakan dulu sebelum dipasang
- Backend ada di `~/Proyek/pwd-vault`. Dari proyek ini backend hanya boleh dijalankan sebagai proses dan dipanggil lewat API. Jangan membaca, menulis, atau mengubah berkas di folder backend, termasuk `.env`, `data/vault.db`, dan kodenya. Memeriksa keberadaan `.venv/bin/python` backend dengan `Path.exists()` diperbolehkan
- Perintah menjalankan GUI: `python -m vaultgui`
- Perintah yang dijalankan GUI untuk backend (setara dengan `uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000`), dengan `cwd` folder backend dan Python dari `.venv` backend:
  `[<backend>/.venv/bin/python, "-m", "uvicorn", "app.main:create_app", "--factory", "--host", "127.0.0.1", "--port", "8000"]`
- Proses dijalankan dengan argumen berbentuk list, tanpa `shell=True`

## Cara bekerja

- Di awal setiap tahap, jelaskan rencana dalam 3-5 kalimat, lalu tunggu kata "lanjut" dari saya sebelum menulis file
- Kerjakan satu tahap saja per giliran, sesuai bagian STATUS
- Tulis atau ubah file hanya di dalam folder proyek ini, dan jangan ubah file yang tidak relevan dengan tahap aktif
- Setelah menulis kode, jalankan `pytest` dan laporkan hasil sebenarnya (lulus atau gagal). Jangan menyatakan berhasil sebelum tes dijalankan
- Untuk bagian UI yang tidak bisa dites otomatis, tulis langkah uji manual singkat yang akan saya jalankan sendiri
- Perintah shell yang mengubah sistem (instal paket, hapus file, pindah file) tampilkan dulu dan minta persetujuan saya. Jangan pakai `sudo`
- Jika ada pilihan desain, tawarkan 2 opsi beserta trade-off, lalu tunggu keputusan saya
- Jika permintaan kurang jelas atau bertentangan dengan SPEC, tanyakan dulu
- Di akhir tahap, ringkas hasilnya dan usulkan pembaruan untuk ARCHITECTURE dan STATUS. Ubah file ini hanya setelah saya menyatakan tahap lulus. Jangan menambah library atau berkas di luar rencana tanpa izin

## Keamanan dan kualitas

- Password (akun login maupun entri) tidak pernah ditulis ke disk, log, `print`, atau pesan error. Jangan mencetak isi respons API yang memuat password
- Cookie sesi hanya disimpan di memori (objek `httpx.Client`), tidak pernah ke berkas
- Alamat server hanya `http://127.0.0.1:<port>`. Tolak alamat lain
- GUI tidak boleh membaca `.env` atau `data/vault.db` backend, dan tidak boleh memakai `sqlite3` secara langsung
- Semua panggilan jaringan berjalan di thread latar. Widget Tkinter hanya disentuh dari thread utama
- Tampilan password hasil reveal disembunyikan lagi otomatis setelah 15 detik. Hasil salin ke clipboard dihapus otomatis setelah 30 detik, hanya bila clipboard masih berisi nilai yang sama
- Auto-lock: 5 menit tanpa aktivitas, GUI memanggil logout ke server, mengosongkan semua data dari widget, dan kembali ke layar login
- Respons 401 di layar mana pun mengembalikan pengguna ke layar login dengan pesan jelas. Respons 429 menampilkan pesan bahwa login dikunci sementara
- URL entri hanya dibuka di browser bila skemanya `http` atau `https`
- Server hanya dihentikan oleh GUI bila GUI sendiri yang memulainya. Saat jendela ditutup (dan lewat `atexit`), hentikan proses dengan `terminate()`, tunggu 5 detik, lalu `kill()` bila perlu
- Output server diarahkan ke `logs/server.log`, bukan PIPE yang tidak dibaca (bisa membuat proses macet)
- Sebelum menganggap proses di port 8000 adalah pwd-vault, verifikasi lewat `GET /openapi.json` (`info.title == "pwd-vault"`), bukan hanya `/health`
- `.venv/`, `logs/`, `__pycache__/`, dan `.pytest_cache/` wajib masuk `.gitignore`
- Tulis test pytest untuk logika non-UI (`config`, `server_manager`, `api_client`, `worker`, logika clipboard). Tes memakai `httpx.MockTransport`, proses palsu, atau server HTTP sementara di port acak. Tes tidak boleh memakai backend asli atau database asli. Data uji harus palsu (contoh: `password-palsu-123`)
- Pesan error untuk pengguna harus jelas, tanpa stack trace

---

# 2. SPEC (apa yang dibangun)

## Tujuan

Aplikasi desktop ringan (Tkinter) sebagai antarmuka untuk backend pwd-vault yang sudah selesai, sekaligus menjalankan dan menghentikan backend itu. Dipakai satu pengguna di komputer sendiri. Proyek ini juga sarana saya belajar memakai Hermes Agent.

## Fitur

1. Panel server: status (berjalan atau berhenti), tombol Mulai dan Hentikan. GUI memulai backend otomatis saat dibuka bila belum berjalan
2. Login dan logout. Password disamarkan di kolom input. Layar login memuat petunjuk bahwa akun dibuat lewat skrip CLI di folder backend
3. Daftar entri (tanpa password) dan pencarian berdasarkan provider atau username
4. Tambah, ubah, dan hapus entri. Hapus meminta konfirmasi
5. Tampilkan password (otomatis tersembunyi lagi) dan salin ke clipboard (otomatis terhapus)
6. Pembuat password acak lewat endpoint backend, dengan pilihan panjang dan jenis karakter, serta tombol untuk memakai hasilnya di formulir
7. Buka URL entri di browser (hanya http dan https)
8. Auto-lock saat tidak ada aktivitas
9. Penanganan error yang ramah: server mati, port dipakai proses lain, sesi berakhir (401), login terkunci (429), input tidak valid (422)

## Di luar cakupan (jangan dikerjakan)

- Mengubah kode backend
- Membaca database atau `.env` backend secara langsung
- Registrasi atau multi-pengguna dari GUI
- Fitur "ingat saya" atau menyimpan password login
- Impor dan ekspor data, sinkronisasi cloud
- Koneksi ke alamat selain 127.0.0.1
- Ikon system tray, installer, atau packaging (PyInstaller dan sejenisnya)

---

# 3. ARCHITECTURE (bagaimana disusun)

## Struktur folder

```
pwd-vault-gui/
├── AGENTS.md
├── .gitignore
├── pytest.ini
├── requirements.txt
├── vaultgui/
│   ├── __init__.py
│   ├── __main__.py          # entry point: python -m vaultgui
│   ├── config.py            # host, port, path backend, batas waktu (bisa di-override env var)
│   ├── server_manager.py    # cek, mulai, hentikan backend (tanpa Tkinter)
│   ├── api_client.py        # pembungkus httpx ke API (tanpa Tkinter)
│   ├── worker.py            # panggilan jaringan di thread latar, hasil ke UI
│   ├── clipboard.py         # salin dan hapus otomatis
│   └── ui/
│       ├── app.py           # jendela utama, perpindahan layar, auto-lock
│       ├── login_view.py
│       ├── entries_view.py  # daftar dan pencarian
│       ├── entry_form.py    # tambah dan ubah
│       ├── entry_form.py    # tambah dan ubah
│       └── generator_dialog.py
├── logs/
│   └── server.log           # tidak di-commit
└── tests/
```

## Backend yang dipakai

- Folder: `~/Proyek/pwd-vault`, Python di `.venv/bin/python`
- Alamat: `http://127.0.0.1:8000`
- Sesi: cookie `pwd_vault_session`, kedaluwarsa setelah 1 jam tanpa aktivitas, `SameSite=Strict`
- Error API berbentuk `{"detail": ...}`. Kode penting: 401 (belum login), 404, 422 (validasi, `detail` berupa daftar), 429 (login terkunci 5 menit)

## Kontrak API (ringkas)

- `GET /health`, `GET /openapi.json`
- `POST /auth/login` (form: `username`, `password`), `POST /auth/logout`, `GET /auth/saya`
- `GET /entri` (parameter `q` opsional), `POST /entri`, `GET /entri/{id}`, `PUT /entri/{id}`, `DELETE /entri/{id}`
- `GET /entri/{id}/password` (membalas `{"id", "password"}`)
- `GET /alat/password-acak` (parameter `panjang` 8-128, `huruf_kecil`, `huruf_besar`, `angka`, `simbol`)
- Field entri: username, password, email, provider, url, keterangan. Otomatis: id, dibuat_pada, diubah_pada

## Keputusan desain

- 2026-11-17: GUI dibuat sebagai proyek terpisah dari backend supaya backend yang sudah selesai tidak ikut berubah, dan supaya Hermes bekerja di folder yang jelas
- 2026-11-17: Tkinter dengan ttk dipilih karena bawaan Python, ringan, dan tanpa library tambahan. Qt dan sejenisnya terlalu berat untuk kebutuhan ini
- 2026-11-17: Backend dijalankan sebagai proses terpisah memakai Python dari `.venv` backend, sehingga GUI tidak perlu memasang FastAPI atau uvicorn
- 2026-11-17: Port 8000 sesuai permintaan. Catatan: AGENTS.md backend menyebut 8001. Port disimpan sebagai satu konstanta di `config.py`
- 2026-11-18: Saat ubah entri, form tidak menampilkan password lama. Bila kolom password dikosongkan, GUI memanggil `GET /entri/{id}/password` sekali untuk mempertahankan password lama lalu mengirim PUT lengkap. Alasan: PUT diasumsikan penggantian penuh, sedangkan menampilkan password lama adalah wewenang Tahap 8.

## Keputusan yang masih terbuka (tawarkan 2 opsi saat tahapnya tiba)

- Pola komunikasi thread latar ke UI (misalnya `threading` dengan `queue` dan polling `after()`, atau `concurrent.futures` dengan callback `after()`). Dibahas di Tahap 4
- Perilaku bila port 8000 sudah dipakai: server pwd-vault yang sudah berjalan dipakai ulang tanpa dimiliki GUI, atau GUI menolak dan meminta saya menghentikannya. Dibahas di Tahap 2

---

# 4. PLAN (urutan kerja)

- [x] Tahap 1: folder proyek, venv, `requirements.txt`, `.gitignore`, `pytest.ini`, `git init`, `python -m vaultgui` membuka jendela ttk kosong, satu test untuk `config.py`. Periksa dulu `python3 -c "import tkinter"`; bila gagal, minta saya memasang `python3-tk`
- [x] Tahap 2: `server_manager.py` (cek identitas lewat `/openapi.json`, mulai, hentikan, deteksi port terpakai, log ke berkas) beserta test
- [x] Tahap 3: `api_client.py` (login, logout, saya, CRUD entri, pencarian, reveal, generator) dengan exception khusus, beserta test `MockTransport`
- [x] Tahap 4: `worker.py`, jendela utama, dan panel server (status, mulai, hentikan)
- [x] Tahap 5: layar login dan logout, penanganan 401 dan 429, auto-lock
- [x] Tahap 6: daftar entri dan pencarian
- [x] Tahap 7: form tambah dan ubah, hapus dengan konfirmasi
- [x] Tahap 8: tampilkan dan salin password (auto-hide, auto-clear), buka URL
- [x] Tahap 9: dialog pembuat password acak
- [ ] Tahap 10: tinjauan akhir (tidak ada rahasia di kode atau log, tidak ada akses ke berkas backend, tidak ada proses server yatim saat GUI ditutup atau dimatikan paksa, uji manual lengkap)

---

# 5. STATUS (kondisi sekarang)

- **Tahap aktif:** 10
- **Terakhir selesai:** 9
- **Masalah terbuka:** pengerasan kecil backend (Tahap 10 di proyek backend) belum dikerjakan. Tidak memblokir pengembangan GUI
- **Yang ingin dikerjakan sekarang:** Tahap 10, tinjauan akhir dan finalisasi.

---

# 6. CARA MEMULAI PERCAKAPAN

Baca `AGENTS.md` di folder ini. Patuhi bagian RULES. Kerjakan hanya tahap yang tertulis di STATUS. Sebelum menulis file, jelaskan rencana dan tunggu persetujuan saya. Jika ada yang tidak jelas atau bertentangan dengan SPEC, tanyakan dulu.
