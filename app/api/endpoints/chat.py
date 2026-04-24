"""
Chat endpoints — Multi-turn conversation with server-side history.

Provides session management for stateful AI conversations.
Sessions are stored in-memory and auto-expire after TTL.
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_generator_service, get_session_manager
from app.schemas.requests import ChatRequest, GenerateRequest
from app.schemas.responses import (
    ChatResponse,
    ChatHistoryResponse,
    ChatMessageSchema,
    ErrorResponse,
    UsageInfo,
)
from app.services.generator import GeneratorService
from app.services.session_manager import SessionManager

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Multi-turn chat conversation",
    description="Send a message in a conversation. "
    "If session_id is null, a new session is created. "
    "If session_id is provided, the existing session is continued.",
    responses={
        404: {"model": ErrorResponse, "description": "Session not found or expired"},
        502: {"model": ErrorResponse, "description": "Provider connection error"},
        504: {"model": ErrorResponse, "description": "Provider timeout"},
    },
)
async def chat(
    request: ChatRequest,
    generator: GeneratorService = Depends(get_generator_service),
    session_mgr: SessionManager = Depends(get_session_manager),
) -> ChatResponse:
    """
    Handle a chat turn: create/continue session, generate AI response.

    Flow:
    1. Create new session or get existing session
    2. Add user message to session history
    3. Build prompt from full history
    4. Call GeneratorService with full context prompt
    5. Add assistant response to session history
    6. Return ChatResponse with session metadata
    """
    # 1. Create or continue session
    if request.session_id is None:
        # New session
        session = session_mgr.create_session(
            provider=request.provider.value,
            model=request.model,
            system_prompt=request.system_prompt,
        )
    else:
        # Continue existing session
        session = session_mgr.get_session(request.session_id)

    session_id = session.session_id

    # 2. Add user message to history
    session_mgr.add_message(session_id, "user", request.message)

    # 3. Build prompt from full history
    prompt = session_mgr.build_prompt(session_id)

    # 4. Call generator with full context
    generate_request = GenerateRequest(
        provider=request.provider,
        model=request.model,
        input=prompt,
    )
    result = await generator.generate(generate_request)

    # 5. Add assistant response to history
    session_mgr.add_message(
        session_id, "assistant", result.output, model=result.model
    )

    # 6. Return response
    return ChatResponse(
        session_id=session_id,
        output=result.output,
        provider=result.provider,
        model=result.model,
        usage=result.usage,
        turn_count=len(session_mgr.get_history(session_id)),
        metadata=result.metadata,
    )


@router.get(
    "/chat/{session_id}/history",
    response_model=ChatHistoryResponse,
    summary="Get chat session history",
    description="Retrieve the full conversation history for a session.",
    responses={
        404: {"model": ErrorResponse, "description": "Session not found or expired"},
    },
)
async def get_chat_history(
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager),
) -> ChatHistoryResponse:
    """Return full conversation history for a session."""
    session = session_mgr.get_session(session_id)
    messages = [
        ChatMessageSchema(
            role=msg.role,
            content=msg.content,
            timestamp=msg.timestamp,
            model=msg.model,
        )
        for msg in session.messages
    ]
    return ChatHistoryResponse(
        session_id=session.session_id,
        provider=session.provider,
        model=session.model,
        messages=messages,
        created_at=session.created_at,
        last_active=session.last_active,
        turn_count=len(session.messages),
    )


@router.delete(
    "/chat/{session_id}",
    summary="Delete chat session",
    description="Delete a chat session and its history.",
    responses={
        404: {"model": ErrorResponse, "description": "Session not found or expired"},
    },
)
async def delete_chat_session(
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager),
) -> dict:
    """Delete a chat session."""
    session_mgr.delete_session(session_id)
    return {
        "status": "deleted",
        "session_id": session_id,
    }
