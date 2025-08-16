from fastapi import FastAPI
from pydantic import BaseModel
import requests
import json
from typing import List
from fastapi.middleware.cors import CORSMiddleware
import random
import re

app = FastAPI()

# Enable CORS for frontend use
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility function to query Ollama
def query_ollama(prompt: str, model: str = "llama2") -> str:
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            }
        )
        response.raise_for_status()
        data = response.json()

        if "response" not in data:
            return json.dumps({
                "error": "Missing 'response' key in Ollama output.",
                "raw": data
            })

        return data["response"]

    except requests.exceptions.RequestException as e:
        return json.dumps({"error": "Request to Ollama failed", "details": str(e)})
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON returned by Ollama", "raw": response.text})


# Function to extract JSON array from text
def extract_json_block(text: str) -> str:
    match = re.search(r'(\[\s*{.*?}\s*\])', text, re.DOTALL)
    return match.group(1) if match else text


# ========== MODELS ==========
class TopicRequest(BaseModel):
    topic: str

class SubtopicRequest(BaseModel):
    subtopic: str

class AnswerRecord(BaseModel):
    subtopic: str
    is_correct: bool


# ========== ENDPOINTS ==========

@app.post("/generate_subtopics")
def generate_subtopics(request: TopicRequest):
    prompt = f"""
    List 4–5 important subtopics of the topic: "{request.topic}".

    For each subtopic, include:
    - "title": the subtopic name
    - "summary": a short 2-line summary

    ⚠️ IMPORTANT:
    - Output should be a pure JSON array
    - No explanations or text before/after
    - Like this:

    [
      {{
        "title": "Subtopic Name",
        "summary": "Brief summary."
      }},
      ...
    ]
    """

    output = query_ollama(prompt)

    try:
        json_text = extract_json_block(output)
        return json.loads(json_text)
    except Exception as e:
        return {
            "error": "Ollama response was not valid JSON",
            "details": str(e),
            "raw_response": output
        }


@app.post("/generate_mcqs")
def generate_mcqs(request: SubtopicRequest):
    prompt = f"""
    Generate exactly 5 multiple choice questions for the subtopic: "{request.subtopic}".

    For each question, include:
    - "question": the question text
    - "correct_answer": the correct answer
    - "wrong_options": list of 3 incorrect options

    ⚠️ IMPORTANT:
    - Respond ONLY with valid JSON array
    - No explanations or text before/after
    - Format:

    [
      {{
        "question": "...",
        "correct_answer": "...",
        "wrong_options": ["...", "...", "..."]
      }},
      ...
    ]
    """

    output = query_ollama(prompt)

    try:
        json_text = extract_json_block(output)
        raw_mcqs = json.loads(json_text)

        formatted_mcqs = []
        for item in raw_mcqs:
            correct = item["correct_answer"]
            wrongs = item["wrong_options"]
            options = wrongs + [correct]
            random.shuffle(options)

            formatted_mcqs.append({
                "question": item["question"],
                "options": options,
                "answer": correct
            })

        return formatted_mcqs

    except Exception as e:
        return {
            "error": "Ollama response was not valid JSON or parsing failed",
            "details": str(e),
            "raw_response": output
        }


@app.post("/analyze_weakness")
def analyze_weakness(answers: List[AnswerRecord]):
    mistake_count = {}

    for ans in answers:
        if not ans.is_correct:
            mistake_count[ans.subtopic] = mistake_count.get(ans.subtopic, 0) + 1

    weak_topics = [sub for sub, count in mistake_count.items() if count >= 2]

    return {"weak_topics": weak_topics}

