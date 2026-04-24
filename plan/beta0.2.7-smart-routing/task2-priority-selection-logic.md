# Task 2 - Priority Selection & Health Integration

## 1. Judul Task
Implement helper seleksi target auto routing dan sambungkan `HealthChecker` ke `GeneratorService`

## 2. Deskripsi
Task ini membangun fondasi routing untuk auto mode. `GeneratorService` harus bisa mengambil daftar model kandidat dari `ModelRegistry`, memfilter berdasarkan capability, melewati provider yang sedang DOWN, lalu mengurutkan target berdasarkan prioritas tetap `nvidia -> gemini -> ollama`.

## 3. Tujuan Teknis
- `GeneratorService` menerima `HealthChecker` melalui dependency injection
- `app/api/dependencies.py` menginisialisasi `HealthChecker` sebelum `GeneratorService`
- Tersedia helper `_get_auto_routing_targets(...)` di `app/services/generator.py`
- Filtering target mengikuti field `ModelCapability`: text, image, embedding, dan streaming
- Provider DOWN dilewati melalui `HealthChecker.is_provider_up()`
- Hasil routing selalu terurut `nvidia`, lalu `gemini`, lalu `ollama`

## 4. Scope

### Yang dikerjakan
- `app/services/generator.py` - tambah dependency `health_checker` dan helper auto routing
- `app/api/dependencies.py` - ubah urutan inisialisasi service agar `HealthChecker` di-pass ke `GeneratorService`

### Yang TIDAK dikerjakan
- Fallback loop di `generate()`, `stream()`, dan `embedding()`
- Unit tests
- Dokumentasi `how_to_run.md`

## 5. Langkah Implementasi

### Step 1: Tambah dependency `health_checker` ke `GeneratorService.__init__()`
Update constructor:

```python
def __init__(
    self,
    providers: dict[str, BaseProvider],
    registry: ModelRegistry,
    cache: "CacheService | None" = None,
    health_checker: "HealthChecker | None" = None,
):
    ...
```

Simpan dependency ini sebagai `self._health_checker`.

### Step 2: Ubah urutan inisialisasi di `app/api/dependencies.py`
Setelah providers, registry, dan cache tersedia:

1. Buat `HealthChecker`
2. Buat `GeneratorService` dengan argumen `health_checker=_health_checker`
3. Buat `SessionManager`
4. Buat `BatchService`

Task ini tidak menggunakan akses global langsung dari dalam `GeneratorService`.

### Step 3: Tambah helper `_get_auto_routing_targets(...)`
Tambahkan helper berikut di `app/services/generator.py`:

```python
def _get_auto_routing_targets(
    self,
    requires_image: bool = False,
    is_embedding: bool = False,
    requires_streaming: bool = False,
) -> list[ModelCapability]:
    ...
```

### Step 4: Ambil kandidat dari `ModelRegistry`
Gunakan `self._registry.list_models()` sebagai sumber kandidat.

Aturan filter:

- `is_embedding=True` -> hanya model `supports_embedding=True`
- `is_embedding=False` -> hanya model `supports_text=True`
- `requires_image=True` -> hanya model `supports_image=True`
- `requires_streaming=True` -> hanya model `supports_streaming=True`

### Step 5: Filter provider berdasarkan health status
Jika `self._health_checker` tersedia, skip kandidat dengan:

```python
not self._health_checker.is_provider_up(model.provider)
```

Provider dengan status `degraded` tetap lolos karena method `is_provider_up()` hanya menolak status DOWN.

### Step 6: Urutkan hasil berdasarkan prioritas tetap
Gunakan priority map deterministic:

```python
priority = {
    "nvidia": 0,
    "gemini": 1,
    "ollama": 2,
}
```

Sort key:

```python
key=lambda model: (priority.get(model.provider, 999), model.name)
```

### Step 7: Raise error jika kandidat kosong
Jika hasil filter kosong, raise `AIGatewayError` dengan pesan eksplisit bahwa tidak ada target tersedia untuk auto mode pada capability tersebut.

## 6. Output yang Diharapkan

Contoh hasil helper:

```python
targets = service._get_auto_routing_targets(requires_image=False)
assert [target.provider for target in targets] == ["nvidia", "gemini", "ollama"]
```

Contoh saat image request:

```python
targets = service._get_auto_routing_targets(requires_image=True)
assert all(target.supports_image for target in targets)
```

## 7. Dependencies
- Task 1 (Schemas & Enum Auto Mode)

## 8. Acceptance Criteria
- [x] `GeneratorService.__init__()` menerima dependency `health_checker`
- [x] `app/api/dependencies.py` menginisialisasi `HealthChecker` sebelum `GeneratorService`
- [x] `_get_auto_routing_targets(...)` ada di `app/services/generator.py`
- [x] Filtering target mengikuti `supports_text`, `supports_image`, `supports_embedding`, dan `supports_streaming`
- [x] Provider DOWN dilewati memakai `HealthChecker.is_provider_up()`
- [x] Hasil kandidat terurut `nvidia -> gemini -> ollama`
- [x] Kandidat kosong me-raise `AIGatewayError`

## 9. Estimasi
Medium (~45 menit)
