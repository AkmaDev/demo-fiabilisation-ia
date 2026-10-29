"""Vérifie des fiches prospects d'entreprises contre l'API publique Recherche d'entreprises.

Chaque fiche (nom, SIRET, code postal) reçoit un statut : « verifiee », « a_corriger » ou
« bloquee ». Le fichier d'entrée n'est jamais modifié : les corrections sont proposées
dans sortie/propositions.json et attendent une validation humaine.

Usage : python verifier.py data/prospects_exemple.csv [--sortie sortie]
"""
import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

API = "https://recherche-entreprises.api.gouv.fr/search"
CHAMPS_OFFICIELS = ("nom_complet", "siret", "code_postal", "commune", "activite_principale")


class ReponseInvalide(Exception):
    """La réponse de l'API n'a pas la forme attendue : on ne peut rien en conclure."""


def siret_valide(siret):
    """14 chiffres et clé de contrôle de Luhn correcte."""
    if len(siret) != 14 or not siret.isdigit():
        return False
    total = 0
    for i, c in enumerate(reversed(siret)):
        n = int(c)
        if i % 2:
            n = n * 2 - 9 if n * 2 > 9 else n * 2
        total += n
    return total % 10 == 0


def etablissements_trouves(donnees, siret):
    """Renvoie les paires (entreprise, établissement) dont le SIRET correspond exactement."""
    if not isinstance(donnees, dict) or not isinstance(donnees.get("results"), list):
        raise ReponseInvalide("pas de liste de résultats")
    trouves = []
    for ent in donnees["results"]:
        etabs = ent.get("matching_etablissements") if isinstance(ent, dict) else None
        if not isinstance(etabs, list) or not etabs:
            raise ReponseInvalide("résultat sans établissement")
        for etab in etabs:
            if not isinstance(etab, dict) or "siret" not in etab:
                raise ReponseInvalide("établissement sans SIRET")
            if etab["siret"] == siret:
                trouves.append((ent, etab))
    return trouves


def _verdict(statut, raison, officiel=None, proposition=None):
    return {"statut": statut, "raison": raison, "officiel": officiel or {}, "proposition": proposition}


def verifier_fiche(fiche, obtenir):
    """Rend le verdict d'une fiche. `obtenir(siret)` renvoie la réponse brute de l'API."""
    siret = fiche["siret"].strip()
    if not siret_valide(siret):
        return _verdict("bloquee", "SIRET mal saisi (14 chiffres et clé de contrôle attendus)")

    try:
        trouves = etablissements_trouves(obtenir(siret), siret)
    except ReponseInvalide as e:
        return _verdict("bloquee", f"réponse de l'API inexploitable : {e}")
    except Exception as e:  # réseau, délai dépassé, JSON illisible
        return _verdict("bloquee", f"API injoignable : {type(e).__name__}")

    if not trouves:
        return _verdict("bloquee", "SIRET introuvable dans la base officielle")
    if len(trouves) > 1:
        return _verdict("bloquee", "plusieurs résultats pour ce SIRET : ambigu")

    ent, etab = trouves[0]
    if ent.get("statut_diffusion") != "O":
        return _verdict("bloquee", "entreprise non diffusible : aucune donnée recopiée")
    if ent.get("etat_administratif") != "A" or etab.get("etat_administratif") != "A":
        return _verdict("bloquee", "entreprise cessée ou établissement fermé")

    officiel = {
        "nom_complet": ent.get("nom_complet"),
        "siret": etab["siret"],
        "code_postal": etab.get("code_postal"),
        "commune": etab.get("libelle_commune"),
        "activite_principale": ent.get("activite_principale"),
    }
    if fiche["code_postal"].strip() != officiel["code_postal"]:
        proposition = {
            "nom": fiche["nom"],
            "siret": siret,
            "champ": "code_postal",
            "ancienne": fiche["code_postal"].strip(),
            "nouvelle": officiel["code_postal"],
            "preuve": {"source": f"{API}?q={siret}", "date": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        }
        return _verdict("a_corriger", "code postal différent de la base officielle", officiel, proposition)

    return _verdict("verifiee", "conforme à la base officielle", officiel)


def obtenir_depuis_api(siret, session=None, delai=10):
    """Interroge l'API réelle. Toute erreur remonte et bloquera la fiche."""
    import requests

    r = (session or requests).get(API, params={"q": siret}, timeout=delai)
    r.raise_for_status()
    return r.json()


def traiter(chemin_entree, dossier_sortie, obtenir, pause=0.0):
    """Vérifie toutes les fiches, écrit rapport.csv et propositions.json. N'écrit jamais dans l'entrée."""
    with open(chemin_entree, newline="", encoding="utf-8") as f:
        fiches = list(csv.DictReader(f))

    verdicts = []
    for fiche in fiches:
        verdicts.append(verifier_fiche(fiche, obtenir))
        time.sleep(pause)

    sortie = Path(dossier_sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    with open(sortie / "rapport.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["nom", "siret_saisi", "statut", "raison", *[f"officiel_{c}" for c in CHAMPS_OFFICIELS]])
        for fiche, v in zip(fiches, verdicts):
            w.writerow([fiche["nom"], fiche["siret"], v["statut"], v["raison"], *[v["officiel"].get(c, "") for c in CHAMPS_OFFICIELS]])
    propositions = [v["proposition"] for v in verdicts if v["proposition"]]
    (sortie / "propositions.json").write_text(json.dumps(propositions, ensure_ascii=False, indent=2), encoding="utf-8")
    return verdicts


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("entree")
    p.add_argument("--sortie", default="sortie")
    args = p.parse_args(argv)

    import requests

    with requests.Session() as session:
        verdicts = traiter(args.entree, args.sortie, lambda s: obtenir_depuis_api(s, session), pause=0.2)

    for statut in ("verifiee", "a_corriger", "bloquee"):
        print(f"{statut:11} {sum(v['statut'] == statut for v in verdicts)}")
    return code_sortie(verdicts)


def code_sortie(verdicts):
    """Une fiche bloquée doit être vue par un humain : le script ne se termine pas en « succès »."""
    return 1 if any(v["statut"] == "bloquee" for v in verdicts) else 0


if __name__ == "__main__":
    sys.exit(main())
