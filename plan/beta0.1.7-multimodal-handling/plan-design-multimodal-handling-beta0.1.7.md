# Multimodal Handling — beta0.1.7

> **Versi**: beta0.1.7  
> **Modul**: Image Input Support (Ollama & Gemini), Image Utilities  
> **Status**: 📋 Planned  
> **Dependency**: beta0.1.5 (Streaming Adapter)  
> **Referensi Blueprint**: `02-provider-layer.md`, `04-api-layer.md`

---

## 1. Latar Belakang

Sampai beta0.1.6, semua fitur hanya menerima **text input**. Banyak use case SaaS modern membutuhkan kemampuan multimodal — misalnya analisis gambar, OCR, visual QA, dan content generation dari referensi visual.

Tantangan utama: Ollama dan Gemini menerima image dalam format yang **berbeda**:
- **Ollama**: Array of base64 strings (tanpa data URI prefix)
- **Gemini**: `Part.from_data(data=bytes, mime_type="image/jpeg")`

Modul ini membangun **image abstraction layer** agar user cukup mengirim `images: [...]` tanpa perlu tahu perbedaan internal antar provider.

### Masalah yang Diselesaikan

- Belum bisa kirim image ke AI → use case visual terbatas
- Dua provider butuh format image berbeda → perlu normalisasi di provider layer
- Belum ada utilitas image processing → base64, URL download, MIME detection
- `supports_image()` masih hardcoded false → perlu diaktifkan

### Kaitan dengan Sistem

- Update `OllamaProvider.generate()` dan `stream()` — tambah image handling
- Update `GeminiProvider.generate()` dan `stream()` — tambah native multimodal
- Buat `app/utils/image.py` — image processing utilities
- `ModelRegistry` sudah track `supports_image` flag → aktifkan validasi

---

## 2. Tujuan

| # | Outcome | Measurable |
|---|---|---|
| 1 | Ollama vision berfungsi | Generate text dari image + prompt via Ollama |
| 2 | Gemini vision berfungsi | Generate text dari image + prompt via Gemini |
| 3 | Format input seragam | User kirim `images: [base64]`, tanpa perlu tahu provider |
| 4 | Image utilities tersedia | Base64 encode/decode, URL→base64, MIME detection |
| 5 | Capability validation aktif | Model non-vision + images → 400 error |
| 6 | Streaming + image berfungsi | POST /stream dengan image → stream response |

---

## 3. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/utils/image.py` — image processing helper
- Update `OllamaProvider.generate()` — tambah image support
- Update `OllamaProvider.stream()` — tambah image support
- Update `GeminiProvider.generate()` — tambah native multimodal
- Update `GeminiProvider.stream()` — tambah native multimodal
- Update `supports_image()` di kedua provider → return True untuk vision models
- Validasi di `GeneratorService` sudah berfungsi (code ada di beta0.1.3)

### ❌ Yang Tidak Dikerjakan

- Image generation (text → image) → future version
- Multiple image analysis → support basic, no advanced
- Image URL auto-download → basic support only
- Video input → future version

---

## 4. Breakdown Task

### Task 1: Image Utilities

- [ ] Implementasi `app/utils/image.py`
  - `strip_data_uri(base64_str) -> str`
    - Remove `data:image/...;base64,` prefix jika ada
    - Return pure base64 string
  - `detect_mime_type(base64_str) -> str`
    - Detect dari data URI prefix, atau dari magic bytes
    - Default: `image/jpeg`
  - `base64_to_bytes(base64_str) -> bytes`
    - Strip data URI, decode base64 → raw bytes
  - `validate_image(base64_str) -> bool`
    - Cek apakah string valid base64 image
    - Cek ukuran tidak melebihi limit (e.g. 20MB)
  - `url_to_base64(url) -> str` (optional)
    - Download image dari URL via httpx
    - Convert ke base64 string

### Task 2: OllamaProvider — Image Support

- [ ] Update `generate()` di `app/providers/ollama.py`
  - Jika `images` ada:
    - Strip data URI prefix dari setiap image
    - Tambah `"images": [base64_str, ...]` ke payload
  - Existing text-only flow tetap sama

- [ ] Update `stream()` di `app/providers/ollama.py`
  - Sama: tambah `"images"` ke payload jika ada

- [ ] Update `supports_image()`:
  - Return True (capability check dilakukan di registry level)

### Task 3: GeminiProvider — Multimodal

- [ ] Update `generate()` di `app/providers/gemini.py`
  - Jika `images` ada:
    - Convert setiap image: base64 → bytes
    - Detect MIME type
    - Build contents: `[prompt, Part.from_data(data=bytes, mime_type=mime)]`
  - Jika tidak ada images → text only (existing flow)

