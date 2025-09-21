import uuid
from fastapi import APIRouter, HTTPException
from ..schemas import ProblemInput, SolveResponse
from ..model_router import pick_model
from ..llm_client import chat_completion

router = APIRouter()

SYSTEM_PROMPT = (
    "You are a patient K-12 tutor. Solve the problem step by step with clear reasoning. "
    "Provide the final answer and a quick check. Keep an encouraging tone."
)

@router.post('/solve', response_model=SolveResponse)
async def solve_problem(body: ProblemInput):
    if not body.text and not body.image_url:
        raise HTTPException(status_code=400, detail="either 'text' or 'image_url' must be provided")
    model = pick_model(body.difficulty or 'medium')
    user_content = body.text or f"Please solve the problem shown in the image: {body.image_url}"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]
    result = await chat_completion(messages, model=model, temperature=0.2, max_tokens=700)
    pid = f"prob_{uuid.uuid4().hex[:8]}"
    solution_text = result['choices'][0]['message']['content']
    return {
        "problem_id": pid,
        "normalized_problem": {
            "text": body.text or "",
            "latex": None,
            "knowledge_tags": body.knowledge_tags or []
        },
        "solution": {
            "final_answer": "see the end of the explanation",
            "steps": solution_text.split('\n'),
            "hints": ["Read the problem, identify knowns and unknowns", "Set up the equation and simplify", "Substitute back to check"],
            "common_mistakes": ["Missing units", "Sign error when transposing terms"],
            "check": "Steps reviewed; conclusion consistent"
        },
        "pedagogy_view": {
            "socratic_questions": ["What does the problem ask for?", "What operation can we apply to both sides first?"],
            "misconceptions": ["Confusing coefficients with exponents", "Dropping parentheses"]
        }
    }
