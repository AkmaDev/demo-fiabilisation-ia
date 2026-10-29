# Registre d'erreurs

Une ligne par anomalie réellement rencontrée. Jamais supprimée : elle sert à ne jamais répéter la même erreur (voir `CLAUDE.md`).

| # | Symptôme | Cause | Test qui la protège | Règle tirée |
|---|---|---|---|---|
| 1 | Une réponse d'API sans liste de résultats était classée « SIRET introuvable » : la fiche restait bloquée, mais avec la mauvaise raison | Les tests ne vérifiaient que le statut, jamais la raison ; un humain aurait cru que l'entreprise n'existait pas alors que l'API était en panne | `test_reponse_invalide_bloque_avec_la_bonne_raison` | Un test vérifie aussi la raison d'un blocage, pas seulement le statut |
| 2 | Un établissement renvoyé par l'API était accepté même si son SIRET différait de celui saisi | La recherche de l'API est plein texte et peut renvoyer une autre entreprise ; aucune réponse fabriquée ne contenait d'autre SIRET | État « autre_entreprise » ajouté à la matrice (`tests/fabrique.py`, `test_matrice`) | Chaque comportement possible de la source a son état dans la matrice, y compris « répond, mais à côté » |
| 3 | Le code de sortie (signal « des fiches sont bloquées ») pouvait passer à 0 sans qu'aucun test échoue | Logique écrite directement dans `main`, jamais appelée par un test | `code_sortie` extraite, `test_code_de_sortie_signale_les_fiches_bloquees` | Le signal envoyé à l'humain est une règle comme les autres : il a son test |
| 4 | `main` pouvait ignorer `code_sortie` sans qu'aucun test échoue | La commande lancée en ligne de commande n'était jamais testée de bout en bout | `test_la_commande_echoue_s_il_reste_une_fiche_bloquee` (sans réseau) | Un test appelle le vrai point d'entrée, pas seulement ses fonctions internes |
