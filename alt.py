from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
import requests
import json

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (for dev)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------
# CONFIG
# ------------------------------
OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama2"

# ------------------------------
# INPUT MODELS
# ------------------------------
class TopicRequest(BaseModel):
    topic: str

class QuizRequest(BaseModel):
    topic: str
    weak_topics: Optional[List[str]] = None

class ReviewRequest(BaseModel):
    answers: List[int]  # user-selected option numbers
    questions: List[dict]  # original quiz data with correct option numbers

# ------------------------------
# HELPERS
# ------------------------------
def query_ollama(prompt: str) -> str:
    """Send a prompt to Ollama and return the generated text."""
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    response = requests.post(OLLAMA_API_URL, json=payload)
    response.raise_for_status()
    return response.json()["response"]

# ------------------------------
# ROUTES
# ------------------------------
@app.get("/")
def root():
    return {"message": "Learning API is running"}

@app.post("/generate_subtopics")
def generate_subtopics(req: TopicRequest):
    prompt = f"""
You are an educational content generator.
Topic: {req.topic}

Return JSON in the following format:
{{
    "overview": "Brief overview of the topic",
    "subtopics": [
        {{
            "name": "Subtopic Name",
            "description": "A short overview of the subtopic"
        }}
    ],
    "resources": [
        {{
            "title": "Resource Name",
            "link": "https://...",
            "type": "YouTube/Website/Course",
            "description": "Why this resource is good"
        }}
    ]
}}

Resources should be free and specific (e.g., Kaggle for Machine Learning, FreeCodeCamp, etc.)
Do not add anything outside JSON.
    """
    try:
        raw_output = query_ollama(prompt)
        return json.loads(raw_output)
    except Exception as e:
        return {"error": str(e), "raw_output": raw_output if 'raw_output' in locals() else None}

@app.post("/quiz")
def generate_quiz(req: QuizRequest):
    weak_info = ""
    if req.weak_topics:
        weak_info = f"Focus 3 out of 5 questions on these weak topics: {', '.join(req.weak_topics)}."
    prompt = f"""
Generate a quiz on the topic: {req.topic}.
{weak_info}

Return JSON in the following format:
{{
    "questions": [
        {{
            "question": "Question text",
            "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
            "correct_option": 2
        }}
    ]
}}

correct_option is the number (1-4) of the correct answer, not the full text.
Do not add explanations here.
Limit to exactly 5 questions.
    """
    try:
        raw_output = query_ollama(prompt)
        return json.loads(raw_output)
    except Exception as e:
        return {"error": str(e), "raw_output": raw_output if 'raw_output' in locals() else None}

@app.post("/review_answers")
def review_answers(req: ReviewRequest):
    prompt = f"""
You are reviewing a quiz.
Questions with correct_option numbers:
{json.dumps(req.questions)}

User answers (numbers only, same order as questions):
{req.answers}

Return JSON in the following format:
{{
    "correct_count": X,
    "incorrect_count": Y,
    "incorrect_details": [
        {{
            "question": "The question text",
            "user_answer": "User's chosen option text",
            "correct_answer": "Correct option text",
            "topic": "The topic this question belongs to",
            "explanation": "Why the correct answer is right and the user answer is wrong"
        }}
    ],
    "weak_topics": ["List of weak topics based on mistakes"]
}}
    """
    try:
        raw_output = query_ollama(prompt)
        parsed = json.loads(raw_output)

        # Ensure weak_topics contains topics of incorrect questions
        weak_topics = []
        for detail in parsed.get("incorrect_details", []):
            topic = detail.get("topic")
            if topic and topic not in weak_topics:
                weak_topics.append(topic)

        parsed["weak_topics"] = weak_topics
        return parsed

    except Exception as e:
        return {
            "error": str(e),
            "raw_output": raw_output if 'raw_output' in locals() else None
        }
