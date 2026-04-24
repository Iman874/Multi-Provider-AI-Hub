# Task 5 - Models Endpoint & Documentation

## 1. Judul Task
Expose `supports_reasoning` di endpoint models dan perbarui dokumentasi penggunaan

## 2. Deskripsi
Task ini menyelesaikan API exposure untuk capability reasoning. Setelah registry dan provider mapping selesai, endpoint `GET /api/v1/models` harus mengembalikan field `supports_reasoning`, lalu dokumentasi perlu diperbarui agar consumer API memahami arti field tersebut dan batasannya.

## 3. Tujuan Teknis
- `GET /api/v1/models` mengembalikan `supports_reasoning` untuk semua item
- `include_unavailable` dan `limit` tetap bekerja seperti sebelumnya
- `supports_reasoning` didokumentasikan di `how_to_run.md`
- Dokumentasi menjelaskan bahwa version ini hanya capability discovery, belum runtime reasoning control

## 4. Scope

### Yang dikerjakan
- `app/api/endpoints/models.py` - tambah mapping field `supports_reasoning`
- `how_to_run.md` - update contoh response models dan penjelasan capability reasoning

### Yang TIDAK dikerjakan
- Perubahan endpoint generate/chat/stream
- Parameter request baru untuk reasoning
- Unit tests

## 5. Langkah Implementasi

### Step 1: Update mapping di `app/api/endpoints/models.py`
Saat membangun `ModelInfoWithAvailability`, tambahkan:

```python
supports_reasoning=m.supports_reasoning,
```

Pastikan semua field existing tetap dipetakan seperti sebelumnya.

### Step 2: Jangan ubah filtering endpoint
Logic berikut tetap dipertahankan:

- filter `provider`
- `limit` per provider
- `include_unavailable`
- availability via `HealthChecker.is_provider_up()`

Task ini hanya menambah satu field response.

### Step 3: Update contoh response di `how_to_run.md`
Tambahkan `supports_reasoning` pada contoh response `GET /api/v1/models`.

Contoh minimal:

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

### Step 4: Tambah penjelasan makna field
Dokumentasi harus menjelaskan:

- `supports_reasoning=true` berarti model dikenali support reasoning/thinking mode
- field ini hanya capability metadata
- field ini belum berarti gateway sudah punya request parameter universal untuk reasoning

### Step 5: Tegaskan batas version ini
Dokumentasi harus menyebut dengan jelas bahwa `beta0.2.8` belum menambahkan:

- `think`
- `thinking_budget`
- reasoning trace di response
- reasoning-aware auto routing

## 6. Output yang Diharapkan

Contoh call:

```powershell
curl "http://localhost:8000/api/v1/models?provider=gemini"
```

Contoh response:

```json
[
  {
    "name": "gemini-2.5-pro",
    "provider": "gemini",
    "supports_text": true,
    "supports_image": true,
    "supports_embedding": false,
    "supports_reasoning": true,
    "available": true
  }
]
```

## 7. Dependencies
- Task 1 (Registry & Response Schema Update)
- Task 3 (Ollama Reasoning Discovery)
- Task 4 (Gemini & NVIDIA Reasoning Mapping)

## 8. Acceptance Criteria
- [x] `GET /api/v1/models` response memiliki field `supports_reasoning`
- [x] `supports_reasoning` berasal dari registry model, bukan hardcode endpoint
- [x] Filtering existing endpoint tetap tidak berubah
- [x] `how_to_run.md` memiliki contoh response models dengan field baru
- [x] Dokumentasi menjelaskan bahwa field ini belum mengaktifkan runtime reasoning control

## 9. Estimasi
Low (~20 menit)
