# Task 1 - Schemas & Enum Auto Mode

## 1. Judul Task
Tambah `ProviderEnum.AUTO` dan update request schema agar menerima auto mode secara konsisten

## 2. Deskripsi
Task ini menyiapkan kontrak input untuk smart routing. Perubahan utamanya adalah menambahkan `"auto"` pada `ProviderEnum` di `app/schemas/common.py` dan mengubah request schema di `app/schemas/requests.py` agar field `model` memakai default `"auto"` pada semua endpoint yang mendukung auto routing.

## 3. Tujuan Teknis
- `ProviderEnum` menerima value `"auto"` di `app/schemas/common.py`
- `GenerateRequest`, `StreamRequest`, `EmbeddingRequest`, dan `ChatRequest` menerima `provider="auto"`
- `model` pada keempat request schema di atas memakai default `"auto"`
- Request schema tetap menjaga validasi input utama seperti `input` dan `message`
- Tidak ada perubahan pada response schema di task ini

## 4. Scope

### Yang dikerjakan
- `app/schemas/common.py` - tambah `AUTO = "auto"` ke `ProviderEnum`
- `app/schemas/requests.py` - update `GenerateRequest`, `StreamRequest`, `EmbeddingRequest`, dan `ChatRequest`
- Examples dan description field disesuaikan agar mencerminkan auto mode

### Yang TIDAK dikerjakan
- Logic smart routing di `GeneratorService`
- Integrasi `HealthChecker`
- Perubahan response schema
- Perubahan metadata session chat

## 5. Langkah Implementasi

### Step 1: Tambah `AUTO` ke `ProviderEnum` di `app/schemas/common.py`
Update enum existing:

```python
class ProviderEnum(str, Enum):
    OLLAMA = "ollama"
    GEMINI = "gemini"
    NVIDIA = "nvidia"
    AUTO = "auto"
```

### Step 2: Update request schema di `app/schemas/requests.py`
Field `provider` tetap required, tetapi examples harus memasukkan `"auto"`.

Request schema yang diubah:

- `GenerateRequest`
- `StreamRequest`
- `EmbeddingRequest`
- `ChatRequest`

### Step 3: Ubah field `model` menjadi default `"auto"`
Semua request schema di atas menggunakan pola:

```python
model: str = Field(
    default="auto",
    description="Model name or 'auto' for smart routing",
    examples=["auto", "llama3.2", "gemini-2.5-pro"],
)
```

### Step 4: Pertahankan validasi request lain apa adanya
Task ini tidak menambah validator baru. Input utama seperti `input` dan `message` tetap menggunakan kontrak existing yang sudah ada di schema.

### Step 5: Pastikan flow chat memakai kontrak yang sama
`ChatRequest` harus mengikuti kontrak auto mode yang sama karena endpoint chat di `app/api/endpoints/chat.py` meneruskan request ke `GenerateRequest`.

## 6. Output yang Diharapkan

Request generate valid:

```json
{
  "provider": "auto",
  "model": "auto",
  "input": "Ringkas artikel ini."
}
```

Request chat valid walaupun model tidak diisi eksplisit:

```json
{
  "provider": "auto",
  "message": "Jelaskan status provider yang tersedia."
}
```

## 7. Dependencies
- Tidak ada

## 8. Acceptance Criteria
- [x] `ProviderEnum.AUTO = "auto"` ada di `app/schemas/common.py`
- [x] `GenerateRequest` menerima `provider="auto"`
- [x] `StreamRequest` menerima `provider="auto"`
- [x] `EmbeddingRequest` menerima `provider="auto"`
- [x] `ChatRequest` menerima `provider="auto"`
- [x] Field `model` pada keempat request schema memakai default `"auto"`
- [x] Tidak ada referensi salah ke `app/schemas/requests.py` untuk definisi `ProviderEnum`

## 9. Estimasi
Low (~15 menit)
