# Task 6 - Documentation: Auto Mode

## 1. Judul Task
Tambah dokumentasi penggunaan smart routing auto mode di `how_to_run.md`

## 2. Deskripsi
Task ini menambahkan panduan praktis untuk frontend atau API consumer agar bisa memakai `provider="auto"` dan `model="auto"` tanpa harus memahami detail fallback di internal gateway. Dokumentasi harus menjelaskan kontrak request, contoh response, dan batas perilaku streaming secara singkat.

## 3. Tujuan Teknis
- Tambah section baru di `how_to_run.md` untuk smart routing auto mode
- Jelaskan kontrak request `provider="auto"` dan `model="auto"`
- Berikan contoh request `POST /api/v1/generate`
- Tampilkan contoh response yang menonjolkan provider/model aktual
- Tambahkan catatan singkat untuk chat, embedding, dan streaming behavior

## 4. Scope

### Yang dikerjakan
- `how_to_run.md` - tambah dokumentasi auto mode

### Yang TIDAK dikerjakan
- Perubahan Swagger schema
- Perubahan dokumentasi provider lain
- Unit tests

## 5. Langkah Implementasi

### Step 1: Tambah section baru di `how_to_run.md`
Gunakan judul yang jelas, misalnya:

```md
Smart Routing & Auto Fallback
```

### Step 2: Jelaskan kontrak request
Tuliskan aturan berikut secara eksplisit:

- kirim `provider: "auto"` untuk meminta gateway memilih provider
- gunakan `model: "auto"` agar gateway memilih model otomatis
- response sukses akan mengembalikan `provider` dan `model` aktual yang dipakai

### Step 3: Tambah contoh `curl` untuk generate
Contoh request:

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "auto",
    "model": "auto",
    "input": "Ringkas logika fallback ini dalam 3 poin."
  }'
```

### Step 4: Tambah contoh response generate
Contoh response harus menonjolkan bahwa provider/model final bukan `"auto"`:

```json
{
  "output": "...",
  "provider": "gemini",
  "model": "gemini-2.5-pro",
  "usage": {
    "prompt_tokens": 120,
    "completion_tokens": 64,
    "total_tokens": 184
  },
  "metadata": {
    "cached": false
  }
}
```

### Step 5: Tambah catatan singkat untuk endpoint lain
Tambahkan catatan ringkas:

- `/chat` mengikuti auto mode yang sama karena endpoint chat memakai `GeneratorService.generate()`
- `/embedding` mendukung `provider="auto"` dan memilih model embedding yang tersedia
- `/stream` mendukung auto mode, tetapi fallback hanya bisa terjadi sebelum token pertama dikirim

### Step 6: Hindari klaim di luar scope
Dokumentasi tidak boleh menjanjikan perubahan pada:

- metadata session history chat
- load balancing paralel
- fallback stream setelah response SSE dimulai

## 6. Output yang Diharapkan

Potongan dokumentasi baru di `how_to_run.md`:

```md
Smart Routing & Auto Fallback

Gunakan `provider: "auto"` dan `model: "auto"` agar gateway memilih target terbaik secara otomatis.

...
```

## 7. Dependencies
- Task 1 (Schemas & Enum Auto Mode)
- Task 3 (Fallback Loop: Generate & Chat Flow)
- Task 4 (Fallback Loop: Stream & Embedding)

## 8. Acceptance Criteria
- [x] `how_to_run.md` memiliki section baru untuk auto mode
- [x] Ada contoh request `POST /api/v1/generate` dengan `provider="auto"` dan `model="auto"`
- [x] Ada contoh response yang menunjukkan provider/model aktual
- [x] Ada catatan untuk chat, embedding, dan streaming
- [x] Dokumentasi tidak menjanjikan perubahan pada session history metadata
- [x] Dokumen task tetap mengikuti template standar repo

## 9. Estimasi
Low (~15 menit)
