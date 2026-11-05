# -*- mode: python ; coding: utf-8 -*-
"""Spec PyInstaller officielle de TidyDeck, livree avec la source.

Elle est construite depuis n'importe quel dossier d'ou qu'on la lance : tous les
chemins sont calculs a partir de SPECPATH (le dossier de ce fichier), donc rien
ne depend du poste de compilation.

Commande (depuis la racine du depot) :
    build_env\\Scripts\\pyinstaller --noconfirm --clean ^
        "TidyDeck_v2\\TidyDeck\\packaging\\TidyDeck.spec" --distpath dist --workpath work

Ce que la spec embarque, et pourquoi :
  * vendor/  -> le module qrcode (licence BSD 3-Clause, voir vendor/qrcode/LICENSE)
  * assets/  -> tidydeck.ico : sans lui la fenetre tourne avec la plume Tk par defaut
  * console=False -> aucune fenetre de console parasite derriere l'interface
  * upx=False -> voir ci-dessous, c'est le point le plus important de ce fichier

UPX est volontairement DESACTIVE (dans EXE et dans COLLECT). UPX recolle les
binaires Python, et un binaire reconditionne de cette facon ressemble beaucoup a
un emballage de malware : c'est exactement le motif qui fait grimper le nombre de
detectations d'un utilitaire qui, lui, ne fait que lire le registre et vider des
caches. Un analyseur qui voit un packer ne prend pas le benefit du doute. On
prefere un livrable un peu plus gros et propre en analyse.
"""
import os

# SPECPATH = dossier de cette spec, donc PROJET = racine du projet TidyDeck.
PROJET = os.path.normpath(os.path.join(SPECPATH, os.pardir))
ICO = os.path.join(PROJET, "assets", "tidydeck.ico")

a = Analysis(
    [os.path.join(PROJET, "main.py")],
    pathex=[PROJET],
    binaries=[],
    datas=[
        (os.path.join(PROJET, "vendor"), "vendor"),
        (os.path.join(PROJET, "assets"), "assets"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TidyDeck",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[ICO],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="TidyDeck",
)
