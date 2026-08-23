import os

import azure.functions as func
from openai import OpenAI

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

client = OpenAI(
    base_url=os.environ["AZURE_AI_ENDPOINT"],
    api_key=os.environ["AZURE_AI_KEY"],
)

MODELE = os.environ.get("AZURE_AI_DEPLOYMENT", "Phi-4-mini-instruct")


@app.route(route="demander")
def demander(req: func.HttpRequest) -> func.HttpResponse:
    question = req.params.get("question")
    if question is None:
        try:
            question = (req.get_json() or {}).get("question")
        except ValueError:
            question = None

    if not question:
        return func.HttpResponse(
            'Paramètre manquant : ?question=... ou un corps JSON {"question": "..."}.',
            status_code=400,
        )

    reponse = client.chat.completions.create(
        model=MODELE,
        messages=[
            {"role": "system", "content": "Tu réponds en français, brièvement."},
            {"role": "user", "content": question},
        ],
    )

    return func.HttpResponse(
        reponse.choices[0].message.content,
        mimetype="text/plain; charset=utf-8",
    )