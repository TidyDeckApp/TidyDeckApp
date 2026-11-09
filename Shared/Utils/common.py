"""Fonctions utilitaires communes (aucun accès réseau ici)."""
import os
import sys
import subprocess
import ctypes
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"
APP_NAME = "TidyDeck"
APP_VERSION = "0.6.1"
NO_WINDOW = 0x08000000  # évite les fenêtres noires de console

# CANAL DE DON UNIQUE. Laisse vide = aucun don demande nulle part.
# Ce lien est le SEUL autorise, et il n'est affiche que sur la page « A propos ».
# Ne jamais ajouter de rappel au demarrage, sur l'Accueil, dans la sidebar, ni de
# palier « premium » : le public vise est TDAH, insister casserait la promesse.
# Un seul prestataire (Ko-fi), pas deux : multiPLIER les vitrines de don transformerait
# un logiciel utile en sollicitation permanente. Voir DISTRIBUTION.md section 3.
DONATION_URL = "https://ko-fi.com/tidydeck"

# Page officielle des téléchargements : le bouton « Vérifier les mises à jour »
# ouvre cette page dans le navigateur. Un clic = une page ; TidyDeck ne télécharge
# et n'installe rien tout seul (voir DISTRIBUTION.md : le réseau part du clic).
SITE_TELECHARGEMENT = "https://tidydeckapp.github.io/index.html#telecharger"

# Pages « Parametres » (URI ms-settings:) retirees par Windows selon la version.
# Valeur = numero de build a partir duquel la page n'existe plus. Indispensable car
# os.startfile() ne signale pas une URI de page inconnue : Windows ouvre la page
# « Parametres introuvables », ce qui n'est pas une erreur pour nous.
# (Table vidée en 0.6 : la seule page listée, « privacy-backgroundapps », n'était
# plus utilisée nulle part depuis le retrait du contrôle « Applications en
# arrière-plan » — disparu de Windows 11. Le mécanisme de repli reste, pour les
# prochaines disparitions.)
MS_SETTINGS_REMOVED = {}
# Equivalent actuel a ouvrir quand la page d'origine a ete retiree.
MS_SETTINGS_ALIASES = {}


def data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def chemin_asset(nom: str) -> str:
    """Chemin d'un fichier embarque dans assets/.

    Embarque PyInstaller : les donnees sont decompressees dans sys._MEIPASS/assets.
    A la source (python main.py) : a cote du paquet Shared/. Un chemin peut donc ne
    jamais exister sans qu'on le sache avant l'appel : les appelants verifient."""
    racine = getattr(sys, "_MEIPASS", None)
    if racine:
        return os.path.join(racine, "assets", nom)
    racine = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(racine, "assets", nom)


def appliquer_icone(fenetre) -> bool:
    """Colle le logo TidyDeck sur la fenetre, et sur toutes celles qui suivront.

    Le "-default" de wm iconbitmap (Windows) herite aux Toplevel : boites de
    dialogue, welcome, toast... sans l'icone par defaut de Tk. Un fichier absent
    ou une icone refusee ne doit jamais empecher la fenetre de s'afficher : on
    renvoie False et la fenetre tourne avec l'icone generique."""
    ico = chemin_asset("tidydeck.ico")
    if not os.path.isfile(ico):
        return False
    try:
        fenetre.iconbitmap(default=ico)
        return True
    except Exception:
        try:
            fenetre.iconbitmap(ico)     # Tk sans "-default" (autres plates-formes)
            return True
        except Exception:
            return False


def human_size(n) -> str:
    from Shared.Utils.lang import get_lang
    en = get_lang() == "en"
    units = ("B", "KB", "MB", "GB", "TB") if en else ("o", "Ko", "Mo", "Go", "To")
    n = float(n)
    for u in units:
        if n < 1024 or u == units[-1]:
            if u in ("o", "B"):
                return f"{int(n)} {u}"
            s = f"{n:.1f} {u}"
            return s if en else s.replace(".", ",")
        n /= 1024


