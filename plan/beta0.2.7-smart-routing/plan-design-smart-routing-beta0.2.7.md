# Plan-Design: Smart Routing & Fallback - beta0.2.7

> **Version**: beta0.2.7  
> **Module**: Smart Routing & Auto Fallback  
> **Status**: Plan  
> **Depends On**: beta0.2.6  
> **Created**: 2026-04-24

---

## 1. Latar Belakang

### Apa itu Smart Routing & Fallback?

Saat ini client masih harus menentukan provider dan model secara eksplisit pada setiap request, misalnya `provider="nvidia"` dan `model="meta/llama-3.3-70b-instruct"`. Kontrak ini membuat frontend ikut menanggung keputusan routing yang seharusnya menjadi tanggung jawab gateway.

Masalah muncul saat provider target mengalami timeout, rate limit, atau status DOWN. Dalam kondisi tersebut request langsung gagal walaupun provider lain sebenarnya masih tersedia dan mampu menangani capability yang sama.

Smart Routing menambahkan mode `auto` agar gateway dapat:

1. Menerima `provider="auto"` dan `model="auto"` dari client.
2. Memilih model terbaik berdasarkan capability request dan urutan prioritas provider.
3. Melewati provider yang sedang DOWN berdasarkan `HealthChecker`.
4. Melakukan fallback otomatis ke target berikutnya saat provider cloud gagal.

### Fokus Version Ini

Goal:
1. Menambah dukungan `auto` pada request schema.
2. Menambah helper seleksi target auto routing di `GeneratorService`.
3. Mengimplementasikan fallback loop untuk `generate()`, `stream()`, dan `embedding()`.
4. Memastikan flow chat ikut mendapatkan auto routing melalui endpoint `app/api/endpoints/chat.py` tanpa menambah method chat baru di service layer.
5. Menyediakan unit test dan dokumentasi penggunaan auto mode.

---

## 2. Analisis Routing - Logic Routing

### 2.1 Kontrak Input Auto Mode

Mode auto berlaku untuk request berikut:

- `GenerateRequest`
- `StreamRequest`
- `EmbeddingRequest`
- `ChatRequest`

Kontrak request:

- `provider` menerima nilai `"auto"` melalui `ProviderEnum.AUTO`.
- `model` menggunakan default `"auto"` pada request schema yang relevan.
- Response schema tetap memakai struktur yang sama; yang berubah hanya nilai `provider` dan `model` pada response sukses yang harus mencerminkan provider/model aktual yang berhasil dipakai.

### 2.2 Prioritas Provider

Urutan prioritas fixed untuk auto mode:

1. `nvidia`
2. `gemini`
3. `ollama`

Urutan ini dipakai konsisten di semua operation. Auto router tidak melakukan round-robin, load balancing paralel, atau scoring dinamis pada versi ini.

### 2.3 Filtering Berdasarkan Capability

Filtering target harus mengikuti field pada `ModelCapability`:

- `supports_text=True` untuk request generate dan chat.
- `supports_image=True` bila request membawa `images`.
- `supports_embedding=True` untuk endpoint embedding.
- `supports_streaming=True` untuk endpoint stream.

Aturan routing:

- Request generate/chat tanpa image hanya mempertimbangkan model text-capable.
- Request generate/chat dengan image hanya mempertimbangkan model yang `supports_text=True` dan `supports_image=True`.
- Request embedding hanya mempertimbangkan model embedding.
- Request stream hanya mempertimbangkan model yang mendukung streaming.

### 2.4 Integrasi Health Status

`HealthChecker` diintegrasikan melalui dependency injection, bukan akses global langsung di dalam service logic.

Aturan health-aware selection:

- Provider dengan `status == "down"` dilewati menggunakan `HealthChecker.is_provider_up()`.
- Provider dengan status `up` atau `degraded` tetap boleh dicoba.
- Bila `HealthChecker` belum tersedia, auto router memakai semua provider yang terdaftar.

### 2.5 Aturan Fallback

Pseudo-code untuk generate dan embedding:

```python
targets = self._get_auto_routing_targets(...)

for target in targets:
    try:
        return await self._generate_single(...)  # atau _embedding_single(...)
    except (
        ProviderAPIError,
        ProviderTimeoutError,
        ProviderConnectionError,
        AllKeysExhaustedError,
    ) as exc:
        logger.warning("Auto-fallback: {provider} gagal ({error})", ...)
        continue

raise AIGatewayError("All auto-routing targets failed.")
```

