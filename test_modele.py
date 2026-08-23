import os

from openai import OpenAI

client = OpenAI(
    base_url=os.environ["AZURE_AI_ENDPOINT"],
    api_key=os.environ["AZURE_AI_KEY"],
)

reponse = client.chat.completions.create(
    model="Phi-4-mini-instruct",
    messages=[
        {"role": "system", "content": "Tu réponds en français, en une phrase."},
        {"role": "user", "content": "Qu'est-ce que la prédiction conforme ?"},
    ],
)

print(reponse.choices[0].message.content)
print("---")
print("jetons :", reponse.usage)