_BAREME_ESPACE = ((50 * 1024 * 1024, "un peu de place"),
                  (1024 * 1024 * 1024, "de la place"),
                  (10 * 1024 * 1024 * 1024, "une bonne place"))


def mots_espace(n):
    """Équivalent Sérénité de human_size : des mots, jamais un chiffre.
    Barème fixe, identique partout dans l'app."""
    from Shared.Utils.lang import T
    for seuil, mot in _BAREME_ESPACE:
        if n < seuil:
            return T(mot)
    return T("beaucoup de place")


def formater_espace(n, serene=False):
    """Taille lisible : chiffres en mode standard, mots en mode Sérénité."""
    return mots_espace(n) if serene else human_size(n)


def entry_size(path):
    """(octets, nb de fichiers) d'un fichier ou dossier. Erreurs ignorées."""
    total = count = 0
    stack = [str(path)]
    while stack:
        p = stack.pop()
        try:
            if os.path.islink(p):
                continue
            if os.path.isfile(p):
                total += os.path.getsize(p)
                count += 1
            elif os.path.isdir(p):
                with os.scandir(p) as it:
                    for e in it:
                        stack.append(e.path)
        except OSError:
            pass
    return total, count


def is_admin() -> bool:
    if not IS_WINDOWS:
        return hasattr(os, "geteuid") and os.geteuid() == 0
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run_cmd(args, timeout=20):
    """Lance une commande et renvoie (code, texte). Décodage tolérant : les outils Windows
    écrivent en cp850 (accents français) et faisaient planter un décodage strict."""
    try:
        kw = {"creationflags": NO_WINDOW} if IS_WINDOWS else {}
        r = subprocess.run(args, capture_output=True, timeout=timeout, **kw)
        return r.returncode, r.stdout.decode("utf-8", errors="replace")
    except Exception:
        return -1, ""


def run_ps(script, timeout=45):
    """PowerShell, sortie forcee en UTF-8.

    Pas de `-ExecutionPolicy Bypass` : ce qui est execute arrive par -Command, que
    la politique d'execution ne bloque pas (elle ne vise que les fichiers .ps1).
    Le drapeau ne servait donc a rien ici, et il compilait des types C# (csc.exe),
    un comportement signale par les analyses de comportement."""
    full = "[Console]::OutputEncoding=[Text.Encoding]::UTF8;" + script
    return run_cmd(["powershell", "-NoProfile", "-NonInteractive", "-Command", full], timeout)


def is_process_running(exe: str) -> bool:
    if not IS_WINDOWS:
        return False
    _, out = run_cmd(["tasklist", "/FI", f"IMAGENAME eq {exe}", "/NH"], 15)
    return exe.lower() in out.lower()


def identifier_processus_tache():
    """Donne au processus sa vraie identité Windows (AppUserModelID).

    Sans cela, la barre des tâches groupe la fenêtre sous l'identité du
    porteur (python.exe quand on lance depuis les sources) et affiche la
    icône du porteur au lieu de celle de TidyDeck, même quand la fenêtre
    porte la bonne icône. À appeler AVANT tk.Tk(), comme l'awareness DPI."""
    if not IS_WINDOWS:
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TidyDeck.TidyDeck")
    except Exception:
        from Shared.Utils import depannage
        depannage.noter("Shared/Utils/common.py:184")


def _alias_windowsapps(p: str) -> bool:
    """Vrai si p est une alias Microsoft Store (PythonManager). Lance en élève,
    cet alias échoue en silence : l'ACL WindowsApps le refuse au processus élevé."""
    p = os.path.normcase(os.path.abspath(p))
    if p.startswith(os.path.normcase(r"C:\Program Files\WindowsApps")):
        return True
    la = os.environ.get("LOCALAPPDATA", "")
    return bool(la) and p.startswith(os.path.normcase(os.path.join(la, "Microsoft", "WindowsApps")))