Aturan khusus streaming:

1. Gateway boleh mencoba target berikutnya hanya jika error terjadi sebelum token pertama berhasil di-yield.
2. Setelah token pertama terkirim, fallback tidak boleh dilakukan karena SSE response sudah dimulai.
3. Jika error terjadi setelah stream berjalan, exception dinaikkan kembali agar flow existing di endpoint stream menangani error tersebut.

Aturan chat:

- Tidak ada method chat baru di `GeneratorService`.
- Auto routing untuk chat terjadi karena `app/api/endpoints/chat.py` membangun `GenerateRequest` lalu memanggil `GeneratorService.generate()`.

---

## 3. Arsitektur

### 3.1 Schema Updates

File yang berubah:

- `app/schemas/common.py`
- `app/schemas/requests.py`

Perubahan inti:

```python
class ProviderEnum(str, Enum):
    OLLAMA = "ollama"
    GEMINI = "gemini"
    NVIDIA = "nvidia"
    AUTO = "auto"
```

Request schema yang diupdate:

- `GenerateRequest.model`
- `StreamRequest.model`
- `EmbeddingRequest.model`
- `ChatRequest.model`

Semua field `model` di atas menggunakan default `"auto"` agar kontrak request konsisten saat client hanya mengirim `provider="auto"`.

### 3.2 GeneratorService

File utama:

- `app/services/generator.py`

Perubahan desain:

1. `GeneratorService.__init__()` menerima `health_checker: HealthChecker | None = None`.
2. Tambah helper `_get_auto_routing_targets(...)` untuk mengembalikan daftar `ModelCapability` yang sudah difilter dan diurutkan.
3. Refactor flow provider tunggal ke helper private agar `generate()`, `stream()`, dan `embedding()` bisa memakai jalur validasi yang sama untuk mode explicit maupun auto.
4. `generate()` dan `embedding()` melakukan fallback penuh sampai ada target sukses atau semua target habis.
5. `stream()` mencoba target satu per satu, tetapi hanya boleh fallback sebelum first token.

Contoh helper yang ditambahkan:

```python
def _get_auto_routing_targets(
    self,
    requires_image: bool = False,
    is_embedding: bool = False,
    requires_streaming: bool = False,
) -> list[ModelCapability]:
    ...
```

### 3.3 Dependency Injection

File yang berubah:

- `app/api/dependencies.py`

Perubahan desain:

1. `HealthChecker` diinisialisasi lebih dulu setelah providers tersedia.
2. `GeneratorService` dibuat sesudah `HealthChecker` agar dependency dapat di-pass langsung melalui constructor.
3. `BatchService` tetap dibuat setelah `GeneratorService`.

Urutan baru:

```python
providers -> model registry -> cache service -> health checker -> generator service -> session manager -> batch service
```

### 3.4 Chat Flow dan Response Behavior

Flow chat tetap berada di:

- `app/api/endpoints/chat.py`

Flow-nya:

```python
ChatRequest -> GenerateRequest -> GeneratorService.generate() -> ChatResponse
```

Konsekuensi desain:

- `ChatResponse.provider` dan `ChatResponse.model` harus menampilkan provider/model aktual dari hasil `GeneratorService.generate()`.
- Tidak ada perubahan pada `ChatHistoryResponse`.
- Tidak ada perubahan pada metadata session yang sudah disimpan oleh `SessionManager` pada versi ini.

---

## 4. Scope

### Yang Dikerjakan

1. **Schemas** - tambah `ProviderEnum.AUTO` dan default `model="auto"` pada request schema.
2. **Health Integration** - sambungkan `HealthChecker` ke `GeneratorService` lewat dependency injection.
3. **Priority Selection** - implement `_get_auto_routing_targets(...)` dengan filter capability dan prioritas `nvidia -> gemini -> ollama`.
4. **Fallback Loop** - update `generate()`, `stream()`, dan `embedding()` untuk auto routing.
5. **Chat Compatibility** - pastikan flow chat existing bekerja lewat `GeneratorService.generate()` tanpa method service baru.
6. **Unit Tests** - tambah test khusus auto routing di `tests/services/test_generator_service.py`.
7. **Documentation** - tambah panduan penggunaan auto mode di `how_to_run.md`.

### Yang TIDAK Dikerjakan

