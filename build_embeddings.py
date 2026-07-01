import json
import re
import pickle
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

print("Loading catalog...")
with open("shl_product_catalog.json", "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()
catalog = json.loads(content, strict=False)

print(f"Loaded {len(catalog)} assessments")

# For each assessment, combine its info into one searchable text
def make_text(item):
    name = item.get("name", "")
    description = item.get("description", "")
    keys = ", ".join(item.get("keys", []))
    job_levels = ", ".join(item.get("job_levels", []))
    return f"{name}. {description}. Categories: {keys}. Job levels: {job_levels}"

texts = [make_text(item) for item in catalog]

print("Building embeddings (this takes 1-2 minutes)...")
model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode(texts, show_progress_bar=True)

# Store in FAISS (vector search database)
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(np.array(embeddings))

# Save everything for later use
faiss.write_index(index, "catalog_index.faiss")
with open("catalog_items.pkl", "wb") as f:
    pickle.dump(catalog, f)

print("\nDone! Saved:")
print(" - catalog_index.faiss (the search index)")
print(" - catalog_items.pkl (the catalog data)")
print("\nYou can now search through 377 assessments smartly!")