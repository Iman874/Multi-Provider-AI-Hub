# Task 2 — OllamaProvider Image Support

> **Modul**: beta0.1.7 — Multimodal Handling  
> **Estimasi**: Medium (60–90 menit)  
> **Dependencies**: Task 1 (Image Utilities), beta0.1.5 Task 1 (Ollama stream)

---

## 1. Judul Task

Update `OllamaProvider.generate()` dan `stream()` — tambah image handling menggunakan base64 format yang diharapkan Ollama.

---

## 2. Deskripsi

Ollama menerima image sebagai array of pure base64 strings (tanpa data URI prefix) di field `images` pada payload. Task ini mengupdate `generate()` dan `stream()` untuk memproses dan mengirim images, serta mengupdate `supports_image()` agar return `True`.

---

## 3. Tujuan Teknis

- `generate()`: jika `images` ada → strip data URI, tambah ke payload `"images": [...]`
- `stream()`: sama — tambah images ke payload
- `supports_image()`: return `True` (capability check di registry level)
- Image diproses via `strip_data_uri()` dari `app/utils/image`

---

## 4. Scope

### ✅ Yang Dikerjakan

- Update `generate()` di `app/providers/ollama.py` — add image handling
- Update `stream()` di `app/providers/ollama.py` — add image handling
- Update `supports_image()` → return `True`
- Import image utilities

### ❌ Yang Tidak Dikerjakan

- Image validation (dilakukan di service layer jika diperlukan di future)
- Multiple image batching optimization
- Image resizing

---

## 5. Langkah Implementasi

### Step 1: Add import di `app/providers/ollama.py`

```python
from app.utils.image import strip_data_uri
```

### Step 2: Update `generate()` — image handling

Existing code sudah memiliki placeholder `if images: payload["images"] = images`. Update menjadi:

```python
        # Image support: strip data URI prefix for Ollama
        if images:
            payload["images"] = [strip_data_uri(img) for img in images]
```

> **Note**: Kode ini **mengganti** placeholder yang ada. `strip_data_uri()` memastikan Ollama menerima pure base64 tanpa `data:image/...;base64,` prefix.

### Step 3: Update `stream()` — image handling

Sama seperti generate, update placeholder image handling di `stream()`:

```python
        # Image support: strip data URI prefix for Ollama
        if images:
            payload["images"] = [strip_data_uri(img) for img in images]
```

### Step 4: Update `supports_image()`

Replace:

```python
    def supports_image(self, model: str) -> bool:
        """Image support — will be enabled in beta0.1.7."""
        return False
```

Dengan:

```python
    def supports_image(self, model: str) -> bool:
        """
        Check if model supports image input.

        Returns True — actual capability validation is done by
        ModelRegistry at the service layer level.
        """
        return True
```

### Step 5: Verifikasi (Ollama harus running + llama3.2-vision pulled)

```bash
python -c "
import asyncio
import base64
from app.providers.ollama import OllamaProvider

async def test():
    provider = OllamaProvider('http://localhost:11434', timeout=120)
    try:
        # Create a minimal test image (1x1 red JPEG)
        # In production, use a real image
        # For this test, we use a placeholder — will error if model doesn't support
        print(f'supports_image: {provider.supports_image(\"llama3.2-vision\")}')

        # Test with actual image (you need llama3.2-vision pulled)
        # Uncomment below with a real base64 image:
        # with open('test.jpg', 'rb') as f:
        #     img_b64 = base64.b64encode(f.read()).decode()
        #     result = await provider.generate(
        #         model='llama3.2-vision',
        #         prompt='What is in this image?',
        #         images=[img_b64],
        #     )
        #     print(f'Output: {result[\"output\"][:100]}')
    finally:
        await provider.close()

asyncio.run(test())
"
```

### Step 6: Test data URI stripping

```bash
python -c "
from app.utils.image import strip_data_uri

# Simulating what OllamaProvider does
images_from_user = [
    'data:image/jpeg;base64,/9j/4AAQtest',
    '/9j/4AAQraw',  # Already without prefix
]

processed = [strip_data_uri(img) for img in images_from_user]
print('Processed images:')
for img in processed:
    print(f'  {img[:20]}...')
    assert not img.startswith('data:')
print('All images stripped correctly')
"
```

---

## 6. Output yang Diharapkan

### Ollama Payload (with images)

Before (beta0.1.5):
```json
{
    "model": "llama3.2-vision",
    "prompt": "What is in this image?",
    "stream": false
}
```

After (beta0.1.7):
```json
{
    "model": "llama3.2-vision",
    "prompt": "What is in this image?",
    "stream": false,
    "images": ["/9j/4AAQSkZJRg..."]
}
```

### Method Changes

| Method | Change |
|---|---|
| `generate()` | `if images: payload["images"] = [strip_data_uri(img) for img in images]` |
| `stream()` | Same image handling added |
| `supports_image()` | `return False` → `return True` |

---

## 7. Dependencies

- **Task 1** — `strip_data_uri` from `app/utils/image.py`
- **beta0.1.5 Task 1** — existing `stream()` implementation
- **Running Ollama** with `llama3.2-vision` for integration test

---

## 8. Acceptance Criteria

- [ ] `generate()` includes images in payload when provided
- [ ] `stream()` includes images in payload when provided
- [ ] Data URI prefix is stripped from all images
- [ ] Raw base64 (without prefix) passes through unchanged
- [ ] `supports_image()` returns `True`
- [ ] Text-only requests still work (no regression)
- [ ] Payload format matches Ollama API spec (`"images": [base64_str, ...]`)

---

## 9. Estimasi

**Medium** — Small code changes but needs careful testing with vision model.
