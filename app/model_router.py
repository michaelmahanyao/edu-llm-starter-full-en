import os

def pick_model(difficulty: str) -> str:
    diff = (difficulty or '').lower()
    if diff == 'easy':
        return os.getenv('MODEL_EASY', 'edu-fast-32k')
    if diff == 'medium':
        return os.getenv('MODEL_MEDIUM', 'edu-reasoning-8k')
    if diff == 'hard':
        return os.getenv('MODEL_HARD', 'edu-vision-8k')
    return os.getenv('MODEL_MEDIUM', 'edu-reasoning-8k')
