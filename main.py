import json
import pickle
import re
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from groq import Groq
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Load search index and catalog
print("Loading search index...")
index = faiss.read_index("catalog_index.faiss")
with open("catalog_items.pkl", "rb") as f:
    catalog = pickle.load(f)
model = SentenceTransformer("all-MiniLM-L6-v2")

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

print("Agent ready!")

# ─── Data Models ───────────────────────────────────────────────────────────────

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

class Recommendation(BaseModel):
    name: str
    url: str
    test_type: str

class ChatResponse(BaseModel):
    reply: str
    recommendations: List[Recommendation]
    end_of_conversation: bool

# ─── Search Function ────────────────────────────────────────────────────────────

def search_catalog(query: str, top_k: int = 10):
    """Search catalog for relevant assessments"""
    query_embedding = model.encode([query])
    distances, indices = index.search(np.array(query_embedding), top_k)
    
    results = []
    for i in indices[0]:
        item = catalog[i]
        # Get test type from keys
        keys = item.get("keys", [])
        test_type = "K"  # default
        if "Personality & Behavior" in keys:
            test_type = "P"
        elif "Ability & Aptitude" in keys:
            test_type = "A"
        elif "Knowledge & Skills" in keys:
            test_type = "K"
        elif "Biodata & Situational Judgment" in keys:
            test_type = "B"
        elif "Competencies" in keys:
            test_type = "C"
        elif "Development & 360" in keys:
            test_type = "D"
        elif "Simulations" in keys:
            test_type = "S"

        results.append({
            "name": item.get("name", ""),
            "url": item.get("link", ""),
            "test_type": test_type,
            "description": item.get("description", "")[:200],
            "job_levels": item.get("job_levels", []),
            "keys": keys
        })
    return results

# ─── Agent Logic ────────────────────────────────────────────────────────────────

def run_agent(messages: List[Message]):
    """Main agent logic — decides what to do and generates response"""
    
    # Build conversation text for context
    conversation = "\n".join([f"{m.role.upper()}: {m.content}" for m in messages])
    last_user_message = messages[-1].content
    
    # Search catalog based on the full conversation context
    search_results = search_catalog(conversation, top_k=10)
    
    # Format catalog results for the prompt
    catalog_context = ""
    for i, r in enumerate(search_results, 1):
        catalog_context += f"""
{i}. Name: {r['name']}
   URL: {r['url']}
   Type: {r['test_type']}
   Categories: {', '.join(r['keys'])}
   Job Levels: {', '.join(r['job_levels'])}
   Description: {r['description']}
"""

    # System prompt — the rules the AI must follow
    system_prompt = f"""You are an SHL assessment recommender agent. You help recruiters find the right SHL assessments.

CATALOG OF AVAILABLE ASSESSMENTS (use ONLY these):
{catalog_context}

YOUR RULES:
1. CLARIFY: If the query is vague (like "I need an assessment"), ask 1-2 clarifying questions. Do NOT recommend yet.
2. RECOMMEND: Once you have enough context (job role, level, what skill to test), recommend 1-10 assessments from the catalog above ONLY.
3. REFINE: If user changes requirements mid-conversation, update recommendations accordingly.
4. COMPARE: If user asks to compare two assessments, answer using only catalog data above.
5. REFUSE: If user asks anything unrelated to SHL assessments (legal advice, general hiring, off-topic), politely refuse and redirect.
6. NEVER make up assessment names or URLs. Only use what is in the catalog above.
7. NEVER recommend on the very first vague message.

RESPONSE FORMAT:
You must respond in this exact JSON format:
{{
  "reply": "your natural language response here",
  "should_recommend": true or false,
  "recommended_indices": [1, 2, 3],
  "end_of_conversation": true or false
}}

- "should_recommend": true only when you have enough context to give a solid shortlist
- "recommended_indices": list of numbers (1-10) from the catalog above to recommend
- "end_of_conversation": true only when the user seems satisfied with recommendations
- Return ONLY the JSON, nothing else
"""

    # Call Groq LLM
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            *[{"role": m.role, "content": m.content} for m in messages]
        ],
        temperature=0.3,
        max_tokens=1000
    )
    
    raw_response = response.choices[0].message.content.strip()
    
    # Parse the JSON response
    try:
        # Extract JSON if wrapped in code blocks
        json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
        else:
            parsed = json.loads(raw_response)
    except:
        # Fallback if JSON parsing fails
        return {
            "reply": raw_response,
            "recommendations": [],
            "end_of_conversation": False
        }
    
    # Build recommendations list
    recommendations = []
    if parsed.get("should_recommend", False):
        indices = parsed.get("recommended_indices", [])
        for idx in indices:
            if 1 <= idx <= len(search_results):
                r = search_results[idx - 1]
                recommendations.append({
                    "name": r["name"],
                    "url": r["url"],
                    "test_type": r["test_type"]
                })
    
    return {
        "reply": parsed.get("reply", ""),
        "recommendations": recommendations,
        "end_of_conversation": parsed.get("end_of_conversation", False)
    }

# ─── API Endpoints ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat")
def chat(request: ChatRequest):
    result = run_agent(request.messages)
    return ChatResponse(
        reply=result["reply"],
        recommendations=[Recommendation(**r) for r in result["recommendations"]],
        end_of_conversation=result["end_of_conversation"]
    )