from fastapi import APIRouter
from ..schemas import ChatRequest, ChatResponse
from ..model_router import pick_model
from ..llm_client import chat_completion

router = APIRouter()

@router.post('/chat/completions', response_model=ChatResponse)
async def chat_completions(body: ChatRequest):
    model = body.model or pick_model('medium')
    messages = [m.model_dump() for m in body.messages]
    if body.pedagogy == 'socratic':
        messages.insert(0, {"role":"system","content":"Ask guiding questions; reveal answers only after 2-3 hints."})
    elif body.pedagogy == 'step_by_step':
        messages.insert(0, {"role":"system","content":"Explain step by step; label each step clearly."})
    result = await chat_completion(messages, model=model, temperature=body.temperature, max_tokens=body.max_tokens)
    return result