- [ ] Update `stream()` di `app/providers/gemini.py`
  - Sama: tambah image parts ke contents jika ada

- [ ] Update `supports_image()`:
  - Return True

### Task 4: Integration Validation

- [ ] Pastikan `GeneratorService.generate()` sudah handle image validation:
  - `request.images` ada + `model_info.supports_image == False` → `ModelCapabilityError`
  - `request.images` ada + `model_info.supports_image == True` → proceed
  - `request.images` kosong/None → text only (existing flow)
- [ ] Pastikan `GeneratorService.stream()` juga pass images ke provider

---

## 5. Design Teknis

### File Baru

| File | Layer | Fungsi |
|---|---|---|
| `app/utils/image.py` | Utils | Image processing helpers |

### File yang Dimodifikasi

| File | Perubahan |
|---|---|
| `app/providers/ollama.py` | generate() + stream() + supports_image() |
| `app/providers/gemini.py` | generate() + stream() + supports_image() |

### Flow: Multimodal Generate (Ollama)

```
Client → POST /api/v1/generate
  Body: { 
    provider: "ollama", 
    model: "llama3.2-vision", 
    input: "What's in this image?", 
    images: ["data:image/jpeg;base64,/9j/4AAQ..."] 
  }

→ service.generate(request)
  → registry.get_model("ollama", "llama3.2-vision")
    → supports_image: true ✓
  → provider.generate("llama3.2-vision", prompt, images)
    → strip_data_uri(image) → pure base64
    → POST /api/generate: { model, prompt, images: [base64] }
    ← { response: "This image shows..." }
  ← GenerateResponse(output="This image shows...")
```

### Flow: Multimodal Generate (Gemini)

```
Client → POST /api/v1/generate
  Body: { 
    provider: "gemini", 
    model: "gemini-2.0-flash", 
    input: "Describe this image", 
    images: ["/9j/4AAQ..."] 
  }

→ service.generate(request)
  → provider.generate("gemini-2.0-flash", prompt, images)
    → base64_to_bytes(image) → raw bytes
    → detect_mime_type → "image/jpeg"
    → contents = ["Describe this image", Part.from_data(bytes, "image/jpeg")]
    → client.models.generate_content(model, contents)
    ← response.text = "The image depicts..."
  ← GenerateResponse(output="The image depicts...")
```

### Image Normalization Flow

```
User sends images: ["data:image/png;base64,ABC123..."]
                            │
                ┌───────────┴───────────┐
                ▼                       ▼
         OllamaProvider          GeminiProvider
         strip prefix            base64 → bytes
         → "ABC123..."          → raw bytes + mime
         payload.images = [...]  Part.from_data(...)
```

---

## 6. Dampak ke Sistem

### Bagian yang Berubah

- Kedua provider: generate() dan stream() diperkaya dengan image handling
- Utilitas baru: `app/utils/image.py`
- Tidak ada perubahan di endpoint, service, atau schema

### Risiko

| Risiko | Mitigasi |
|---|---|
| Image terlalu besar → timeout | Validate ukuran di image utils, reject > 20MB |
| Invalid base64 string | validate_image() sebelum kirim ke provider |
| MIME type salah | Detect dari magic bytes, fallback ke jpeg |
| Ollama vision model belum di-pull | Error jelas dari Ollama → ProviderAPIError |

### Dependency

| Depends On | Depended By |
|---|---|
| beta0.1.3 (Ollama generate) | Future: OCR SaaS |
| beta0.1.4 (Gemini generate) | Future: Visual QA |
| beta0.1.5 (Streaming) | Future: Image-to-text streaming |

---

## 7. Definition of Done

- [ ] `POST /generate` dengan Ollama vision model + image → describe image
- [ ] `POST /generate` dengan Gemini + image → describe image
- [ ] `POST /stream` dengan image → streaming description
- [ ] Data URI prefix di-strip otomatis untuk Ollama
- [ ] Base64 di-convert ke bytes untuk Gemini
- [ ] Model non-vision + images → 400 error `CAPABILITY_NOT_SUPPORTED`
- [ ] Image utilities berfungsi: strip, detect mime, validate, convert
- [ ] Tidak ada perubahan di endpoint code atau schema

---

## Referensi Blueprint

- [02-provider-layer.md](../bluprint/02-provider-layer.md) — Image handling per provider
- [04-api-layer.md](../bluprint/04-api-layer.md) — Multimodal request examples
