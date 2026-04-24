# Task 3 - Fallback Loop: Generate & Chat Flow

## 1. Judul Task
Implement fallback loop auto mode pada `generate()` dan pastikan flow chat existing ikut memakai jalur tersebut

## 2. Deskripsi
Task ini mengaktifkan fallback otomatis untuk operasi sinkronus berbasis text generation. Implementasi utamanya ada di `GeneratorService.generate()`. Flow chat tidak membuat method service baru; endpoint chat existing tetap membangun `GenerateRequest` dan memanggil `GeneratorService.generate()`, sehingga auto routing untuk chat terjadi melalui jalur yang sama.

## 3. Tujuan Teknis
- `GeneratorService.generate()` mendukung `provider="auto"`
- Retry hanya dilakukan untuk error provider yang bersifat retryable
- Response sukses selalu mengembalikan provider/model aktual yang benar-benar menjawab request
- Flow chat di `app/api/endpoints/chat.py` tetap memakai `GeneratorService.generate()`
- Task ini tidak menambah method chat baru di `GeneratorService`
- Metadata session dan `ChatHistoryResponse` tidak diubah pada task ini

## 4. Scope

### Yang dikerjakan
- `app/services/generator.py` - auto routing dan fallback loop untuk `generate()`
- Verifikasi flow existing di `app/api/endpoints/chat.py` agar tetap menggunakan `GenerateRequest -> GeneratorService.generate()`

### Yang TIDAK dikerjakan
- Perubahan struktur `ChatHistoryResponse`
- Perubahan metadata provider/model yang disimpan di `SessionManager`
- Fallback loop untuk `stream()` dan `embedding()`
- Unit tests

## 5. Langkah Implementasi

### Step 1: Refactor flow explicit provider menjadi helper private
Ekstrak logika generate existing ke helper private, misalnya:

```python
async def _generate_single(self, request: GenerateRequest) -> GenerateResponse:
    ...
```

Helper ini harus tetap menangani:

- provider resolution
- model lookup
- capability validation
- cache lookup
- provider invocation
- cache write
- response normalization

### Step 2: Jadikan `generate()` sebagai dispatcher
`generate()` memutuskan dua jalur:

1. Jika `request.provider != ProviderEnum.AUTO` -> panggil `_generate_single(request)`
2. Jika `request.provider == ProviderEnum.AUTO` -> jalankan fallback loop

### Step 3: Implement fallback loop untuk auto mode
Ambil target dari:

```python
targets = self._get_auto_routing_targets(
    requires_image=bool(request.images),
    is_embedding=False,
    requires_streaming=False,
)
```

Untuk setiap target:

1. Buat `GenerateRequest` baru dengan `provider=target.provider`, `model=target.name`, `input=request.input`, `images=request.images`
2. Panggil `_generate_single(target_request)`
3. Return response pertama yang sukses

### Step 4: Tangkap hanya error retryable
Exception yang ditangkap dan memicu fallback:

- `ProviderAPIError`
- `ProviderTimeoutError`
- `ProviderConnectionError`
- `AllKeysExhaustedError`

Gunakan warning log yang konsisten:

```python
logger.warning(
    "Auto-fallback generate failed: provider={provider}, model={model}, error={error}",
    ...,
)
```

Error non-retryable seperti `ProviderNotFoundError` atau `ModelCapabilityError` tidak boleh disembunyikan.

### Step 5: Raise error jika semua target gagal
Setelah loop habis, raise:

```python
AIGatewayError("All auto-routing targets failed.")
```

### Step 6: Sinkronkan dengan flow chat existing
`app/api/endpoints/chat.py` tetap memakai pola:

```python
generate_request = GenerateRequest(
    provider=request.provider,
    model=request.model,
    input=prompt,
)
result = await generator.generate(generate_request)
```

Karena itu:

- auto routing untuk chat aktif otomatis setelah task ini selesai
- `ChatResponse.provider` dan `ChatResponse.model` tetap diisi dari `result`
- task ini tidak menambah method chat baru di `GeneratorService`

## 6. Output yang Diharapkan

Generate auto mode:

```python
response = await service.generate(
    GenerateRequest(provider="auto", model="auto", input="Hello")
)
assert response.provider in {"nvidia", "gemini", "ollama"}
assert response.model != "auto"
```

Chat flow tetap valid:

```python
result = await generator.generate(generate_request_from_chat_endpoint)
assert result.provider in {"nvidia", "gemini", "ollama"}
```

## 7. Dependencies
- Task 1 (Schemas & Enum Auto Mode)
- Task 2 (Priority Selection & Health Integration)

## 8. Acceptance Criteria
- [x] `GeneratorService.generate()` mendukung `provider="auto"`
- [x] Flow explicit provider tetap memakai jalur validasi existing
- [x] Fallback hanya terjadi untuk `ProviderAPIError`, `ProviderTimeoutError`, `ProviderConnectionError`, dan `AllKeysExhaustedError`
- [x] Response sukses mengembalikan provider/model aktual, bukan `"auto"`
- [x] Semua target gagal me-raise `AIGatewayError`
- [x] Dokumen task tidak lagi menginstruksikan penambahan method chat baru di `GeneratorService`
- [x] Flow chat tetap dinyatakan melalui `app/api/endpoints/chat.py`

## 9. Estimasi
Medium (~45 menit)
