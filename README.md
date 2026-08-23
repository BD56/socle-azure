# ☁️ Socle Azure : une fonction HTTP qui interroge un modèle de langage

Une Azure Function en Python qui reçoit une question et renvoie la réponse d'un modèle
de langage hébergé dans Azure AI Foundry.

Le code tient en quarante lignes. Ce qui a pris du temps, ce sont les trois murs
rencontrés en chemin sur un abonnement étudiant — c'est la partie de ce dépôt qui a
le plus de chances de servir à quelqu'un d'autre, et elle est documentée plus bas.

## Pourquoi ce projet

Je viens de la statistique et de la modélisation. Je savais entraîner un modèle et
calibrer un intervalle de confiance, je n'avais jamais rien déployé sur un cloud
d'entreprise ni appelé un modèle de langage par API. Les offres de stage que je vise
demandent les deux.

L'objectif n'était donc pas de construire quelque chose d'impressionnant, mais de
franchir une première fois toute la chaîne, de bout en bout, et de savoir ensuite de
quoi je parle. Le périmètre a été fermé avant d'écrire la première ligne : une route,
un appel, aucun secret dans le code. Tout le reste attendra le projet suivant.

## L'architecture

```
curl ──► Azure Function (Python 3.12, plan consumption, France Central)
              │
              └──► Azure AI Foundry ──► Phi-4-mini-instruct
```

Le point de terminaison de Foundry est **compatible avec l'interface d'OpenAI**
(`.../openai/v1`), ce qui a une conséquence agréable : le même code fonctionne avec
n'importe quel fournisseur exposant cette interface, y compris un modèle tournant en
local sous Ollama. Il suffit de changer deux variables. Ce n'est donc pas du code
jetable attaché à Azure.

## Reproduire