def _interpreteur_eleve() -> str:
    """Cherche le VRAI interpreteur pour la relance elevee : le pythoncore reel
    (sys._base_executable) plutot que l'alias Store ; pythonw si dispo (pas de
    console). Renvoie "" si rien de propre — l'appelant retombera sur sys.executable."""
    if getattr(sys, "frozen", False):
        return os.path.abspath(sys.executable)
    cands = [getattr(sys, "_base_executable", "") or "", sys.executable]
    for filtre_alias in (True, False):          # 2e passe : on accepte l'alias par defaut
        for c in cands:
            if not c or not os.path.exists(c):
                continue
            if filtre_alias and _alias_windowsapps(c):
                continue
            pyw = os.path.join(os.path.dirname(c), "pythonw.exe")
            if c.lower().endswith("python.exe") and os.path.exists(pyw):
                return pyw
            return os.path.abspath(c)
    return ""


def relaunch_as_admin() -> bool:
    """Relance TidyDeck avec l'invite Windows (UAC). Renvoie True si la demande est partie.

    Trois pieges verifieés sur machine reelle, tous corriges ici :
    * chemins absolus + dossier de travail explicite : sans eux, l'enfant eleve
      mourait sur un « main.py » introuvable (la fenetre actuelle, elle, etait
      deja fermee) ;
    * l'alias Microsoft Store (WindowsApps) ne se lance JAMAIS en eleve : il
      echoue en silence -> on resout le vrai interpreteur (pythoncore, pythonw) ;
    * marqueur --relance-admin : l'enfant peut demarrer pendant que le parent
      n'a pas encore rendu son mutex « instance unique » ; sans patience, il se
      croyait « deja ouvert » et quittait sans bruit.
    """
    if not IS_WINDOWS:
        return False
    try:
        if getattr(sys, "frozen", False):
            exe = os.path.abspath(sys.executable)
            args = [a if a.startswith("-") else os.path.abspath(a) for a in sys.argv[1:]]
            cwd = os.path.dirname(exe)
        else:
            exe = _interpreteur_eleve() or os.path.abspath(sys.executable)
            script = os.path.abspath(sys.argv[0] or "main.py")
            cwd = os.path.dirname(script)
            args = [script] + [a if a.startswith("-") else os.path.abspath(a)
                               for a in sys.argv[1:]]
        if "--relance-admin" not in args:
            args.append("--relance-admin")
        params = " ".join(f'"{a}"' for a in args)
        return ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, cwd, 1) > 32
    except Exception:
        return False


def open_in_explorer(path: str):
    """Ouvre un dossier, un fichier, ou un chemin namespace Windows («::{...}» = Corbeille).
    Renvoie True si l'ouverture a ete declenchee."""
    if not path:
        return False
    try:
        if IS_WINDOWS:
            os.startfile(path)  # noqa
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        try:
            if IS_WINDOWS:
                subprocess.Popen(["explorer", path])
                return True
        except Exception:
            from Shared.Utils import depannage
            depannage.noter("Shared/Utils/common.py:268")
        return False


def select_in_explorer(path: str) -> bool:
    """Ouvre l'Explorateur **avec l'element selectionne**, et non pas ouvert.

    `open_in_explorer(fichier)` lance le fichier dans son application associee :
    ce n'est pas ce qu'on veut pour « Ouvrir l'emplacement ». Sous Windows on passe
    par `explorer /select,<chemin>` ; un dossier s'ouvre normalement."""
    if not path:
        return False
    p = os.path.abspath(str(path))
    if not IS_WINDOWS:
        return open_in_explorer(p)
    if os.path.isdir(p):
        return open_in_explorer(p)
    try:
        subprocess.Popen(["explorer.exe", "/select,", p])
        return True
    except Exception:
        return open_in_explorer(os.path.dirname(p))


