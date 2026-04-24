# Task 5 - Unit Tests: GeneratorService Auto Routing

## 1. Judul Task
Tambah unit test untuk auto routing dan fallback di `GeneratorService`

## 2. Deskripsi
Task ini menambahkan test coverage khusus untuk smart routing pada level service. File test baru mengikuti pola folder test repo saat ini, yaitu `tests/services/`. Fokus pengujian ada pada pemilihan target, fallback generate/embedding, dan aturan streaming sebelum serta sesudah first token.

## 3. Tujuan Teknis
- Buat file test baru `tests/services/test_generator_service.py`
- Verifikasi urutan target auto routing sesuai prioritas provider
- Verifikasi provider DOWN dilewati
- Verifikasi fallback `generate()` dan `embedding()` bekerja
- Verifikasi aturan stream sebelum dan sesudah first token
- Verifikasi semua target gagal akan me-raise `AIGatewayError`
- Dokumentasi task langsung mengarahkan ke file test baru di `tests/services/`

## 4. Scope

### Yang dikerjakan
- `tests/services/test_generator_service.py` - file baru untuk auto routing tests

### Yang TIDAK dikerjakan
- End-to-end API tests
- Perubahan provider tests existing
- Dokumentasi `how_to_run.md`

## 5. Langkah Implementasi

### Step 1: Buat file `tests/services/test_generator_service.py`
Ikuti pola test repo saat ini:

- `pytest`
- `pytest.mark.asyncio`
- `AsyncMock` / `MagicMock`
- mock registry, mock providers, dan mock `HealthChecker`

### Step 2: Siapkan fixture dasar
Fixture minimum:

- mock provider `nvidia`
- mock provider `gemini`
- mock provider `ollama`
- mock `ModelRegistry` dengan beberapa `ModelCapability`
- mock `HealthChecker`
- `GeneratorService` yang dibangun dengan dependency tersebut

### Step 3: Tambah test untuk target ordering dan health filtering
Skenario:

1. Semua provider UP -> urutan target `nvidia`, `gemini`, `ollama`
2. `nvidia` DOWN -> urutan target mulai dari `gemini`
3. Request image -> hanya model `supports_image=True`
4. Request stream -> hanya model `supports_streaming=True`
5. Request embedding -> hanya model `supports_embedding=True`

### Step 4: Tambah test generate auto mode
Skenario minimum:

1. Jalur ideal: NVIDIA sukses
2. NVIDIA timeout -> fallback ke Gemini
3. NVIDIA dan Gemini gagal -> fallback ke Ollama
4. Semua target gagal -> `AIGatewayError`

Assert:

- response `provider` dan `model` bukan `"auto"`
- provider yang dipanggil sesuai urutan prioritas

### Step 5: Tambah test embedding auto mode
Skenario minimum:

1. Hanya model embedding yang dicoba
2. Target pertama gagal -> target berikutnya sukses
3. Semua target gagal -> `AIGatewayError`

### Step 6: Tambah test stream auto mode
Skenario minimum:

1. Target pertama gagal sebelum first token -> fallback ke target kedua
2. Target pertama sukses mengirim first token lalu gagal -> exception diteruskan, tidak ada fallback

### Step 7: Dokumentasikan batas chat testing
Tidak perlu menambah test untuk method chat di `GeneratorService` karena flow chat pada repo ini berjalan melalui endpoint chat yang memanggil `GeneratorService.generate()`.

## 6. Output yang Diharapkan

Contoh struktur file:

```python
async def test_generate_auto_falls_back_to_gemini(...):
    ...

async def test_stream_auto_does_not_fallback_after_first_token(...):
    ...
```

Contoh assert:

```python
assert response.provider == "gemini"
assert response.model != "auto"
```

## 7. Dependencies
- Task 1 (Schemas & Enum Auto Mode)
- Task 2 (Priority Selection & Health Integration)
- Task 3 (Fallback Loop: Generate & Chat Flow)
- Task 4 (Fallback Loop: Stream & Embedding)

## 8. Acceptance Criteria
- [x] File baru `tests/services/test_generator_service.py` didefinisikan dalam plan
- [x] Ada test untuk priority ordering dan health filtering
- [x] Ada test untuk fallback `generate()`
- [x] Ada test untuk fallback `embedding()`
- [x] Ada test untuk aturan fallback `stream()` sebelum first token
- [x] Ada test yang memastikan tidak ada fallback setelah first token
- [x] Dokumen task mengarahkan ke file test baru `tests/services/test_generator_service.py`

## 9. Estimasi
Medium (~1 jam)
