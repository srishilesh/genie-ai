import os
from openai import OpenAI

# Manually test the key used in your .env
client = OpenAI(api_key="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")

try:
    response = client.embeddings.create(
        input="Testing connection",
        model="text-embedding-3-small"
    )
    print("Success! Connection and permissions are valid.")
except Exception as e:
    print(f"Failed: {e}")