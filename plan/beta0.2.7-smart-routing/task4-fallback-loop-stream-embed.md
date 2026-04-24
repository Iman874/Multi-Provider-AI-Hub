# Task 4 - Fallback Loop: Stream & Embedding

## 1. Judul Task
Implement fallback loop auto mode pada `stream()` dan `embedding()` dengan aturan streaming yang presisi

## 2. Deskripsi
Task ini menyelesaikan auto routing untuk operation non-chat yang belum tercakup di Task 3. `embedding()` menggunakan pola fallback penuh seperti generate. `stream()` membutuhkan aturan khusus: fallback hanya boleh terjadi sebelum token pertama berhasil dikirim ke client.

## 3. Tujuan Teknis
- `GeneratorService.embedding()` mendukung `provider="auto"`
- `GeneratorService.stream()` mendukung `provider="auto"`
- Filtering stream memakai capability `supports_streaming`
- Fallback streaming hanya boleh terjadi sebelum first token
- Setelah stream berjalan, error diteruskan dan tidak berpindah provider
- Endpoint SSE existing tetap kompatibel dengan behavior baru

## 4. Scope

### Yang dikerjakan
- `app/services/generator.py` - auto routing untuk `stream()` dan `embedding()`
- Kompatibilitas flow existing pada `app/api/endpoints/stream.py`

### Yang TIDAK dikerjakan
- Perubahan format SSE response
- Perubahan response schema generate/chat
- Unit tests
- Dokumentasi `how_to_run.md`

## 5. Langkah Implementasi

### Step 1: Refactor flow explicit embedding ke helper private
Ekstrak logika existing embedding ke helper private, misalnya:

```python
async def _embedding_single(self, request: EmbeddingRequest) -> EmbeddingResponse:
    ...
```

Helper ini harus mempertahankan:

- provider resolution
- model lookup
- capability validation
- cache lookup
- provider invocation
- cache write
- response normalization

### Step 2: Tambah auto routing pada `embedding()`
Jika `request.provider != ProviderEnum.AUTO`, panggil `_embedding_single(request)`.

Jika auto mode:

```python
targets = self._get_auto_routing_targets(
    is_embedding=True,
    requires_streaming=False,
)
```

Untuk setiap target:

1. Buat `EmbeddingRequest` baru dengan provider/model aktual target
2. Panggil `_embedding_single(target_request)`
3. Return response pertama yang sukses

Tangkap exception retryable yang sama seperti Task 3:

- `ProviderAPIError`
- `ProviderTimeoutError`
- `ProviderConnectionError`
- `AllKeysExhaustedError`

### Step 3: Refactor flow explicit stream ke helper private
Ekstrak logika existing stream ke helper private, misalnya:

```python
async def _stream_single(
    self,
    request: StreamRequest,
) -> AsyncGenerator[str, None]:
    ...
```

Helper ini tetap menjalankan validasi provider/model/capability sebelum token pertama dihasilkan.

### Step 4: Implement auto routing pada `stream()`
Ambil target dengan capability filter:

```python
targets = self._get_auto_routing_targets(
    requires_image=bool(request.images),
    is_embedding=False,
    requires_streaming=True,
)
```

Untuk tiap target:

1. Buat `StreamRequest` baru dengan provider/model aktual
2. Panggil `_stream_single(target_request)` untuk memperoleh async iterator
3. Coba ambil token pertama dengan `await anext(iterator)`
4. Jika error retryable terjadi sebelum token pertama, log warning dan lanjut ke target berikutnya
5. Jika token pertama berhasil diperoleh, yield token itu lalu teruskan sisa iterator sampai selesai

### Step 5: Jangan fallback setelah stream dimulai
Setelah token pertama sukses di-yield:

- jika iterator berikutnya melempar exception, exception dinaikkan kembali
- jangan mencoba target berikutnya
- biarkan `app/api/endpoints/stream.py` menangani flow error SSE yang sudah ada

### Step 6: Raise error jika semua target gagal sebelum first token
Jika semua target gagal sebelum ada token pertama, raise:

```python
AIGatewayError("All auto-routing targets failed.")
```

## 6. Output yang Diharapkan

Embedding auto mode:

```python
response = await service.embedding(
    EmbeddingRequest(provider="auto", model="auto", input="embed this")
)
assert response.provider in {"nvidia", "gemini", "ollama"}
assert response.model != "auto"
```

Streaming auto mode:

```python
chunks = []
async for token in service.stream(
    StreamRequest(provider="auto", model="auto", input="Count to three")
):
    chunks.append(token)

assert len(chunks) > 0
```

## 7. Dependencies
- Task 2 (Priority Selection & Health Integration)
- Task 3 (Fallback Loop: Generate & Chat Flow)

## 8. Acceptance Criteria
- [x] `GeneratorService.embedding()` mendukung `provider="auto"`
- [x] `GeneratorService.stream()` mendukung `provider="auto"`
- [x] Stream filtering memakai `supports_streaming=True`
- [x] Fallback streaming hanya dilakukan sebelum first token
- [x] Error setelah first token tidak memicu perpindahan provider
- [x] Semua target gagal sebelum first token me-raise `AIGatewayError`
- [x] Response embedding mengembalikan provider/model aktual yang sukses

## 9. Estimasi
Medium (~45 menit)
