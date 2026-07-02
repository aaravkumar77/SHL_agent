import requests

BASE_URL = "https://shl-agent-roy5.onrender.com"

def chat(messages):
    response = requests.post(
        f"{BASE_URL}/chat",
        json={"messages": messages}
    )
    # Print status code and raw response to see what's happening
    print(f"Status code: {response.status_code}")
    print(f"Raw response: {response.text}")
    return response.json()

# Test vague query
messages = [
    {"role": "user", "content": "I need an assessment"}
]
result = chat(messages)
print(result)