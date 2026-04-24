# Task 3 — GeminiProvider Multimodal Support

> **Modul**: beta0.1.7 — Multimodal Handling  
> **Estimasi**: High (2–3 jam)  
> **Dependencies**: Task 1 (Image Utilities), beta0.1.5 Task 2 (Gemini stream)

---

## 1. Judul Task

Update `GeminiProvider.generate()` dan `stream()` — tambah native multimodal support menggunakan `Part.from_data()` untuk image input.

---

## 2. Deskripsi

Gemini menerima image secara native via `Part.from_data(data=bytes, mime_type="image/jpeg")`. Task ini mengupdate kedua methods untuk membangun `contents` list yang mencampur text dan image parts.

---

## 3. Tujuan Teknis

- `generate()`: jika `images` ada → convert base64 → bytes, detect MIME, build mixed contents
- `stream()`: sama — build mixed contents dengan image parts
- `supports_image()`: return `True`
- Contents format: `[prompt_text, Part.from_data(...), Part.from_data(...), ...]`

---

## 4. Scope

### ✅ Yang Dikerjakan

- Update `generate()` di `app/providers/gemini.py`
- Update `stream()` di `app/providers/gemini.py`
- Update `supports_image()` → return `True`

### ❌ Yang Tidak Dikerjakan

- Video input
- Multiple image analysis optimization

---

## 5. Langkah Implementasi

### Step 1: Add imports di `app/providers/gemini.py`

```python
from app.utils.image import base64_to_bytes, detect_mime_type
```

### Step 2: Create helper method `_build_contents()`

Add a private helper method to `GeminiProvider`:

```python
    def _build_contents(
        self,
        prompt: str,
        images: Optional[list[str]] = None,
    ) -> list:
        """
        Build Gemini contents list with text and optional image parts.

        For text-only: ["prompt text"]
        For multimodal: ["prompt text", Part.from_data(bytes, mime), ...]
        """
        contents: list = [prompt]

        if images:
            for img_b64 in images:
                # Convert base64 → raw bytes
                img_bytes = base64_to_bytes(img_b64)
                # Detect MIME type
                mime = detect_mime_type(img_b64)
                # Create Gemini Part
                part = types.Part.from_bytes(
                    data=img_bytes,
                    mime_type=mime,
                )
                contents.append(part)

        return contents
```

### Step 3: Update `generate()` — use `_build_contents()`

Replace the existing contents building logic:

**Before:**
```python
        # Build contents — text only for now
        contents: list = [prompt]

        # Image support placeholder (beta0.1.7)
        if images:
            contents = [prompt]  # Will add image Parts in beta0.1.7
```

**After:**
```python
        # Build contents (text-only or multimodal)
        contents = self._build_contents(prompt, images)
```

### Step 4: Update `stream()` — use `_build_contents()`

Same replacement in `stream()`:

**Before:**
```python
        # Build contents — text only for now
        contents: list = [prompt]

        # Image support placeholder (beta0.1.7)
        if images:
            contents = [prompt]
```

**After:**
```python
        # Build contents (text-only or multimodal)
        contents = self._build_contents(prompt, images)
```

### Step 5: Update `supports_image()`

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

### Step 6: Verifikasi (GEMINI_API_KEY diperlukan)

```bash
python -c "
import asyncio
import base64
from app.config import settings
from app.providers.gemini import GeminiProvider

async def test():
    if not settings.GEMINI_API_KEY:
        print('GEMINI_API_KEY not set, skipping')
        return

    provider = GeminiProvider(
        api_key=settings.GEMINI_API_KEY,
        timeout=60,
    )

    print(f'supports_image: {provider.supports_image(\"gemini-2.0-flash\")}')

    # Test _build_contents
    contents = provider._build_contents('Hello')
    print(f'Text only: {len(contents)} part(s)')

    # Test with fake image (1x1 red pixel JPEG)
    # In real test, use actual image file
    # with open('test.jpg', 'rb') as f:
    #     img_b64 = base64.b64encode(f.read()).decode()
    #     result = await provider.generate(
    #         model='gemini-2.0-flash',
    #         prompt='What is in this image?',
    #         images=[img_b64],
    #     )
    #     print(f'Output: {result[\"output\"][:100]}')

asyncio.run(test())
"
```

### Step 7: Test text-only regression

```bash
python -c "
import asyncio
from app.config import settings
from app.providers.gemini import GeminiProvider

async def test():
    if not settings.GEMINI_API_KEY:
        print('GEMINI_API_KEY not set, skipping')
        return

    provider = GeminiProvider(
        api_key=settings.GEMINI_API_KEY,
        timeout=60,
    )
    # Text-only should still work
    result = await provider.generate(
        model='gemini-2.0-flash',
        prompt='Say hello in one word',
    )
    print(f'Text-only: {result[\"output\"][:50]}')

asyncio.run(test())
"
```

---

## 6. Output yang Diharapkan

### Contents Building

| Input | Contents |
|---|---|
| `prompt="Hello"`, `images=None` | `["Hello"]` |
| `prompt="Describe"`, `images=[base64]` | `["Describe", Part.from_bytes(bytes, "image/jpeg")]` |
| `prompt="Compare"`, `images=[img1, img2]` | `["Compare", Part(...), Part(...)]` |

### Method Changes

| Method | Change |
|---|---|
| `generate()` | Use `_build_contents()` for mixed text+image |
| `stream()` | Use `_build_contents()` for mixed text+image |
| `supports_image()` | `return False` → `return True` |
| `_build_contents()` | **NEW** private helper |

---

## 7. Dependencies

- **Task 1** — `base64_to_bytes`, `detect_mime_type` from `app/utils/image.py`
- **beta0.1.5 Task 2** — existing `stream()` implementation
- **Valid GEMINI_API_KEY** for integration test

---

## 8. Acceptance Criteria

- [ ] `generate()` sends image parts to Gemini when images provided
- [ ] `stream()` sends image parts to Gemini when images provided
- [ ] `_build_contents()` correctly builds text-only and multimodal contents
- [ ] MIME type detected from base64 data
- [ ] Data URI prefix stripped before byte conversion
- [ ] `supports_image()` returns `True`
- [ ] Text-only requests still work (no regression)
- [ ] `types.Part.from_bytes()` used correctly with `data=bytes, mime_type=str`

---

## 9. Estimasi

**High** — SDK multimodal API, content part building, MIME handling, dual method update.
