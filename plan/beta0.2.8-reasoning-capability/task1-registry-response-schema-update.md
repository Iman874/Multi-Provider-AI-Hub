# Task 1 - Registry & Response Schema Update

## 1. Judul Task
Tambah capability `supports_reasoning` ke registry model dan response schema endpoint models

## 2. Deskripsi
Task ini menyiapkan kontrak data untuk reasoning capability di level gateway. Perubahan utamanya adalah menambahkan field `supports_reasoning` ke `ModelCapability` di registry, lalu mengekspos field yang sama lewat response schema `ModelInfo` dan `ModelInfoWithAvailability` agar `GET /api/v1/models` bisa mengembalikan metadata reasoning secara konsisten.

## 3. Tujuan Teknis
- `ModelCapability` memiliki field baru `supports_reasoning: bool = False`
- `ModelInfo` memiliki field response `supports_reasoning`
- `ModelInfoWithAvailability` otomatis mewarisi field tersebut
- Perubahan ini tidak mengubah contract response generate/chat/embedding/stream
- Default seluruh model existing tetap `supports_reasoning=False` sampai provider mapping diperbarui

## 4. Scope

### Yang dikerjakan
- `app/services/model_registry.py` - tambah field `supports_reasoning` ke dataclass `ModelCapability`
- `app/schemas/responses.py` - tambah field `supports_reasoning` ke `ModelInfo`

### Yang TIDAK dikerjakan
- Logic deteksi reasoning per provider
- Perubahan `GET /api/v1/models` handler
- Dokumentasi `how_to_run.md`
- Unit tests

## 5. Langkah Implementasi

### Step 1: Update `ModelCapability` di `app/services/model_registry.py`
Tambahkan field baru di dataclass:

```python
supports_reasoning: bool = False
```

Letakkan setelah `supports_streaming` agar grouping capability tetap jelas.

### Step 2: Update docstring `ModelCapability`
Perbarui penjelasan capability di docstring agar reasoning menjadi capability resmi yang disimpan registry, setara dengan text, image, embedding, dan streaming.

### Step 3: Update `ModelInfo` di `app/schemas/responses.py`
Tambahkan field response:

```python
supports_reasoning: bool = Field(
    ..., description="Whether the model supports reasoning/thinking mode"
)
```

Karena `ModelInfoWithAvailability` mewarisi `ModelInfo`, tidak perlu schema baru untuk field reasoning.

### Step 4: Pastikan backward compatibility response lain
Task ini tidak menyentuh:

- `GenerateResponse`
- `EmbeddingResponse`
- `ChatResponse`
- SSE payload di endpoint stream

### Step 5: Default reasoning untuk model existing tetap false
Sebelum provider mapping di task berikutnya masuk, semua object `ModelCapability` yang belum mengisi field baru harus tetap valid karena field memiliki default `False`.

## 6. Output yang Diharapkan

Contoh object registry:

```python
model = ModelCapability(
    name="gemini-2.5-pro",
    provider="gemini",
    supports_text=True,
    supports_image=True,
    supports_embedding=False,
    supports_streaming=True,
    supports_reasoning=True,
)
```

Contoh response schema:

```json
{
  "name": "gemini-2.5-pro",
  "provider": "gemini",
  "supports_text": true,
  "supports_image": true,
  "supports_embedding": false,
  "supports_reasoning": true,
  "available": true
}
```

## 7. Dependencies
- Tidak ada

## 8. Acceptance Criteria
- [x] `ModelCapability` memiliki field `supports_reasoning`
- [x] Default field tersebut adalah `False`
- [x] `ModelInfo` memiliki field `supports_reasoning`
- [x] `ModelInfoWithAvailability` mewarisi field reasoning tanpa schema tambahan
- [x] Tidak ada perubahan pada contract response endpoint lain

## 9. Estimasi
Low (~20 menit)