- Load balancing kompleks seperti round-robin atau least-connection.
- Parallel fan-out ke beberapa provider dalam satu request.
- Perubahan pada `ChatHistoryResponse` atau metadata session yang tersimpan.
- Persistensi metric fallback ke database.
- Policy ranking model berdasarkan benchmark kualitas atau latency dinamis.

---

## 5. Rencana Pengujian

### Test Case 1: Auto Generate - Jalur Ideal

- `provider="auto"`, `model="auto"`.
- NVIDIA tersedia dan sukses.
- Assert response berasal dari `nvidia` dan model NVIDIA yang dipilih.

### Test Case 2: Auto Generate - Fallback ke Gemini

- NVIDIA melempar `ProviderTimeoutError`.
- Gemini sukses.
- Assert warning log tercatat dan response sukses berasal dari `gemini`.

### Test Case 3: Auto Embedding - Filter Capability

- Registry berisi model text dan embedding.
- Request `EmbeddingRequest(provider="auto", model="auto", ...)`.
- Assert hanya model `supports_embedding=True` yang dipertimbangkan.

### Test Case 4: Auto Stream - Retry Sebelum First Token

- Target pertama melempar `ProviderConnectionError` sebelum token pertama.
- Target kedua berhasil mengirim token.
- Assert fallback terjadi dan stream tetap berjalan normal.

### Test Case 5: Auto Stream - Error Setelah First Token

- Target pertama berhasil mengirim token pertama lalu gagal.
- Assert exception diteruskan dan tidak ada fallback ke target berikutnya.

### Test Case 6: Auto Chat - Flow Existing Tetap Valid

- `ChatRequest(provider="auto", model="auto", ...)`.
- Endpoint chat tetap memanggil `GeneratorService.generate()`.
- Assert `ChatResponse.provider` dan `ChatResponse.model` berasal dari provider aktual yang berhasil.

---

## 6. Task Breakdown (Estimasi)

| # | Task | Scope | Estimasi |
|---|------|-------|----------|
| 1 | Schemas & Enum Auto Mode | `app/schemas/common.py`, `app/schemas/requests.py` | 15 min |
| 2 | Priority Selection & Health Integration | `app/services/generator.py`, `app/api/dependencies.py` | 45 min |
| 3 | Fallback Loop: Generate & Chat Flow | `app/services/generator.py`, validasi flow `app/api/endpoints/chat.py` | 45 min |
| 4 | Fallback Loop: Stream & Embedding | `app/services/generator.py` | 45 min |
| 5 | Unit Tests: GeneratorService Auto Routing | `tests/services/test_generator_service.py` | 1 hr |
| 6 | Documentation: Auto Mode | `how_to_run.md` | 15 min |

**Total estimasi: ~3.75 jam**

---

## 7. Risiko & Mitigasi

| Risiko | Dampak | Mitigasi |
|--------|--------|----------|
| Health status stale menyebabkan provider sehat ikut dilewati | Auto mode kehilangan kandidat yang valid | Hanya skip provider dengan `status == "down"` melalui `is_provider_up()`; status `degraded` tetap dianggap tersedia |
| Streaming gagal di tengah response | Client menerima stream terputus | Fallback hanya diizinkan sebelum first token; setelah stream dimulai error diteruskan ke flow SSE existing |
| Chat session tetap menyimpan provider/model awal dari request | Metadata history bisa berbeda dengan response aktual | Batasi scope versi ini pada `ChatResponse`; tidak mengubah session persistence pada `SessionManager` |

---

## 8. Success Criteria

- [ ] `provider="auto"` diterima oleh request schema generate, stream, embedding, dan chat.
- [ ] `model="auto"` menjadi default yang valid untuk request schema terkait.
- [ ] `GeneratorService` dapat memilih target auto routing berdasarkan capability, prioritas, dan status health.
- [ ] `generate()` dan `embedding()` melakukan fallback otomatis saat target pertama gagal.
- [ ] `stream()` hanya melakukan fallback sebelum token pertama dikirim.
- [ ] Flow chat tetap memakai `GeneratorService.generate()` dan tidak memperkenalkan method chat baru di service layer.
- [ ] `GenerateResponse`, `EmbeddingResponse`, dan `ChatResponse` mengembalikan provider/model aktual yang berhasil dipakai.
- [ ] Task breakdown dan semua file task `beta0.2.7` konsisten dengan struktur dokumen standar repo.