def ms_page_available(page: str) -> bool:
    """False si la page Parametres est connue pour ne plus exister sur CETTE version
    de Windows. Indispensable : os.startfile() reussit meme sur une URI ms-settings
    inconnue (Windows ouvre « Parametres introuvables »), donc sans cette table
    aucun repli ne serait jamais declenche."""
    base = page.split(":", 1)[1] if ":" in page else page
    removed = MS_SETTINGS_REMOVED.get(base)
    if removed is None:
        return True
    try:
        return sys.getwindowsversion().build < removed
    except Exception:
        return True


def open_windows_settings(page: str = "startupapps"):
    """Ouvre la page correspondante des Paramètres Windows. Lecture seule : aucune
    valeur modifiee par TidyDeck.

    Accepte :
      "startupapps"                       -> ms-settings:startupapps
      "ms-settings:gaming"                -> utilise tel quel
      "control:Microsoft.PowerOptions"    -> Panneau de configuration (control.exe)
    Une page retiree par une version recente de Windows est remplacee par son
    equivalent actuel (MS_SETTINGS_ALIASES) ; a defaut on renvoie False pour que
    l'appelante passe au candidat suivant.
    Renvoie True si l'ouverture a ete declenchee, False sinon (le bouton peut prvenir).
    """
    if not IS_WINDOWS or not page:
        return False
    if not ms_page_available(page):
        alias = MS_SETTINGS_ALIASES.get(page.split(":", 1)[1] if ":" in page else page)
        if not alias:
            return False
        page = alias
    if page.startswith("control:"):
        try:
            subprocess.Popen(["control.exe", "/name", page.split(":", 1)[1]])
            return True
        except Exception:
            return False
    target = page if page.startswith("ms-settings:") else f"ms-settings:{page}"
    try:
        os.startfile(target)  # noqa
        return True
    except Exception:
        try:
            subprocess.Popen(["explorer", target])
            return True
        except Exception:
            return False


HIVE_LONG = {"HKCU": "HKEY_CURRENT_USER", "HKLM": "HKEY_LOCAL_MACHINE",
             "HKCR": "HKEY_CLASSES_ROOT", "HKU": "HKEY_USERS",
             "HKCC": "HKEY_CURRENT_CONFIG"}


def reg_path(hive: str, key: str) -> str:
    """Chemin complet de registre, tel que regedit l'affiche."""
    return HIVE_LONG.get(hive.upper(), hive) + "\\" + str(key).strip("\\")


def copy_text(text: str) -> bool:
    """Copie du texte dans le presse-papiers via clip.exe (aucune dependance).
    En UTF-16LE : c'est ce que clip.exe attend pour conserver les accents."""
    try:
        kw = {"creationflags": NO_WINDOW} if IS_WINDOWS else {}
        return subprocess.run(["clip"], input=str(text).encode("utf-16-le"),
                             timeout=10, **kw).returncode == 0
    except Exception:
        return False


def open_reg_key(hive: str, key: str):
    """Ouvre regedit pour consulter une cle. N'ECRIT RIEN dans le registre :
    simple acces en consultation (regedit est lance, aucune valeur modifiee).

    regedit ne sait pas recevoir une cle en parametre : on copie donc le chemin
    complet dans le presse-papiers pour que tu n'aies plus qu'a le coller, et le
    bouton affiche ce qui a ete copie."""
    if not IS_WINDOWS:
        return False
    root = os.environ.get("SystemRoot", r"C:\Windows")
    for candidate in (os.path.join(root, "regedit.exe"), os.path.join(root, "System32", "regedit.exe")):
        if os.path.exists(candidate):
            try:
                # os.startfile (ShellExecute) : regedit exige une elevation,
                # Windows affiche la confirmation UAC comme pour tout regedit.
                os.startfile(candidate)  # noqa
                return True
            except OSError:
                continue
    return False
