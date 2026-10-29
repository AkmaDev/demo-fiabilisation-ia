# Fiabiliser des données produites avec une IA

Une démonstration courte : comment empêcher un outil de données, écrit par un agent IA, d'afficher une information fausse comme « vérifiée ».

**👉 [Essayer dans le navigateur](https://akmadev.github.io/demo-fiabilisation-ia/)**, sans rien installer. La page exécute le fichier `verifier.py` testé ici, tel quel (avec [Pyodide](https://pyodide.org), Python dans le navigateur) : aucune logique n'est réécrite en JavaScript, et un test (`tests/test_page.py`) y veille.

**Le cas** : un agent IA de prospection cherche des entreprises sur le web et produit des fiches (nom, SIRET, code postal) pour une équipe commerciale. Avant qu'un commercial s'en serve, `verifier.py` compare ce que l'IA affirme à la base officielle (API publique [Recherche d'entreprises](https://recherche-entreprises.api.gouv.fr), données SIRENE) et range chaque fiche en **vérifiée**, **à corriger** ou **bloquée**.

**Qui fait quoi** : le code et les tests sont écrits par un agent IA (Claude Code). Je cadre le travail, j'écris les règles, je vérifie les résultats et je décide de ce qui est accepté.

## L'IA est contrôlée à deux endroits

| Où | Ce que l'IA peut faire de travers | Ce qui le rattrape |
|---|---|---|
| **Dans les données qu'elle produit** | Inventer une entreprise ou un SIRET, donner une information périmée, confondre deux entreprises, se tromper d'adresse, mal recopier un numéro | Le vérificateur : chaque fiche est comparée à la base officielle, et bloquée en cas de doute |
| **Dans le code qu'elle écrit** | Des tests « au vert » qui ne protègent pas tout | Les tests de mutation : on casse le code exprès pour vérifier que les tests le remarquent |

| Erreur typique d'un agent IA | Fiche d'exemple ou test qui la reproduit | Résultat |
|---|---|---|
| Entreprise inventée (hallucination) | « Entreprise inventée par l'agent » | bloquée : SIRET introuvable |
| Information périmée | Camaïeu (cessée fin 2023) | bloquée : entreprise cessée |
| Adresse erronée | Fnac Darty, code postal 75001 | à corriger : 94200, avec la preuve |
| Numéro mal recopié | « Doctolib (dernier chiffre faux) » | bloquée avant même d'interroger la base |
| Zéro initial perdu à l'export | « Fnac Darty (SIRET tronqué à l'export) » | bloquée : 13 chiffres |
| Confusion avec une autre entreprise : la recherche renvoie un autre SIRET | état « autre_entreprise » de la matrice de tests | bloquée : SIRET différent |
| Confusion avec une autre entreprise : le nom d'une entreprise avec le SIRET d'une autre | « BlaBlaCar » avec le SIRET de Doctolib | bloquée : le nom ou le SIRET est faux, noms officiels affichés |

Les fiches d'exemple n'ont pas été produites par un vrai agent : elles ont été construites à la main pour reproduire ces erreurs typiques, sur des entreprises dont les données sont publiques.

## Le circuit

```mermaid
flowchart LR
  A[Règles<br/>CLAUDE.md] --> B[L'agent IA<br/>écrit le code]
  B --> C[Tests relancés<br/>à chaque modification]
  C -- un test échoue --> D[Modification refusée]
  C --> E[Tests de mutation :<br/>on casse le code exprès]
  E -- défaut non détecté --> F[Registre ERREURS.md<br/>+ nouveau test]
  F --> B
```

## Les règles (extrait de [CLAUDE.md](CLAUDE.md))

