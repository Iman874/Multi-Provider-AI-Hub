# Task 4 — Integration & End-to-End Validation

> **Modul**: beta0.1.7 — Multimodal Handling  
> **Estimasi**: Medium (60–90 menit)  
> **Dependencies**: Task 2 (Ollama image), Task 3 (Gemini multimodal)

---

## 1. Judul Task

End-to-end validation: multimodal generate dan stream untuk kedua provider, capability validation, dan regression testing.

---

## 2. Deskripsi

Memvalidasi bahwa semua multimodal paths berfungsi end-to-end melalui API. Termasuk:
- `POST /generate` + images → kedua provider
- `POST /stream` + images → kedua provider
- Capability validation: non-vision model + images → 400 error
- Regression: text-only requests masih berfungsi

**Penting**: Tidak ada perubahan di endpoint code, service code, atau schema — semua sudah di-handle oleh code dari beta0.1.3. Task ini memvalidasi bahwa **zero-change architecture** tetap berlaku untuk multimodal.

---

## 3. Tujuan Teknis

- Verify image flows through: endpoint → service → provider → AI
- Verify capability validation catches non-vision models
- Verify text-only flow unaffected
- Verify streaming + images works
- Verify ZERO changes needed di `generate.py`, `stream.py`, `generator.py`, schemas

---

## 4. Scope

### ✅ Yang Dikerjakan

- End-to-end test semua multimodal scenarios
- Verify zero-change architecture
- Regression testing

### ❌ Yang Tidak Dikerjakan

- New code (semua kode baru sudah di task 1–3)
- Performance benchmarks
- Image quality evaluation

---

## 5. Langkah Implementasi

### Step 0: Prepare test image

Encode sebuah gambar test sebagai base64:

```bash
python -c "
import base64
# Use any small image file you have
with open('test_image.jpg', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()
    print(f'Base64 length: {len(b64)}')
    print(f'First 50 chars: {b64[:50]}...')
    # Save for use in curl commands
    with open('test_image_b64.txt', 'w') as out:
        out.write(b64)
"
```

Atau gunakan data URI format:
```bash
python -c "
import base64
with open('test_image.jpg', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()
    data_uri = f'data:image/jpeg;base64,{b64}'
    print(f'Data URI length: {len(data_uri)}')
"
```

### Step 1: Start server

```bash
uvicorn app.main:app --reload --port 8000
```

### Step 2: Test Ollama multimodal generate

```bash
# Replace <BASE64_IMAGE> with actual base64 string
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama",
    "model": "llama3.2-vision",
    "input": "What is in this image? Describe briefly.",
    "images": ["<BASE64_IMAGE>"]
  }'
```

Expected response:

```json
{
    "output": "The image shows...",
    "provider": "ollama",
    "model": "llama3.2-vision",
    "usage": { ... },
    "metadata": { ... }
}
```

### Step 3: Test Gemini multimodal generate

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gemini",
    "model": "gemini-2.0-flash",
    "input": "Describe this image in one sentence.",
    "images": ["<BASE64_IMAGE>"]
  }'
```

### Step 4: Test Ollama multimodal streaming

```bash
curl -N -X POST http://localhost:8000/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama",
    "model": "llama3.2-vision",
    "input": "What do you see?",
    "images": ["<BASE64_IMAGE>"]
  }'
```

Expected: SSE tokens streaming, ending with `data: [DONE]`

### Step 5: Test Gemini multimodal streaming

```bash
curl -N -X POST http://localhost:8000/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gemini",
    "model": "gemini-2.0-flash",
    "input": "Describe what you see.",
    "images": ["<BASE64_IMAGE>"]
  }'
```

### Step 6: Test capability validation — non-vision model + images

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama",
    "model": "llama3.2",
    "input": "What is this?",
    "images": ["<BASE64_IMAGE>"]
  }'
```

Expected 400 response:

```json
{
    "error": "Model 'llama3.2' does not support 'image'",
    "code": "CAPABILITY_NOT_SUPPORTED"
}
```

### Step 7: Test data URI stripping (Ollama)

```bash
# Send with data URI prefix — should work (prefix stripped automatically)
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama",
    "model": "llama3.2-vision",
    "input": "What is this?",
    "images": ["data:image/jpeg;base64,<BASE64_IMAGE>"]
  }'
```

### Step 8: Regression — text-only requests

```bash
# Text-only generate (should still work)
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"provider":"ollama","model":"llama3.2","input":"Hello"}'

# Text-only stream (should still work)
curl -N -X POST http://localhost:8000/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"provider":"ollama","model":"llama3.2","input":"Hello"}'

# Embedding (should still work)
curl -X POST http://localhost:8000/api/v1/embedding \
  -H "Content-Type: application/json" \
  -d '{"provider":"ollama","model":"qwen3-embedding:0.6b","input":"Hello"}'

# Models list (should still work)
curl http://localhost:8000/api/v1/models
```

### Step 9: Verify zero-change architecture

These files must have **ZERO modifications** from beta0.1.6:

```
# No changes allowed:
app/api/endpoints/generate.py
app/api/endpoints/stream.py
app/api/endpoints/embedding.py
app/api/endpoints/models.py
app/services/generator.py
app/api/dependencies.py
app/api/router.py
app/main.py
app/schemas/*
```

If using git:
```bash
git diff --name-only
# Should only show:
# app/providers/ollama.py    (modified)
# app/providers/gemini.py    (modified)
# app/utils/__init__.py      (new)
# app/utils/image.py         (new)
```

---

## 6. Output yang Diharapkan

### Validation Matrix

| Test | Ollama | Gemini |
|---|---|---|
| Generate + image | ✅ | ✅ |
| Stream + image | ✅ | ✅ |
| Non-vision + image | ❌ 400 | ❌ 400 |
| Text-only (regression) | ✅ | ✅ |
| Embedding (regression) | ✅ | ✅/⚠️ |

### Final API Surface (complete after beta0.1.7)

| Method | Path | Supports Images |
|---|---|---|
| GET | `/health` | N/A |
| GET | `/api/v1/models` | N/A |
| POST | `/api/v1/generate` | ✅ via `images` field |
| POST | `/api/v1/stream` | ✅ via `images` field |
| POST | `/api/v1/embedding` | ❌ (text only) |

---

## 7. Dependencies

- **Task 2** — Ollama image support implemented
- **Task 3** — Gemini multimodal support implemented
- **Running Ollama** with `llama3.2-vision` pulled
- **GEMINI_API_KEY** for Gemini tests
- **Test image file** untuk generate base64

---

## 8. Acceptance Criteria

- [ ] `POST /generate` + Ollama vision + image → AI describes image
- [ ] `POST /generate` + Gemini + image → AI describes image
- [ ] `POST /stream` + image → SSE tokens about image content
- [ ] Non-vision model + images → 400 CAPABILITY_NOT_SUPPORTED
- [ ] Data URI prefix automatically stripped for Ollama
- [ ] Base64 → bytes conversion works for Gemini
- [ ] Text-only generate still works (no regression)
- [ ] Text-only stream still works (no regression)
- [ ] Embedding still works (no regression)
- [ ] Models endpoint still works (no regression)
- [ ] ZERO changes in endpoint/service/schema files
- [ ] Only `ollama.py`, `gemini.py`, and `utils/image.py` modified/created

---

## 9. Estimasi

**Medium** — Mostly testing, but thorough coverage of all multimodal paths + regression.
