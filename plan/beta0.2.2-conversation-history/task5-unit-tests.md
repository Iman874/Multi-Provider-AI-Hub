# Task 5 — Unit Tests SessionManager

## 1. Judul Task
Implementasi 12 unit tests untuk `SessionManager` service

## 2. Deskripsi
Menulis unit tests lengkap yang memvalidasi semua operasi `SessionManager`: create, add, get, delete, trimming, cleanup, build_prompt, dan edge cases. Tests menggunakan `pytest` dan mock `time.time()` untuk tes TTL expiration.

## 3. Tujuan Teknis
- 12 test cases baru di `tests/services/test_session_manager.py`
- Coverage: semua public methods `SessionManager`
- Edge case: trimming dengan/tanpa system prompt, expired cleanup, session not found
- Semua existing tests tetap PASS

## 4. Scope
### Yang dikerjakan
- `tests/services/test_session_manager.py` — file baru, 12 test functions

### Yang TIDAK dikerjakan
- Integration test endpoint (bisa ditambah nanti)
- Load testing / performance testing

## 5. Langkah Implementasi

### Step 1: Buat file `tests/services/test_session_manager.py`

```python
"""
Unit tests for SessionManager service.

Tests cover: session CRUD, message trimming, prompt building,
TTL-based cleanup, and error handling.
"""

import time
from unittest.mock import patch

import pytest

from app.core.exceptions import SessionNotFoundError
from app.services.session_manager import ChatMessage, ChatSession, SessionManager
```

### Step 2: Setup fixture
```python
@pytest.fixture
def manager():
    """Create a SessionManager with small limits for testing."""
    return SessionManager(max_history=5, ttl_minutes=1)


@pytest.fixture
def manager_default():
    """Create a SessionManager with default settings."""
    return SessionManager()
```

### Step 3: Test `create_session` (tanpa dan dengan system prompt)
```python
def test_create_session(manager: SessionManager):
    """Test basic session creation without system prompt."""
    session = manager.create_session("ollama", "llama3.2")
    assert session.session_id is not None
    assert len(session.session_id) == 36  # UUID v4 format
    assert session.provider == "ollama"
    assert session.model == "llama3.2"
    assert session.messages == []
    assert session.system_prompt is None
    assert session.created_at > 0
    assert session.last_active > 0
    assert manager.active_count == 1
```

### Step 4: Test `create_session` dengan system prompt
```python
def test_create_session_with_system_prompt(manager: SessionManager):
    """Test session creation with system prompt adds it as first message."""
    session = manager.create_session(
        "gemini", "gemini-2.5-pro", system_prompt="You are helpful"
    )
    assert session.system_prompt == "You are helpful"
    assert len(session.messages) == 1
    assert session.messages[0].role == "system"
    assert session.messages[0].content == "You are helpful"
```

### Step 5: Test `add_message_user`
```python
def test_add_message_user(manager: SessionManager):
    """Test adding a user message."""
    session = manager.create_session("ollama", "llama3.2")
    msg = manager.add_message(session.session_id, "user", "Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"
    assert msg.model is None
    assert msg.timestamp > 0
    assert len(session.messages) == 1
```

### Step 6: Test `add_message_assistant` (dengan model)
```python
def test_add_message_assistant(manager: SessionManager):
    """Test adding an assistant message with model name."""
    session = manager.create_session("ollama", "llama3.2")
    msg = manager.add_message(
        session.session_id, "assistant", "Hi there!", model="llama3.2"
    )
    assert msg.role == "assistant"
    assert msg.content == "Hi there!"
    assert msg.model == "llama3.2"
```

### Step 7: Test `history_order` (chronological)
```python
def test_history_order(manager: SessionManager):
    """Test that messages are returned in chronological order."""
    session = manager.create_session("ollama", "llama3.2")
    manager.add_message(session.session_id, "user", "First")
    manager.add_message(session.session_id, "assistant", "Second", model="llama3.2")
    manager.add_message(session.session_id, "user", "Third")

    history = manager.get_history(session.session_id)
    assert len(history) == 3
    assert history[0].content == "First"
    assert history[1].content == "Second"
    assert history[2].content == "Third"
    # Timestamps should be increasing
    assert history[0].timestamp <= history[1].timestamp <= history[2].timestamp
```

