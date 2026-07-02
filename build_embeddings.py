import json
import pickle
import numpy as np
import faiss
from fastembed import TextEmbedding

print("Loading catalog...")
with open("shl_product_catalog.json", "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()
catalog = json.loads(content, strict=False)

def make_text(item):
    name = item.get("name", "")
    description = item.get("description", "")
    keys = ", ".join(item.get("keys", []))
    job_levels = ", ".join(item.get("job_levels", []))
    return f"{name}. {description}. Categories: {keys}. Job levels: {job_levels}"

texts = [make_text(item) for item in catalog]

print("Building embeddings...")
embedding_model = TextEmbedding("BAAI/bge-small-en-v1.5")
embeddings = list(embedding_model.embed(texts))
embeddings = np.array(embeddings).astype('float32')

dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

faiss.write_index(index, "catalog_index.faiss")
with open("catalog_items.pkl", "wb") as f:
    pickle.dump(catalog, f)

print(f"Done! {len(catalog)} assessments indexed.")