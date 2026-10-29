# Règles du projet

Objectif : **zéro erreur silencieuse**. Une fiche fausse marquée « vérifiée » est le pire résultat possible. Toute anomalie doit soit bloquer, soit être signalée.

## 1. Données

- **Jamais de donnée inventée.** Une valeur sans source retrouvable n'est pas écrite.
- **Dans le doute, on bloque.** Réponse d'API invalide, réseau en panne, résultat ambigu : la fiche est « bloquée », jamais « vérifiée ». « Vérifiée » n'est jamais une valeur par défaut.
- **Le fichier d'entrée n'est jamais modifié.** Une correction est écrite dans `sortie/propositions.json` (champ, ancienne valeur, nouvelle valeur, preuve) et n'est appliquée qu'après validation humaine.
- **Minimisation (RGPD).** On ne recopie que les champs utiles. Les dirigeants (données personnelles) ne sont jamais recopiés. Une fiche non diffusible est bloquée sans rien recopier.

## 2. Logique de décision

- **Un statut n'est jamais forcé à la main.** Seule la fonction `verifier_fiche` rend le verdict.
- **Une correction traite la famille de cas, pas le cas signalé.** Chaque état de l'entrée est testé contre chaque état de la réponse de l'API (`tests/test_matrice.py`).

## 3. Tests

- **Toute règle de décision arrive avec un test qui échoue sans elle.** Le prouver en désactivant la règle (test de mutation).
- **Un test appelle la vraie fonction**, jamais une reconstruction de ses étapes.
- **Pas de réseau dans les tests** : les réponses d'API sont fabriquées (`tests/fabrique.py`).
- **Pas de test qui passe sans rien vérifier.**
- Les tests se relancent automatiquement après chaque modification d'un fichier `.py` (`.claude/settings.json`). S'ils échouent, la modification est refusée.

## 4. Définition de « terminé »

1. `pytest` passe avec les versions de `requirements.txt` ;
2. la matrice passe en entier ;
3. les mutations des règles modifiées sont détectées ;
4. toute anomalie réellement rencontrée est inscrite dans `ERREURS.md` (symptôme, cause, test qui la protège, règle tirée) ;
5. le compte rendu dit ce qui a été testé, ce qui ne l'a pas été, sans affirmer plus que ce qui a été vérifié.

## 5. Code et commits

- Commentaires courts : ce que fait le code et pourquoi.
- Commits au nom d'AkmaDev, sans ligne `Co-Authored-By`.
