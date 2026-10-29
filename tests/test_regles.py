"""Règles unitaires : clé de contrôle, réponses invalides, minimisation, entrée intacte."""
import csv
import hashlib
import json

import pytest

from tests.fabrique import SIRET, entreprise, etablissement, reponse
from verifier import code_sortie, siret_valide, traiter, verifier_fiche


@pytest.mark.parametrize(
    "siret, attendu",
    [
        (SIRET, True),
        ("79459881300077", True),  # Doctolib, siège (donnée publique)
        (SIRET[:-1] + str((int(SIRET[-1]) + 1) % 10), False),  # une faute de frappe
        (SIRET[:13], False),  # 13 chiffres : un zéro initial perdu par un tableur
        ("1234 5678 9000", False),
        ("", False),
    ],
)
def test_siret_valide(siret, attendu):
    assert siret_valide(siret) is attendu


@pytest.mark.parametrize(
    "donnees",
    [
        None,
        [],
        {"results": "pas une liste"},
        {"results": [{"siren": "123"}]},  # pas d'établissements
        {"results": [{"matching_etablissements": [{"code_postal": "75011"}]}]},  # pas de SIRET
    ],
)
def test_reponse_invalide_bloque_avec_la_bonne_raison(donnees):
    fiche = {"nom": "x", "siret": SIRET, "code_postal": "75011"}
    verdict = verifier_fiche(fiche, lambda s: donnees)
    assert verdict["statut"] == "bloquee"
    # Une API cassée ne doit pas se faire passer pour un SIRET inexistant.
    assert verdict["raison"].startswith("réponse de l'API inexploitable"), verdict["raison"]


@pytest.mark.parametrize(
    "statuts, attendu",
    [(["verifiee", "a_corriger"], 0), (["verifiee", "bloquee"], 1), ([], 0)],
)
def test_code_de_sortie_signale_les_fiches_bloquees(statuts, attendu):
    assert code_sortie([{"statut": s} for s in statuts]) == attendu


def test_officiel_ne_contient_que_les_champs_utiles():
    fiche = {"nom": "x", "siret": SIRET, "code_postal": "75011"}
    verdict = verifier_fiche(fiche, lambda s: reponse(entreprise([etablissement()])))
    assert verdict["statut"] == "verifiee"
    assert set(verdict["officiel"]) == {"nom_complet", "siret", "code_postal", "commune", "activite_principale"}


def test_non_diffusible_ne_recopie_rien():
    fiche = {"nom": "x", "siret": SIRET, "code_postal": "75011"}
    verdict = verifier_fiche(fiche, lambda s: reponse(entreprise([etablissement()], diffusion="P")))
    assert verdict["statut"] == "bloquee"
    assert verdict["officiel"] == {}


def test_la_commande_echoue_s_il_reste_une_fiche_bloquee(tmp_path, monkeypatch):
    import verifier

    entree = _ecrire_entree(tmp_path, [
        {"nom": "ok", "siret": SIRET, "code_postal": "75011"},
        {"nom": "faute de frappe", "siret": SIRET[:13], "code_postal": "75011"},
    ])
    monkeypatch.setattr(verifier, "obtenir_depuis_api", lambda s, session=None: reponse(entreprise([etablissement()])))
    monkeypatch.setattr(verifier.time, "sleep", lambda s: None)
    assert verifier.main([str(entree), "--sortie", str(tmp_path / "sortie")]) == 1


def _ecrire_entree(dossier, lignes):
    chemin = dossier / "prospects.csv"
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["nom", "siret", "code_postal"])
        w.writeheader()
        w.writerows(lignes)
    return chemin


def test_traiter_ne_modifie_pas_l_entree_et_ne_recopie_pas_les_dirigeants(tmp_path):
    entree = _ecrire_entree(tmp_path, [
        {"nom": "ok", "siret": SIRET, "code_postal": "75011"},
        {"nom": "cp faux", "siret": SIRET, "code_postal": "75012"},
    ])
    empreinte = hashlib.sha256(entree.read_bytes()).hexdigest()

    verdicts = traiter(entree, tmp_path / "sortie", lambda s: reponse(entreprise([etablissement()])))

    assert hashlib.sha256(entree.read_bytes()).hexdigest() == empreinte
    assert [v["statut"] for v in verdicts] == ["verifiee", "a_corriger"]
    rapport = (tmp_path / "sortie" / "rapport.csv").read_text(encoding="utf-8")
    assert "DUPONT" not in rapport and "dirigeant" not in rapport.lower()
    propositions = json.loads((tmp_path / "sortie" / "propositions.json").read_text(encoding="utf-8"))
    assert len(propositions) == 1
    p = propositions[0]
    assert (p["champ"], p["ancienne"], p["nouvelle"]) == ("code_postal", "75012", "75011")
    assert p["preuve"]["source"].startswith("https://recherche-entreprises.api.gouv.fr")
