from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Literal, Any, Dict

GradeBand = Literal['primary','middle','high']
Subject = Literal['math','physics','chemistry','biology','english','chinese','history','geography','cs']
Difficulty = Literal['easy','medium','hard']

class ProblemInput(BaseModel):
    text: Optional[str] = Field(None, description='Problem statement (Markdown/LaTeX).')
    image_url: Optional[HttpUrl] = Field(None, description='URL to an image of the problem.')
    grade_band: Optional[GradeBand] = None
    subject: Optional[Subject] = None
    knowledge_tags: Optional[List[str]] = None
    difficulty: Optional[Difficulty] = 'medium'
    require_explanation: bool = True

class SolveResponse(BaseModel):
    problem_id: str
    normalized_problem: Dict[str, Any]
    solution: Dict[str, Any]
    pedagogy_view: Dict[str, Any]

class ChatMessage(BaseModel):
    role: Literal['system','user','assistant']
    content: str

class ChatRequest(BaseModel):
    model: Optional[str] = None
    messages: List[ChatMessage]
    stream: bool = False
    temperature: float = 0.3
    max_tokens: int = 512
    pedagogy: Optional[Literal['socratic','direct','step_by_step','bilingual_zh_en','concise']] = 'step_by_step'
    grade_band: Optional[GradeBand] = None
    subject: Optional[Subject] = None

class ChatResponse(BaseModel):
    id: str
    model: str
    choices: Any
    usage: Any
