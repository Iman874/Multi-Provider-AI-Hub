# Task 3 — Integration & Validation

> **Modul**: beta0.1.4 — Gemini Provider  
> **Estimasi**: Medium (45–60 menit)  
> **Dependencies**: Task 1 (GeminiProvider), Task 2 (Factory)

---

## 1. Judul Task

Validasi end-to-end: Gemini provider terintegrasi tanpa perubahan pada endpoint, service, atau Ollama code. Verify zero-change architecture.

---

## 2. Deskripsi

Task ini **bukan coding baru** — melainkan memvalidasi bahwa penambahan GeminiProvider bekerja sempurna dengan arsitektur yang sudah ada. Karena factory dan dependency injection sudah di-setup di beta0.1.3, Gemini provider seharusnya aktif **secara otomatis** setelah task 1 & 2 selesai. Task ini juga memvalidasi bahwa TIDAK ADA file yang berubah di luar scope.

---

## 3. Tujuan Teknis

- Verify Gemini muncul di startup log sebagai active provider
- Verify `POST /generate` dengan `provider="gemini"` menghasilkan text
- Verify `POST /generate` dengan `provider="ollama"` tetap berfungsi (no regression)
- Verify ZERO file berubah di endpoint, service, schemas, dan Ollama provider
- Verify graceful degradation saat GEMINI_API_KEY kosong

---

## 4. Scope

### ✅ Yang Dikerjakan

- End-to-end testing seluruh flow
- Verifikasi file yang TIDAK boleh berubah
- Test graceful degradation (no API key)
- Update `.env` dengan GEMINI_API_KEY (jika belum)

### ❌ Yang Tidak Dikerjakan

- Kode baru
- Streaming atau embedding

---

## 5. Langkah Implementasi

### Step 1: Set GEMINI_API_KEY di `.env`

```env
GEMINI_API_KEY=your-actual-api-key-here
```

### Step 2: Start server

```bash
uvicorn app.main:app --reload --port 8000
```

Startup log sekarang harus menampilkan:

```
... | AI Generative Core v0.1.1
... | Gemini API Key: configured
... | OllamaProvider initialized: http://localhost:11434 (timeout=120s)
... | GeminiProvider initialized (timeout=120s)
... | Active providers: ['ollama', 'gemini']
... | Model registry: 6 models registered
... | GeneratorService initialized with providers: ['ollama', 'gemini']
```

### Step 3: Test Gemini generate

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"provider":"gemini","model":"gemini-2.0-flash","input":"Say hello in one word"}'
```

Expected response:

```json
{
    "output": "Hello!",
    "provider": "gemini",
    "model": "gemini-2.0-flash",
    "usage": {
        "prompt_tokens": 7,
        "completion_tokens": 2,
        "total_tokens": 9
    },
    "metadata": null
}
```

### Step 4: Test Ollama masih berfungsi (no regression)

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"provider":"ollama","model":"llama3.2","input":"Say hello in one word"}'
```

Harus tetap return text dari Ollama.

### Step 5: Test graceful degradation

1. Kosongkan `GEMINI_API_KEY` di `.env`:
   ```env
   GEMINI_API_KEY=
   ```

2. Restart server

3. Startup log harus menampilkan:
   ```
   ... | Gemini API Key: not set
   ... | Gemini provider skipped: GEMINI_API_KEY not set
   ... | Active providers: ['ollama']
   ```

4. Test Gemini request → 404:
   ```bash
   curl -X POST http://localhost:8000/api/v1/generate \
     -H "Content-Type: application/json" \
     -d '{"provider":"gemini","model":"gemini-2.0-flash","input":"hi"}'
   ```

   Response:
   ```json
   {
       "error": "Provider 'gemini' not found or disabled",
       "code": "PROVIDER_NOT_FOUND"
   }
   ```

5. Ollama tetap berfungsi normal.

### Step 6: Verify zero-change proof

Pastikan file-file berikut **TIDAK berubah** dari beta0.1.3:

```bash
# These files must have ZERO modifications:
# - app/api/endpoints/generate.py
# - app/services/generator.py
# - app/providers/ollama.py
# - app/schemas/common.py
# - app/schemas/requests.py
# - app/schemas/responses.py
```

Jika menggunakan git:
```bash
git diff --name-only
# Hanya harus menampilkan:
# app/providers/__init__.py
# app/providers/gemini.py (new file)
```

### Step 7: Verify models endpoint

```bash
curl http://localhost:8000/api/v1/models?provider=gemini
```

Harus return 3 Gemini models (sudah ada dari beta0.1.2 registry defaults).

---

## 6. Output yang Diharapkan

### Validation Checklist

| Test | Expected Result |
|---|---|
| Startup log shows 2 providers | `Active providers: ['ollama', 'gemini']` |
| POST /generate Gemini | 200 + AI text |
| POST /generate Ollama | 200 + AI text (no regression) |
| No API key → Gemini disabled | 404 PROVIDER_NOT_FOUND |
| No API key → Ollama works | 200 normal |
| GET /models?provider=gemini | 3 Gemini models |
| generate.py unchanged | ✅ |
| generator.py unchanged | ✅ |
| ollama.py unchanged | ✅ |
| schemas unchanged | ✅ |

---

## 7. Dependencies

- **Task 1** — GeminiProvider implemented
- **Task 2** — Factory updated
- **Running Ollama** (untuk regression test)
- **Valid GEMINI_API_KEY** (untuk integration test)

---

## 8. Acceptance Criteria

- [ ] Server starts with 2 active providers (with API key)
- [ ] `POST /generate` provider="gemini" → 200 + AI text
- [ ] `POST /generate` provider="ollama" → 200 + AI text (no regression)
- [ ] Without API key → Gemini disabled, Ollama works
- [ ] Gemini disabled → request returns 404 (not crash)
- [ ] `generate.py` has ZERO modifications
- [ ] `generator.py` has ZERO modifications
- [ ] `ollama.py` has ZERO modifications
- [ ] `schemas/` has ZERO modifications
- [ ] Swagger UI shows "gemini" as valid provider option

---

## 9. Estimasi

**Medium** — Mostly testing, but thorough validation across multiple scenarios.