### Step 8: Test `max_history_trim` (FIFO tanpa system prompt)
```python
def test_max_history_trim(manager: SessionManager):
    """Test FIFO trimming when exceeding max_history (no system prompt)."""
    # manager has max_history=5
    session = manager.create_session("ollama", "llama3.2")

    # Add 6 messages (exceeds max of 5)
    for i in range(6):
        role = "user" if i % 2 == 0 else "assistant"
        manager.add_message(session.session_id, role, f"msg-{i}")

    history = manager.get_history(session.session_id)
    assert len(history) == 5
    # First message should be msg-1 (msg-0 was trimmed)
    assert history[0].content == "msg-1"
    # Last message should be msg-5
    assert history[-1].content == "msg-5"
```

### Step 9: Test `system_prompt_preserved` (trim with system prompt)
```python
def test_system_prompt_preserved(manager: SessionManager):
    """Test that system prompt is ALWAYS preserved at index 0 after trim."""
    # manager has max_history=5
    session = manager.create_session(
        "ollama", "llama3.2", system_prompt="Be helpful"
    )
    # Session starts with 1 message (system prompt)
    # Add 5 more messages = 6 total → exceeds max of 5

    manager.add_message(session.session_id, "user", "Q1")
    manager.add_message(session.session_id, "assistant", "A1", model="llama3.2")
    manager.add_message(session.session_id, "user", "Q2")
    manager.add_message(session.session_id, "assistant", "A2", model="llama3.2")
    manager.add_message(session.session_id, "user", "Q3")

    history = manager.get_history(session.session_id)
    assert len(history) == 5
    # System prompt MUST be at index 0
    assert history[0].role == "system"
    assert history[0].content == "Be helpful"
    # Q1 should be trimmed (oldest non-system message)
    assert history[1].content != "Q1"
    # Last should be Q3
    assert history[-1].content == "Q3"
```

### Step 10: Test `delete_session`
```python
def test_delete_session(manager: SessionManager):
    """Test session deletion."""
    session = manager.create_session("ollama", "llama3.2")
    assert manager.active_count == 1

    result = manager.delete_session(session.session_id)
    assert result is True
    assert manager.active_count == 0

    # Trying to get deleted session should raise error
    with pytest.raises(SessionNotFoundError):
        manager.get_session(session.session_id)
```

### Step 11: Test `session_not_found`
```python
def test_session_not_found(manager: SessionManager):
    """Test that accessing non-existent session raises SessionNotFoundError."""
    with pytest.raises(SessionNotFoundError) as exc_info:
        manager.get_session("non-existent-id")
    assert "non-existent-id" in str(exc_info.value.message)
    assert exc_info.value.code == "SESSION_NOT_FOUND"
```

### Step 12: Test `cleanup_expired` (mock time)
```python
def test_cleanup_expired(manager: SessionManager):
    """Test TTL-based session cleanup using mocked time."""
    # manager has ttl_minutes=1

    # Create session at current time
    session = manager.create_session("ollama", "llama3.2")
    assert manager.active_count == 1

    # Mock time to be 2 minutes in the future (past TTL of 1 minute)
    future_time = time.time() + 120  # 2 minutes later
    with patch("app.services.session_manager.time") as mock_time:
        mock_time.time.return_value = future_time
        count = manager.cleanup_expired()

    assert count == 1
    assert manager.active_count == 0
```

### Step 13: Test `build_prompt_format`
```python
def test_build_prompt_format(manager: SessionManager):
    """Test prompt builder produces correct [Role] Content format."""
    session = manager.create_session("ollama", "llama3.2")
    manager.add_message(session.session_id, "user", "Hello")
    manager.add_message(session.session_id, "assistant", "Hi!", model="llama3.2")

    prompt = manager.build_prompt(session.session_id)
    assert "[User] Hello" in prompt
    assert "[Assistant] Hi!" in prompt
    # Should be separated by double newlines
    assert "\n\n" in prompt
```

