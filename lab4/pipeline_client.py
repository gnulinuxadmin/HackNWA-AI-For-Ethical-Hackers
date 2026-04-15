# pipeline_client.py
from langchain_ollama import ChatOllama

model = ChatOllama(model="llama3.2", temperature=0)

prompt = "What is 144 divided by 12, then elevated to the power of 2?"

response = model.invoke(prompt)

print("\n--- Pipeline Output ---\n")
print(response.content)
