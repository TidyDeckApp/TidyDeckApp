"""Débloat Windows : désinstallation des applications préinstallées inutiles.

RÈGLE : réservé au mode avancé. On ne désinstalle que ce qui est RÉELLEMENT installé
et reconnu. Les applis tierces sponsorisées (Candy Crush, Spotify, Netflix…) ont des
identifiants opaques qui changent selon la région : ils ne sont PAS codés en dur, on
les apparie par mot-clé sur la liste des paquets réellement présents sur la machine.
"""
import re
from Shared.Utils.common import IS_WINDOWS, run_ps
from Shared.Utils.lang import T

# Le nom d'un paquet AppX ne contient que des lettres, des chiffres, des points et des
# tirets. On valide AVANT toute insertion dans une commande PowerShell : une quote, un
# point-virgule, un "$" ou un backtick ne peuvent donc pas passer, et l'injection de
# commande est impossible quelle que soit la source du nom.
PKG_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-]{0,127}$")


def valid_name(pkg):
    return isinstance(pkg, str) and bool(PKG_NAME_RE.match(pkg))

# Applis Microsoft préinstallées, identifiants stables.
KNOWN = [
    ("Actualités", ["Microsoft.BingNews"]),
    ("Météo", ["Microsoft.BingWeather"]),
    ("Astuces", ["Microsoft.Getstarted"]),
    ("Obtenir de l'aide", ["Microsoft.GetHelp"]),
    ("Hub de commentaires", ["Microsoft.WindowsFeedbackHub"]),
    ("Solitaire Collection", ["Microsoft.MicrosoftSolitaireCollection"]),
    ("Hub Microsoft 365", ["Microsoft.MicrosoftOfficeHub"]),
    ("Clipchamp", ["Clipchamp.Clipchamp"]),
    ("Power Automate", ["Microsoft.PowerAutomateDesktop"]),
    ("Skype", ["Microsoft.SkypeApp"]),
    ("Visionneuse 3D, Print 3D, Portail de réalité mixte",
     ["Microsoft.Microsoft3DViewer", "Microsoft.Print3D", "Microsoft.MixedReality.Portal"]),
    ("Cortana (abandonnée)", ["Microsoft.549981C3F5F10"]),
]

# Applis tierces sponsorisées : identifiants variables selon la région/machine.
# On ne code PAS le nom complet, on cherche ces mots-clés dans les paquets installés.
THIRD_PARTY = [
    "candy crush", "candycrush", "candy saga", "candysaga", "king.com", "king.",
    "bubble witch", "bubblewitch", "spotify", "netflix", "tiktok", "disney",
    "prime video", "primevideo", "facebook", "instagram", "linkedin",
    "word cookies", "wordcookies", "words of wonder", "match factory",
    "marvel", "emol", "super.", "bubblew",
]

# Ce qu'on ne touche JAMAIS, même si un mot-clé correspondrait par accident.
# (Microsoft.Getstarted n'y figure pas : c'est une cible assumée, voir KNOWN.)
PROTECTED = (
    "microsoft.windows.", "microsoft.windowsstore", "microsoft.ui.", "microsoft.vclibs",
    "microsoft.net.native", "microsoft.net.universal", "microsoft.aad.", "microsoft.appcompat",
    "microsoft.desktopappinstall", "microsoft.services", "microsoft.livecall",
    "microsoft.liveid", "microsoft.microsoftpass", "microsoft.wifi", "microsoft.bluetooth",
    "shell.", "windows.", "microsoft.adaptiveboundingbox",
    # Xbox / jeu : retirer ça casse la barre de jeu, le DVR et les succès.
    "microsoft.xbox", "microsoft.gaming", "microsoft.xboxgamingoverlay",
    # Sécurité : Windows Security / Defender, et tout ce qui s'en rapproche.
    "microsoft.sechealthui", "microsoft.securityhealth", "microsoft.security.",
    "microsoft.windowsdefender", "microsoft.defender",
    # Runtime d'applications : beaucoup de paquets Modernes en dépendent.
    "microsoft.windowsappruntime", "microsoftcorporationii.winappruntime",
    "microsoft.winget", "microsoft.storepurchaseapp", "microsoft.microsoftedge",
    # Extensions de codecs : sans elles, images et vidéos ne s'ouvrent plus.
    "microsoft.heif", "microsoft.webp", "microsoft.hevc", "microsoft.mpeg2",
    "microsoft.av1", "microsoft.avc", "microsoft.rawimage", "microsoft.media.",
    "microsoft.languageexperiencepack",
)