- **Dans le doute, on bloque.** API en panne, réponse ambiguë, entreprise fermée : la fiche est bloquée, jamais « vérifiée ».
- **Le fichier saisi n'est jamais modifié.** Une correction est proposée dans `sortie/propositions.json`, avec l'ancienne valeur, la nouvelle et la preuve. Un humain la valide.
- **Minimisation (RGPD).** On ne recopie que les champs utiles, jamais les dirigeants. Une entreprise non diffusible est bloquée sans rien recopier.
- **Le nom doit correspondre au SIRET.** Il est comparé, après normalisation (majuscules, accents, ponctuation, formes juridiques), à tous les noms officiels : raison sociale, nom complet, sigle, enseignes et nom commercial de l'établissement. L'égalité est stricte : « contenu dans » accepterait d'autres entités (« Leboncoin » pour CSE LEBONCOIN). Un nom incohérent bloque la fiche sans rien proposer, car on ne sait pas lequel du nom ou du SIRET est faux.
- **Toute règle a un test qui échoue sans elle**, prouvé par un test de mutation.

## Ce qui a été vérifié (29/10/2026)

| Contrôle | Résultat |
|---|---|
| Tests automatiques (`pytest`) | 74 tests passent, sans aucun appel réseau |
| Matrice de pannes ([tests/test_matrice.py](tests/test_matrice.py)) | 5 états de fiche × 8 états de réponse de l'API, soit 40 combinaisons, chacune avec son statut attendu |
| Tests de mutation ([outils/mutations.py](outils/mutations.py)) | **Premier passage : 10 sur 13 détectées.** Les trous ont été fermés et inscrits au [registre](ERREURS.md) ; passage suivant : 14 sur 14. Après l'ajout de la règle du nom : **19 sur 19** |
| Hook (`.claude/settings.json`) | Avec le défaut de démonstration ci-dessous, 2 tests échouent et la modification est refusée |
| Exécution réelle sur [data/prospects_exemple.csv](data/prospects_exemple.csv) (8 fiches) | 2 vérifiées, 1 à corriger, 5 bloquées ; fichier d'entrée inchangé (empreinte identique) |
| Page web (Chrome sans interface, en local) | Même résultat que le script sur les 8 fiches |

Le premier passage des mutations a montré que des tests « au vert » ne protégeaient pas tout : une API en panne pouvait se faire passer pour un SIRET inexistant, et un établissement au SIRET différent pouvait être accepté. **Une relecture externe a ensuite trouvé un trou que les mutations ne pouvaient pas voir**, parce que la règle n'existait pas : le nom n'était jamais comparé, et « BlaBlaCar » avec le SIRET de Doctolib sortait « vérifiée » (registre, n° 5). Une mutation ne teste que les règles écrites ; une relecture indépendante reste nécessaire.

## Lancer

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # sous Linux/macOS : .venv/bin/python
.venv/Scripts/python -m pytest -q
.venv/Scripts/python verifier.py data/prospects_exemple.csv
.venv/Scripts/python outils/mutations.py
```

Le script se termine avec le code 1 s'il reste une fiche bloquée : elle doit être vue par un humain.

## Le défaut de démonstration

Dans `verifier.py`, remplacer `return _verdict("a_corriger"` par `return _verdict("verifiee"`. C'est le défaut le plus grave possible : une fiche à corriger présentée comme vérifiée. Les tests le détectent et le hook refuse la modification.

## Limites

- Les tests utilisent des réponses d'API fabriquées. Un changement de format de l'API réelle serait bloqué (réponse inexploitable), mais n'est pas testé contre l'API réelle elle-même.
- L'exécution réelle a porté sur 8 fiches d'exemple.
- **Les noms commerciaux non déclarés sont bloqués à tort.** Exemple réel : la société qui exploite Leboncoin s'appelle LBC FRANCE et la base ne lui connaît aucune enseigne « LEBONCOIN » ; une fiche « Leboncoin » juste serait bloquée. C'est un choix assumé : une fausse alerte coûte une vérification humaine, alors qu'une fausse confirmation fait contacter la mauvaise entreprise.
- Les mutations sont écrites à la main ; elles ne couvrent que les règles listées dans `outils/mutations.py`.
- Le vérificateur ne contrôle que ce qui existe dans la base officielle (identité, état, code postal). Une information que la base ne contient pas (un téléphone, un nom de contact) ne peut pas être vérifiée par cet outil.