### Step 14: Test `active_count`
```python
def test_active_count(manager: SessionManager):
    """Test active_count property returns correct session count."""
    assert manager.active_count == 0

    s1 = manager.create_session("ollama", "llama3.2")
    assert manager.active_count == 1

    s2 = manager.create_session("gemini", "gemini-2.5-pro")
    assert manager.active_count == 2

    manager.delete_session(s1.session_id)
    assert manager.active_count == 1
```

### Step 15: Test `build_prompt_with_system`
```python
def test_build_prompt_with_system(manager: SessionManager):
    """Test prompt builder includes system prompt with [System] prefix."""
    session = manager.create_session(
        "ollama", "llama3.2", system_prompt="You are a poet"
    )
    manager.add_message(session.session_id, "user", "Write a poem")

    prompt = manager.build_prompt(session.session_id)
    assert prompt.startswith("[System] You are a poet")
    assert "[User] Write a poem" in prompt
    # System should come before user
    sys_idx = prompt.index("[System]")
    user_idx = prompt.index("[User]")
    assert sys_idx < user_idx
```

## 6. Output yang Diharapkan

Jalankan tests:
```bash
pytest tests/services/test_session_manager.py -v
```

Expected output:
```
tests/services/test_session_manager.py::test_create_session PASSED
tests/services/test_session_manager.py::test_create_session_with_system_prompt PASSED
tests/services/test_session_manager.py::test_add_message_user PASSED
tests/services/test_session_manager.py::test_add_message_assistant PASSED
tests/services/test_session_manager.py::test_history_order PASSED
tests/services/test_session_manager.py::test_max_history_trim PASSED
tests/services/test_session_manager.py::test_system_prompt_preserved PASSED
tests/services/test_session_manager.py::test_delete_session PASSED
tests/services/test_session_manager.py::test_session_not_found PASSED
tests/services/test_session_manager.py::test_cleanup_expired PASSED
tests/services/test_session_manager.py::test_build_prompt_format PASSED
tests/services/test_session_manager.py::test_active_count PASSED
tests/services/test_session_manager.py::test_build_prompt_with_system PASSED

13 passed
```

> **Note:** Ada 13 test functions (bukan 12) karena `test_create_session_with_system_prompt` dipecah dari `test_create_session`. Ini lebih granular dan lebih baik.

Jalankan ALL tests:
```bash
pytest -v
```
Expected: Semua existing tests PASS + 13 test baru PASS.

## 7. Dependencies
- **Task 1** — `SessionNotFoundError` exception
- **Task 2** — `SessionManager`, `ChatMessage`, `ChatSession` classes

## 8. Acceptance Criteria
- [ ] File `tests/services/test_session_manager.py` dibuat
- [ ] 13 test functions implemented (12 dari spec + 1 bonus)
- [ ] `test_create_session` — UUID generated, messages empty, metadata set
- [ ] `test_create_session_with_system_prompt` — system prompt as first message
- [ ] `test_add_message_user` — user message stored correctly
- [ ] `test_add_message_assistant` — assistant message with model field
- [ ] `test_history_order` — chronological order verified
- [ ] `test_max_history_trim` — oldest messages trimmed, count = max_history
- [ ] `test_system_prompt_preserved` — system prompt at index 0 after trim
- [ ] `test_delete_session` — session removed, re-access raises error
- [ ] `test_session_not_found` — `SessionNotFoundError` raised with correct message
- [ ] `test_cleanup_expired` — expired sessions removed (time mocked)
- [ ] `test_build_prompt_format` — `[User]`/`[Assistant]` format correct
- [ ] `test_active_count` — correct count after create/delete
- [ ] `test_build_prompt_with_system` — `[System]` prefix included
- [ ] Semua existing tests tetap PASS
- [ ] `pytest` exit code 0

## 9. Estimasi
Medium (~45 menit)