def list_installed():
    """Noms des paquets AppX installés pour l'utilisateur courant.

    On utilise $_.Name (et non PackageFamilyName) : c'est ce que `Get-AppxPackage
    -Name ...` attend pour désinstaller ensuite.
    """
    if not IS_WINDOWS:
        return []
    code, out = run_ps("Get-AppxPackage | ForEach-Object { $_.Name }")
    if code != 0 or not out.strip():
        return []
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def _protected(name):
    low = name.lower()
    return any(low.startswith(p) for p in PROTECTED)


def unsafe_names():
    """En une seule passe : paquets marqués NonRemovable ou IsFramework par Windows.

    Ils ne doivent jamais être proposés, même s'ils correspondent à un mot-clé.
    En cas d'échec de lecture on renvoie un ensemble vide : la vérification
    unitaire dans uninstall() reste le filet.
    """
    if not IS_WINDOWS:
        return set()
    try:
        code, out = run_ps("Get-AppxPackage | Where-Object { $_.NonRemovable -or $_.IsFramework } "
                          "| ForEach-Object { $_.Name }")
    except Exception:
        return set()
    if code != 0:
        return set()
    return {ln.strip() for ln in out.splitlines() if ln.strip()}


def safety_flags(pkg):
    """(NonRemovable, IsFramework) d'un paquet installé.

    Échec de lecture → (True, False) : par prudence on refuse plutôt que d'agir
    à l'aveugle. Ça vaut aussi pour une exception remontée par PowerShell.
    """
    if not IS_WINDOWS or not valid_name(pkg):
        return True, False
    script = ("$p = Get-AppxPackage -Name '" + pkg + "' | Select-Object -First 1; "
              'if ($null -eq $p) { "NOTFOUND" } else { '
              'if ($p.NonRemovable) { "NR=1" } else { "NR=0" }; '
              'if ($p.IsFramework) { "FW=1" } else { "FW=0" } }')
    try:
        code, out = run_ps(script)
    except Exception:
        return True, False
    if code != 0 or "NOTFOUND" in (out or ""):
        return True, False
    return "NR=1" in out, "FW=1" in out


def _match(packages, installed):
    """Retourne les paquets installés qui correspondent (préfixe) à la liste donnée."""
    found = []
    for pat in packages:
        for pkg in installed:
            if pkg.lower().startswith(pat.lower()) and not _protected(pkg):
                found.append(pkg)
    return sorted(set(found))


def _match_third(installed):
    """Applis tierces sponsorisées : appariement par mot-clé, jamais par nom codé en dur."""
    found = []
    for pkg in installed:
        low = pkg.lower()
        if _protected(pkg):
            continue
        for kw in THIRD_PARTY:
            if kw in low:
                found.append(pkg)
                break
    return sorted(set(found))


def scan():
    """Groupe les appli reconnues et réellement installées.

    Retourne une liste de dicts : label, packages (noms installés), kind ('ms'|'tierce').
    Les appli non installées sont simplement absentes de la liste.
    """
    installed = list_installed()
    if not installed:
        return []
    blocked = unsafe_names()
    installed = [p for p in installed if p not in blocked]
    out = []
    for label, packages in KNOWN:
        hits = _match(packages, installed)
        if hits:
            out.append({"label": label, "packages": hits, "kind": "ms"})
    tierces = _match_third(installed)
    if tierces:
        out.append({"label": T("Applis tierces sponsorisées"), "packages": tierces, "kind": "tierce"})
    return out


def uninstall(pkg):
    """Désinstalle un paquet pour l'utilisateur courant. Renvoie (ok, message).

    Trois verrous, dans cet ordre : nom validé (pas d'injection possible dans la
    commande), liste protégée, puis attributs du manifeste (NonRemovable /
    IsFramework).
    """
    if not IS_WINDOWS:
        return False, "Non Windows"
    if not valid_name(pkg):
        return False, T("Nom de paquet invalide (caractères non autorisés)")
    if _protected(pkg):
        return False, T("Programme protégé")
    non_removable, is_framework = safety_flags(pkg)
    if non_removable:
        return False, T("Programme non amovible (NonRemovable)")
    if is_framework:
        return False, T("Composant framework (IsFramework)")
    code, out = run_ps("Get-AppxPackage -Name '" + pkg + "' | Remove-AppxPackage -ErrorAction Stop")
    if code == 0:
        return True, ""
    return False, (out or T("Échec")).strip()[:200]
