import json
import re

# Load the file
with open("shl_product_catalog.json", "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

# Try parsing with strict=False (allows control characters)
catalog = json.loads(content, strict=False)

# See how many tests are in it
print(f"Total assessments: {len(catalog)}")
print("\nFirst item name:", catalog[0]["name"])
print("First item link:", catalog[0]["link"])

# Show all unique test types/keys
all_keys = set()
for item in catalog:
    for key in item.get("keys", []):
        all_keys.add(key)

print("\nAll test categories in catalog:")
for key in sorted(all_keys):
    print(" -", key)