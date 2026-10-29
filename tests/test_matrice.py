"""Matrice : chaque état de la fiche saisie contre chaque état de la réponse de l'API.

Une correction traite la famille de cas, pas le cas signalé (CLAUDE.md, section 2).
"""
import pytest

from tests.fabrique import REPONSES, SIRET
from verifier import verifier_fiche

FICHES = {
    "fiche_correcte": {"nom": "Entreprise fictive", "siret": SIRET, "code_postal": "75011"},
    "cle_fausse": {"nom": "Entreprise fictive", "siret": SIRET[:-1] + str((int(SIRET[-1]) + 1) % 10), "code_postal": "75011"},
    "code_postal_faux": {"nom": "Entreprise fictive", "siret": SIRET, "code_postal": "75012"},
}

# Statut attendu pour chaque combinaison. Seules deux combinaisons ne sont pas bloquées.
ATTENDU = {
    ("fiche_correcte", "correcte"): "verifiee",
    ("code_postal_faux", "correcte"): "a_corriger",
}


@pytest.mark.parametrize("etat_fiche", FICHES)
@pytest.mark.parametrize("etat_api", REPONSES)
def test_matrice(etat_fiche, etat_api):
    appels = []

    def obtenir(siret):
        appels.append(siret)
        return REPONSES[etat_api]()

    verdict = verifier_fiche(FICHES[etat_fiche], obtenir)

    attendu = ATTENDU.get((etat_fiche, etat_api), "bloquee")
    assert verdict["statut"] == attendu, verdict["raison"]
    assert verdict["raison"], "chaque verdict doit dire pourquoi"
    if etat_fiche == "cle_fausse":
        assert appels == [], "un SIRET mal saisi ne doit pas interroger l'API"
    if attendu == "a_corriger":
        assert verdict["proposition"]["nouvelle"] == "75011"
    else:
        assert verdict["proposition"] is None


def test_panne_reseau_bloque():
    def obtenir(siret):
        raise ConnectionError("réseau indisponible")

    verdict = verifier_fiche(FICHES["fiche_correcte"], obtenir)
    assert verdict["statut"] == "bloquee"
