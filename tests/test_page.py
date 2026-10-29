"""Garde-fous de la page web : elle doit exécuter verifier.py lui-même, jamais une copie de sa logique."""
import ast
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "index.html").read_text(encoding="utf-8")


def test_la_page_charge_le_vrai_verifier():
    assert 'fetch("verifier.py")' in PAGE
    assert "verifier.verifier_fiche(" in PAGE
    assert "verifier.siret_valide" in PAGE


def test_la_page_ne_reimplemente_pas_les_regles():
    # Les verdicts ne doivent sortir que de verifier.py : la page ne les écrit jamais elle-même.
    for statut in ('"verifiee"', '"a_corriger"', '"bloquee"'):
        assert f"statut = {statut}" not in PAGE and f"statut: {statut}" not in PAGE


def test_verifier_ne_charge_que_la_bibliotheque_standard():
    # Sinon il ne se chargerait pas dans le navigateur (Pyodide n'a pas `requests`).
    arbre = ast.parse((RACINE / "verifier.py").read_text(encoding="utf-8"))
    imports = set()
    for noeud in arbre.body:
        if isinstance(noeud, ast.Import):
            imports.update(a.name.split(".")[0] for a in noeud.names)
        elif isinstance(noeud, ast.ImportFrom):
            imports.add(noeud.module.split(".")[0])
    assert imports <= set(sys.stdlib_module_names), imports - set(sys.stdlib_module_names)
