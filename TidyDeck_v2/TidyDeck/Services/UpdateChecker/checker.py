"""Vérification de mise à jour : UNIQUEMENT quand l'utilisateur clique, jamais en arrière-plan."""
import hashlib
import json
import os
import re
import urllib.request
from Shared.Utils.common import APP_VERSION
from Shared.Utils.lang import T

REPO = "TidyDeckApp/TidyDeck"   # dépôt GitHub qui publie les versions
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
_URL_ASSET = re.compile(r"^https://github\.com/" + re.escape(REPO) + r"/releases/download/[^/?#]+/[^/?#]+$")


def parse(v):
    """« 0.6.0 » / « v1.2 » / « 1.4.0-beta1 » -> tuple de nombres. Vide si pas de numéro."""
    out = []
    for morceau in re.split(r"[._\-]+", (v or "").strip().lstrip("vV")):
        m = re.match(r"^(\d+)", morceau)
        if not m:
            break
        out.append(int(m.group(1)))
    return tuple(out)


def compare(a, b):
    """>0 si a plus récent que b, 0 si identique, <0 si plus ancien. 0.10 > 0.9."""
    ta, tb = parse(a), parse(b)
    n = max(len(ta), len(tb))
    ta = ta + (0,) * (n - len(ta))
    tb = tb + (0,) * (n - len(tb))
    return (ta > tb) - (ta < tb)


def check() -> str:
    url = f"https://api.github.com/repos/{REPO}/releases/latest"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TidyDeck"})
        with urllib.request.urlopen(req, timeout=8) as r:
            tag = json.load(r).get("tag_name", "").lstrip("v")
    except Exception:
        return T("Impossible de vérifier (pas de connexion, ou dépôt non configuré).")
    if not parse(tag):
        return T("Impossible de lire la version publiée sur le dépôt.")
    if compare(tag, APP_VERSION) > 0:
        return T("Nouvelle version disponible : {v0} (tu as {v1}).").format(v0=tag, v1=APP_VERSION)
    if compare(tag, APP_VERSION) == 0:
        return T("Tu as la dernière version ({v0}).").format(v0=APP_VERSION)
    return (T("Tu as {v0}, ce qui est plus récent que la dernière version "
              "publiée ({v1}). Rien à faire.").format(v0=APP_VERSION, v1=tag))


def _fetch(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": "TidyDeck"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _est_du_depot(url) -> bool:
    """Seule la page de téléchargement du dépôt fait foi : rien d'autre."""
    return bool(_URL_ASSET.match(str(url or "")))


def latest():
    """Dernière release publiée (tag + fichiers), None si injoignable ou illisible."""
    try:
        data = json.loads(_fetch(API_URL, 8).decode("utf-8", "replace"))
    except Exception:
        return None
    tag = str(data.get("tag_name", "")).lstrip("vV")
    if not parse(tag):
        return None
    assets = [{"name": str(a.get("name", "")), "url": str(a.get("browser_download_url", "")),
               "size": int(a.get("size", 0) or 0)} for a in data.get("assets", []) if isinstance(a, dict)]
    return {"tag": tag, "assets": assets}


def verifier() -> dict:
    """État complet pour le bouton « Mises à jour » (appelé sur clic uniquement).

    statuts : maj (une version existe + fichiers vérifiables), jour (rien de neuf),
    hors_ligne (API injoignable), inverifiable (zip absent, .sha256 absent,
    ou URL qui ne vient pas du dépôt : alors on ne télécharge rien)."""
    relance = latest()
    if relance is None:
        return {"statut": "hors_ligne"}
    tag = relance["tag"]
    if compare(tag, APP_VERSION) <= 0:
        return {"statut": "jour", "tag": tag}
    zipa = next((a for a in relance["assets"] if a["name"] == f"TidyDeck-{tag}-win64.zip"), None)
    sha = next((a for a in relance["assets"] if a["name"] == f"TidyDeck-{tag}-win64.zip.sha256"), None)
    if not zipa or not sha or not _est_du_depot(zipa["url"]) or not _est_du_depot(sha["url"]):
        return {"statut": "inverifiable", "tag": tag}
    return {"statut": "maj", "tag": tag, "zip": zipa, "sha": sha}


def _place_libre(dossier, nom):
    """Jamais écraser : si le nom existe déjà, « (2) », « (3) »…"""
    base, ext = os.path.splitext(nom)
    cible = os.path.join(dossier, nom)
    n = 2
    while os.path.exists(cible):
        cible = os.path.join(dossier, f"{base} ({n}){ext}")
        n += 1
    return cible


def telecharger(dossier, zipa, sha, proges=None, annule=None) -> dict:
    """Télécharge le .sha256 d'abord, puis le zip vers un « .part », vérifie, renomme.

    Aucun fichier ne reste en cas d'échec : hash faux = supprimé (« abime »),
    annulation = supprimé (« annule »), réseau = supprimé (« reseau »).
    Retourne {"statut": ..., "chemin": ...}."""
    part = os.path.join(dossier, zipa["name"] + ".part")
    try:
        hash_attendu = _fetch(sha["url"], 15).decode("ascii", "replace").strip().split()[0].lower()
    except Exception:
        return {"statut": "reseau"}
    if not re.fullmatch(r"[0-9a-f]{64}", hash_attendu):
        return {"statut": "inverifiable"}
    h = hashlib.sha256()
    try:
        req = urllib.request.Request(zipa["url"], headers={"User-Agent": "TidyDeck"})
        with urllib.request.urlopen(req, timeout=30) as r, open(part, "wb") as fh:
            try:
                total = int(r.headers.get("Content-Length", 0) or 0)
            except ValueError:
                total = 0
            recu = 0
            while True:
                if annule and annule():
                    fh.close()
                    try:
                        os.remove(part)
                    except OSError:
                        pass
                    return {"statut": "annule"}
                chunk = r.read(65536)
                if not chunk:
                    break
                fh.write(chunk)
                h.update(chunk)
                recu += len(chunk)
                if proges:
                    proges(recu, total)
    except Exception:
        try:
            os.remove(part)
        except OSError:
            pass
        return {"statut": "reseau"}
    if h.hexdigest() != hash_attendu:
        try:
            os.remove(part)
        except OSError:
            pass
        return {"statut": "abime"}
    final = _place_libre(dossier, zipa["name"])
    os.replace(part, final)
    return {"statut": "ok", "chemin": final}
