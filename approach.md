# SHL Assessment Recommender — Approach Document

## What I Built

A conversational AI agent that helps recruiters find the right SHL assessments through natural dialogue. Instead of keyword search, a recruiter describes what they need and the agent asks clarifying questions, then recommends relevant assessments from the SHL catalog with real URLs.

The system is a FastAPI backend with two endpoints — `GET /health` and `POST /chat`. The API is stateless — every request carries the full conversation history and returns a reply, structured recommendations (when ready), and an end of conversation flag.

**Live URL:** https://shl-agent-roy5.onrender.com

---

## Step 1 — Understanding the Problem

Before writing any code, I read all 10 conversation traces. This was the most useful thing I did early on. I noticed recruiters don't give clean structured input — they change their mind mid-conversation, volunteer information early, give partial context, or ask comparison questions. This shaped how I designed the agent's decision logic.

---

## Step 2 — Data

I downloaded the SHL product catalog JSON from the provided link. It contained 377 assessments across 8 categories:

- Ability & Aptitude
- Knowledge & Skills
- Personality & Behavior
- Competencies
- Biodata & Situational Judgment
- Assessment Exercises
- Development & 360
- Simulations

Each entry had a name, link, description, job levels, and category keys. I wrote a small exploration script to verify the data loaded correctly and understand what fields were available before building anything.

---

## Step 3 — Retrieval Setup

**Embedding model:** fastembed (BAAI/bge-small-en-v1.5)

For each of the 377 assessments, I combined the name, description, categories, and job levels into a single text block and generated a dense vector embedding. These embeddings are stored in a FAISS IndexFlatL2 index for fast similarity search.

```
text = f"{name}. {description}. Categories: {keys}. Job levels: {job_levels}"
```

I chose fastembed because it is lightweight (runs well within Render's free 512MB RAM limit), free with no API costs, and produces good semantic embeddings. An earlier attempt used sentence-transformers (all-MiniLM-L6-v2) which crashed on Render due to memory limits — switching to fastembed fixed the deployment issue.

At query time, the full conversation history is embedded and used to retrieve the top 10 most semantically similar assessments. Using the full conversation (not just the last message) means retrieval improves as the conversation progresses and more context accumulates.

I tested retrieval independently before building the agent — queried "Java developer test", "personality test for manager", "graduate verbal reasoning" and confirmed results were relevant.

---

## Step 4 — Agent Design

The agent logic runs inside the `/chat` endpoint. Every call:

1. Takes the full conversation history
2. Retrieves top 10 relevant assessments from FAISS using the full conversation as the search query
3. Formats those 10 assessments (name, URL, type, description, job levels) into a structured context block
4. Builds a system prompt with the retrieved assessments + conversation rules
5. Sends everything to Groq API (llama-3.1-8b-instant, free tier)
6. Parses the LLM's JSON response
7. Returns the final output in SHL's required schema

**The four conversational behaviors:**

- **Clarify:** If the query is vague ("I need an assessment"), the agent asks 1-2 focused questions before recommending anything. It never recommends on the first vague turn.
- **Recommend:** Once enough context is gathered (role, level, skill to test), recommends 1-10 assessments with names and catalog URLs.
- **Refine:** If the user changes requirements mid-conversation ("actually add personality tests"), the agent updates the shortlist without starting over.
- **Compare:** If asked to compare two assessments, the agent answers using only catalog data from the retrieved context — not the model's prior knowledge.
- **Refuse:** Off-topic questions (legal advice, general hiring, prompt injection) are politely declined and redirected.

**Why RAG matters here:** Without grounding, the LLM might hallucinate fake assessment names or wrong URLs. By retrieving real catalog entries first and injecting them into the prompt, the agent can only recommend assessments that actually exist in the catalog.

**Prompt design:** The system prompt tells the LLM to respond only in a strict JSON format:

```json
{
  "reply": "natural language response",
  "should_recommend": true or false,
  "recommended_indices": [1, 2, 3],
  "end_of_conversation": true or false
}
```

URLs always come from the retrieved catalog items — the LLM only picks indices, never generates URLs itself. This eliminates hallucination of links.

---

## Step 5 — Schema Compliance

SHL's evaluator checks schema compliance on every single response. A wrong format means automatic failure. I kept the output schema strict:

```json
{
  "reply": "string",
  "recommendations": [{"name": "...", "url": "...", "test_type": "..."}],
  "end_of_conversation": false
}
```

Recommendations is always an empty array when clarifying or refusing — never null or missing. The 8-turn limit is enforced by returning `end_of_conversation: true` when the conversation is complete.

---

## Step 6 — What Didn't Work

**Memory issue on Render:** First deployment used sentence-transformers which exceeded Render's 512MB free tier RAM limit and crashed on startup. Switched to fastembed which is significantly lighter and solved the problem.

**Early recommendations:** Early prompt versions sometimes recommended on the first turn even for vague queries. Fixed by adding an explicit rule in the system prompt — "never recommend on a vague first message, always clarify first."

**JSON parsing failures:** The LLM occasionally wrapped its JSON response in markdown code blocks. Fixed by using regex to extract the JSON object before parsing.

---

## Step 7 — Evaluation

Tested against all 10 public conversation traces manually — ran each persona's conversation through the live API and checked if the final shortlist overlapped with the expected assessments.

Also tested edge cases:
- Off-topic questions ("how do I fire someone?") → correctly refused
- Prompt injection attempts → correctly refused
- Mid-conversation refinements ("actually add personality tests") → shortlist updated correctly
- Comparison questions → answered using only catalog data

Response times stayed well under the 30-second timeout since the embedding model and FAISS index are loaded once at startup.

---

## Stack

| Component | Choice | Reason |
|---|---|---|
| Embeddings | fastembed (BAAI/bge-small-en-v1.5) | Lightweight, free, good semantic quality |
| Vector store | FAISS IndexFlatL2 | Fast, free, runs in memory |
| LLM | Groq API (llama-3.1-8b-instant) | Free tier, fast inference |
| Backend | FastAPI + uvicorn | Required by assignment |
| Deployment | Render (free tier) | Simple GitHub integration |
| AI tools used | Claude (Anthropic) — used for explaining concepts, scaffolding code structure, and debugging errors. All design decisions and understanding are my own. |

