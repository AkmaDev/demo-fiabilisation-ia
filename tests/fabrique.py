"""Réponses fabriquées de l'API Recherche d'entreprises, pour tester sans réseau.

Les SIRET sont fictifs mais ont une clé de contrôle valide.
"""


def avec_cle(debut13):
    """Complète 13 chiffres avec le 14e qui rend la clé de Luhn valide."""
    for d in "0123456789":
        s = debut13 + d
        total = 0
        for i, c in enumerate(reversed(s)):
            n = int(c)
            if i % 2:
                n = n * 2 - 9 if n * 2 > 9 else n * 2
            total += n
        if total % 10 == 0:
            return s
    raise ValueError(debut13)


SIRET = avec_cle("1234567800001")
AUTRE_SIRET = avec_cle("9876543200001")


def etablissement(siret=SIRET, code_postal="75011", etat="A"):
    return {
        "siret": siret,
        "code_postal": code_postal,
        "libelle_commune": "PARIS",
        "etat_administratif": etat,
    }


def entreprise(etabs, etat="A", diffusion="O"):
    return {
        "siren": etabs[0]["siret"][:9],
        "nom_complet": "ENTREPRISE FICTIVE",
        "activite_principale": "62.01Z",
        "etat_administratif": etat,
        "statut_diffusion": diffusion,
        "dirigeants": [{"nom": "DUPONT", "prenoms": "JEANNE"}],
        "matching_etablissements": etabs,
    }


def reponse(*entreprises):
    return {"results": list(entreprises), "total_results": len(entreprises)}


# Les états possibles de la réponse de l'API, pour la matrice.
REPONSES = {
    "correcte": lambda: reponse(entreprise([etablissement()])),
    "zero_resultat": lambda: reponse(),
    # La recherche de l'API est plein texte : elle peut renvoyer une autre entreprise.
    "autre_entreprise": lambda: reponse(entreprise([etablissement(siret=AUTRE_SIRET)])),
    "plusieurs_resultats": lambda: reponse(
        entreprise([etablissement()]), entreprise([etablissement()])
    ),
    "etablissement_ferme": lambda: reponse(entreprise([etablissement(etat="F")])),
    "entreprise_cessee": lambda: reponse(entreprise([etablissement()], etat="C")),
    "non_diffusible": lambda: reponse(entreprise([etablissement()], diffusion="P")),
    "reponse_invalide": lambda: {"erreur": "format inattendu"},
}
