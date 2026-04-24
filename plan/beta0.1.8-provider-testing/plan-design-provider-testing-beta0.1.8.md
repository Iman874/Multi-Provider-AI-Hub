# Blueprint: AI Generative Core — Provider Testing (beta0.1.8)

## 1. Visi & Tujuan
Setelah mengimplementasikan berbagai fungsionalitas (generate, stream, embedding, multimodal) untuk dua provider yang berbeda (Ollama dan Gemini), terdapat beberapa kendala stabilitas di mana integrasi mengalami kegagalan pada saat interaksi dengan service. 
Tujuan dari versi **beta0.1.8** ini adalah membangun fondasi pengujian unit (Unit Testing) yang komprehensif, khususnya untuk layer **Provider** (`OllamaProvider` dan `GeminiProvider`). Hal ini akan memastikan setiap fungsi (termasuk *error handling*, timeout, dan parsing response) dapat berjalan konsisten dan tidak rentan rusak oleh perubahan di masa depan.

## 2. Scope Development
- **Setup Testing Environment**: Konfigurasi `pytest`, `pytest-asyncio`, dan pustaka mock (`respx` atau `pytest-httpx` untuk Ollama, serta `unittest.mock` untuk Gemini).
- **OllamaProvider Tests**: Pengujian `generate()`, `stream()`, `embedding()`, dan handling exception (API Error, Connection Error, Timeout).
- **GeminiProvider Tests**: Pengujian isolasi menggunakan mock Google GenAI SDK untuk menguji response sukses, streaming chunks, dan berbagai kemungkinan exception.

## 3. Arsitektur & Desain Test

Pengujian akan difokuskan pada isolasi external API call:
- **Ollama**: Mencegat (intercept) request HTTP yang keluar dari `httpx.AsyncClient` menggunakan `respx` atau `pytest-httpx`. Kita tidak akan memanggil service Ollama asli saat unit test berjalan.
- **Gemini**: Me-mock internal object `genai.Client` untuk menyimulasikan return model dari `client.models.generate_content`, `generate_content_stream`, dan `embed_content`.

### Struktur Direktori Test
```text
tests/
├── conftest.py                   # Global fixtures
├── providers/
│   ├── test_ollama_provider.py   # Test suite untuk Ollama
│   └── test_gemini_provider.py   # Test suite untuk Gemini
```

## 4. Breakdowns (Daftar Task)

### Task 1 — Setup Testing Environment (`task1-setup-testing.md`)
- Menambahkan `pytest`, `pytest-asyncio`, `pytest-mock`, dan `respx` ke `requirements.txt`.
- Membuat `tests/conftest.py` dengan konfigurasi dasar asyncio dan fixture inisialisasi provider.

### Task 2 — OllamaProvider Unit Tests (`task2-test-ollama.md`)
- **Generate**: Memastikan request payload JSON terbuat dengan benar, dan mock response mengembalikan token.
- **Stream**: Memastikan `aiter_lines` dari `httpx` dimock dan parsing format NDJSON Ollama (termasuk edge case broken JSON) berfungsi.
- **Embedding**: Memastikan ekstraksi vector dari payload response `["embeddings"][0]` benar.
- **Exceptions**: Memastikan error koneksi, error timeout, dan HTTP Error dikonversi menjadi custom exception project (e.g. `ProviderTimeoutError`).

### Task 3 — GeminiProvider Unit Tests (`task3-test-gemini.md`)
- **Generate**: Mock return object SDK untuk text generation dan verifikasi output list of parts (Multimodal).
- **Stream**: Mock iterable chunk response dari `generate_content_stream`.
- **Embedding**: Mock return `embed_content` SDK.
- **Exceptions**: Menguji string matching error Gemini (seperti block 404, deadline exceeded, dsb) untuk menerjemahkannya ke error standar kita.

## 5. Timeline & Estimasi
- **Task 1**: Low (30 menit)
- **Task 2**: Medium (60 - 90 menit)
- **Task 3**: Medium (60 - 90 menit)
**Total Estimasi**: ~3 jam

## 6. Acceptance Criteria Global
- Perintah `pytest` berhasil dieksekusi dari *root directory*.
- 100% test pass untuk direktori `tests/providers/`.
- Tidak memerlukan koneksi internet atau service Ollama lokal yang menyala untuk menjalankan unit test (*fully mocked*).
- Coverage pengujian error-handling mencakup minimal status 4xx, 5xx, dan timeout connection.
