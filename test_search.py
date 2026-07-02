import pickle
import faiss
import numpy as np
from fastembed import TextEmbedding

# Load everything we built
print("Loading search index...")
index = faiss.read_index("catalog_index.faiss")
with open("catalog_items.pkl", "rb") as f:
    catalog = pickle.load(f)
model = TextEmbedding("BAAI/bge-small-en-v1.5")

def search(query, top_k=5):
    # Convert query to numbers
    query_embedding = np.array(list(model.embed([query]))).astype('float32')
    
    # Search FAISS for closest matches
    distances, indices = index.search(query_embedding, top_k)
    
    # Return the matching tests
    results = []
    for i in indices[0]:
        item = catalog[i]
        results.append({
            "name": item["name"],
            "link": item["link"],
            "keys": item.get("keys", [])
        })
    return results

# Test with some example queries
queries = [
    "Java developer programming test",
    "personality test for manager",
    "graduate entry level verbal reasoning"
]

for query in queries:
    print(f"\nQuery: '{query}'")
    print("Top matches:")
    results = search(query)
    for r in results:
        print(f"  - {r['name']} | {r['keys']}")