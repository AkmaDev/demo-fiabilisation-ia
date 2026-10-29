"""Tests de mutation : on casse volontairement une règle de verifier.py et on vérifie qu'au moins un test échoue.

Chaque mutation est appliquée sur le vrai fichier, les tests sont lancés, puis le fichier est restauré.
Usage : python outils/mutations.py
"""
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
CIBLE = RACINE / "verifier.py"

MUTATIONS = [
    ("clé de Luhn ignorée", "    return total % 10 == 0", "    return True"),
    ("longueur du SIRET ignorée", "if len(siret) != 14 or not siret.isdigit():", "if False:"),
    ("réponse sans liste acceptée", 'raise ReponseInvalide("pas de liste de résultats")', "return []"),
    ("panne réseau acceptée", '_verdict("bloquee", f"API injoignable', '_verdict("verifiee", f"API injoignable'),
    ("SIRET introuvable accepté", '_verdict("bloquee", "SIRET introuvable', '_verdict("verifiee", "SIRET introuvable'),
    ("ambiguïté ignorée", "if len(trouves) > 1:", "if False:"),
    ("non-diffusion ignorée", 'if ent.get("statut_diffusion") != "O":', "if False:"),
    ("entreprise cessée ignorée", 'if ent.get("etat_administratif") != "A" or etab', "if etab"),
    ("SIRET approximatif accepté", 'if etab["siret"] == siret:', "if True:"),
    ("dirigeants recopiés", '"activite_principale": ent.get("activite_principale"),\n    }',
     '"activite_principale": ent.get("activite_principale"),\n        "dirigeants": ent.get("dirigeants"),\n    }'),
    ("statut forcé à « verifiee » après correction", 'return _verdict("a_corriger"', 'return _verdict("verifiee"'),
    ("proposition non écrite", 'propositions = [v["proposition"] for v in verdicts if v["proposition"]]', "propositions = []"),
    ("code de sortie toujours 0", 'return 1 if any(v["statut"] == "bloquee" for v in verdicts) else 0', "return 0"),
    ("main ignore le code de sortie", "    return code_sortie(verdicts)", "    return 0"),
]


def lancer_tests():
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x"], cwd=RACINE, capture_output=True, text=True)
    return r.returncode == 0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    original = CIBLE.read_text(encoding="utf-8")
    survivantes = []
    try:
        for nom, avant, apres in MUTATIONS:
            if original.count(avant) != 1:
                print(f"INTROUVABLE  {nom}")
                survivantes.append(nom)
                continue
            CIBLE.write_text(original.replace(avant, apres), encoding="utf-8")
            if lancer_tests():
                print(f"NON DÉTECTÉE {nom}")
                survivantes.append(nom)
            else:
                print(f"détectée     {nom}")
    finally:
        CIBLE.write_text(original, encoding="utf-8")
    print(f"\n{len(MUTATIONS) - len(survivantes)} / {len(MUTATIONS)} mutations détectées")
    return 1 if survivantes else 0


if __name__ == "__main__":
    sys.exit(main())
