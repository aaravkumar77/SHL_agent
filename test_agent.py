import requests

BASE_URL = "http://localhost:8000"

def chat(messages):
    response = requests.post(
        f"{BASE_URL}/chat",
        json={"messages": messages}
    )
    return response.json()

print("=== FULL CONVERSATION TEST ===\n")

# Turn 1: vague
messages = [
    {"role": "user", "content": "I need an assessment"}
]
result = chat(messages)
print(f"User: I need an assessment")
print(f"Agent: {result['reply']}")
print(f"Recommendations: {result['recommendations']}\n")

# Turn 2: add context
messages.append({"role": "assistant", "content": result['reply']})
messages.append({"role": "user", "content": "I am hiring a mid level Java developer"})
result = chat(messages)
print(f"User: I am hiring a mid level Java developer")
print(f"Agent: {result['reply']}")
print(f"Recommendations: {result['recommendations']}\n")

# Turn 3: give more detail
messages.append({"role": "assistant", "content": result['reply']})
messages.append({"role": "user", "content": "I want to test Java fundamentals and also their personality"})
result = chat(messages)
print(f"User: I want to test Java fundamentals and also their personality")
print(f"Agent: {result['reply']}")
print(f"Recommendations: {result['recommendations']}\n")

# Turn 4: off topic test
messages2 = [
    {"role": "user", "content": "What is the best way to fire an employee?"}
]
result2 = chat(messages2)
print(f"=== OFF TOPIC TEST ===")
print(f"User: What is the best way to fire an employee?")
print(f"Agent: {result2['reply']}")
print(f"Recommendations: {result2['recommendations']}")