Prérequis : [uv](https://docs.astral.sh/uv/), [Azure CLI](https://learn.microsoft.com/cli/azure/),
[Azure Functions Core Tools v4](https://learn.microsoft.com/azure/azure-functions/functions-run-local),
et une ressource Azure AI Foundry avec un modèle déployé.

```bash
# 1. Environnement
uv sync

# 2. Renseigner local.settings.json : point de terminaison, clé, nom du déploiement

# 3. Vérifier l'appel au modèle, sans la couche Azure
uv run python test_modele.py

# 4. Lancer la fonction en local
source .venv/bin/activate   # indispensable : voir « L'environnement virtuel » plus bas
func start
```

```bash
curl "http://localhost:7071/api/demander?question=Bonjour"
```

Pour le déploiement. Les noms de compte de stockage et d'application de fonctions sont
uniques à l'échelle mondiale (ils deviennent des noms de domaine), d'où les
`<nom-unique>` à remplacer par les vôtres — celui du stockage n'accepte que des
minuscules et des chiffres, sans tiret.

```bash
az group create --name rg-socle-ia --location francecentral

az storage account create --name <nom-unique> --resource-group rg-socle-ia \
    --location francecentral --sku Standard_LRS

az functionapp create --resource-group rg-socle-ia \
    --consumption-plan-location francecentral --runtime python \
    --runtime-version 3.12 --functions-version 4 --os-type Linux \
    --name <nom-unique> --storage-account <nom-unique>

az functionapp config appsettings set --name <nom-unique> --resource-group rg-socle-ia \
    --settings AZURE_AI_ENDPOINT="..." AZURE_AI_KEY="..." AZURE_AI_DEPLOYMENT="..."

func azure functionapp publish <nom-unique>
```

La clé n'existe que comme paramètre d'application côté Azure et comme variable
d'environnement en local. Elle n'apparaît nulle part dans le code, et
`local.settings.json` est ignoré par git.

## Les trois murs d'un abonnement « Azure for Students »

La documentation officielle présente Azure OpenAI comme accessible aux comptes
étudiants. En pratique, voici ce que j'ai constaté en août 2026.

**1. Les modèles GPT ont un quota nul.** Dans le portail Foundry, page Quota, onglet
« Jeton par minute », interrupteur « Tout afficher » : toutes les lignes affichent
`0/0 TPM`. Le second chiffre est la capacité allouée. Ce n'est pas un quota consommé,
c'est une capacité jamais attribuée. Vérifié sur plusieurs modèles et plusieurs
régions. Le déploiement échoue avec « Quota insuffisant ».

**2. Les modèles du catalogue passant par la Place de marché sont refusés.** Tenté avec
Ministral 3B :

> Purchase failed because there is no valid payment method associated with this Azure
> subscription. […] The plan can't be purchased using a free subscription.

Un abonnement gratuit ne peut souscrire à aucune offre d'éditeur tiers, quel que soit
le crédit disponible.

**3. Les modèles publiés par Microsoft, eux, passent.** La famille Phi ne transite pas
par la Place de marché, donc ni la restriction de souscription ni les quotas Azure
OpenAI ne s'appliquent. `Phi-4-mini-instruct` en « Standard global » se déploie sans
rien demander à personne.

C'est la sortie de secours, et je ne l'ai trouvée nulle part écrite. D'où ce paragraphe.

### Deux autres pierres sur le chemin

**Le fournisseur de ressources n'est pas enregistré.** Sur un abonnement neuf,
`az functionapp create` échoue avec `MissingSubscriptionRegistration` pour
`Microsoft.Web`. Formalité : `az provider register --namespace Microsoft.Web`, puis
attendre l'état `Registered`.

**L'environnement virtuel.** `func start` utilise le Python **activé dans le terminal**,
pas celui que `uv` a créé. Sans `source .venv/bin/activate`, il tombe sur le Python 3.9
du système, `openai` reste introuvable, aucune fonction n'est enregistrée et la requête
part dans le vide. Le message affiché (« No job functions found ») ne pointe pas vers la
cause.

## Limites assumées

**Le modèle invente, et il le fait bien.** Je lui ai demandé ce qu'était la prédiction
conforme — un sujet sur lequel j'ai travaillé un an. Il a répondu trois paragraphes
assurés, en bon français, parlant d'« espaces conformes de Curie » et de « probabilités
résidentielles ». Tout est faux. Rien dans la réponse ne signale qu'il ne sait pas.
C'est la limite la plus importante de ce dépôt, et elle n'est pas corrigeable ici :
elle appelle un autre projet, sur la calibration de l'abstention.

**Il suit mal les instructions.** Consigne « réponds en une phrase », réponse de
263 jetons. C'est le prix d'un modèle de petite taille.

**Aucune gestion d'erreur.** Si le modèle est indisponible ou le quota dépassé,
l'exception remonte et la fonction renvoie un 500 au corps vide. Suffisant pour une
démonstration, inacceptable pour un service réel.

**Aucune limitation de débit.** La clé de fonction protège l'accès, rien ne protège la
facturation. Quiconque disposerait de la clé pourrait épuiser le crédit.

**Le client est créé au chargement du module.** C'est un choix : une variable manquante
fait échouer le démarrage plutôt que la première requête. En contrepartie, une
configuration incomplète se manifeste par un 500 muet — ce qui m'est arrivé, avec un
placeholder poussé à la place de la vraie clé.

**Aucun test.** Le projet est trop mince pour le justifier, mais autant l'écrire que le
laisser deviner.

## Pile technique

Python 3.12 · uv · azure-functions · openai · Azure Functions (plan consumption, Linux)
· Azure AI Foundry · Phi-4-mini-instruct · Azure CLI

## Suite

Ce socle sert de point de départ à un projet plus intéressant : une tâche de
classification confiée à un modèle de langage, avec des ensembles de prédiction
conformes et une abstention calibrée. Autrement dit, faire dire « je ne sais pas » à un
modèle avec une garantie statistique, plutôt qu'avec un seuil choisi à l'intuition. Le
paragraphe sur l'hallucination, plus haut, en est la justification.
