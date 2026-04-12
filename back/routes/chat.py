from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from ..services.chat_service import ChatService
from ..dependencies.chat_dependencies import get_chat_service
from ..dependencies.auth_dependencies import get_current_user
from ..auth.entities.user import User as DomainUser

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("/message")
async def chat_message(
    request: Request,
    chat_service: ChatService = Depends(get_chat_service),
    current_user: DomainUser | None = Depends(get_current_user)
):
    data = await request.json()
    message = data.get("message", "")
    model = data.get("model")
    session_id = request.cookies.get("sessionid")

    if not message:
        return JSONResponse({"success": False, "error": "Message is required"}, status_code=400)

    result = await chat_service.process_message(
        message=message,
        user_id=current_user.id if current_user else None,
        session_id=session_id,
        model=model
    )
    return JSONResponse(result)

@router.post("/message/stream")
async def chat_message_stream(
    request: Request,
    chat_service: ChatService = Depends(get_chat_service),
    current_user: DomainUser | None = Depends(get_current_user)
):
    data = await request.json()
    message = data.get("message", "")
    model = data.get("model")
    session_id = request.cookies.get("sessionid")

    if not message:
        return JSONResponse({"success": False, "error": "Message is required"}, status_code=400)

    async def generate():
        async for chunk in chat_service.process_message_stream(
            message=message,
            user_id=current_user.id if current_user else None,
            session_id=session_id,
            model=model
        ):
            yield chunk

    return StreamingResponse(generate(), media_type="text/event-stream")

@router.get("/history")
async def get_chat_history(
    request: Request,
    chat_service: ChatService = Depends(get_chat_service),
    current_user: DomainUser | None = Depends(get_current_user)
):
    session_id = request.cookies.get("sessionid")
    history = await chat_service._get_chat_history(
        user_id=current_user.id if current_user else None,
        session_id=session_id
    )
    return JSONResponse({"success": True, "history": history})

@router.delete("/history")
async def clear_chat_history(
    request: Request,
    chat_service: ChatService = Depends(get_chat_service),
    current_user: DomainUser | None = Depends(get_current_user)
):
    session_id = request.cookies.get("sessionid")
    success = await chat_service.clear_history(
        user_id=current_user.id if current_user else None,
        session_id=session_id
    )
    return JSONResponse({"success": success})


