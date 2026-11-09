"""Programmes lancés au démarrage — activer/désactiver SANS supprimer.
Même source que le Gestionnaire des tâches : clés Run (utilisateur, machine, 32 bits),
dossiers Démarrage et tâches UWP ; état activé/désactivé lu dans StartupApproved (registre)."""
import os
import re
import struct
import time
from Shared.Utils import registry
from Shared.Utils import refus
from Shared.Utils import dossiers
from Shared.Utils.common import IS_WINDOWS
from Services.Logger.journal import register_undo
from Shared.Utils.lang import T

APPR = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved"
SOURCES = [
    ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Run", APPR + r"\Run", "Pour toi uniquement"),
    ("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run",
     "Pour tous les utilisateurs (modifier demande les droits admin)"),
    ("HKLM", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run",
     r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run32",
     "Programmes 32 bits, tous les utilisateurs (admin requis)"),
]


def dossiers_demarrage():
    """Les deux dossiers « Demarrage », resolues par Windows et non par un chemin recolle.

    Le nom affiche (« Menu Démarrer\\Programmes\\Démarrage » sur un PC francais) est
    cosmétique, le nom reel reste anglais : le chemin en dur passait. Ce qui cassait
    en silence, c'est la redirection — regle d'entreprise, profil itinerant,
    profil deplace : le chemin recolle ne mene alors a rien, la page Demarrage
    affiche zero entree et l'utilisateur croit que rien ne se lance au demarrage.
    Le repli en dur reste la pour les machines ou l'appel repond mal."""
    perso = dossiers.connu("startup") or os.path.expandvars(
        r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
    tous = dossiers.connu("common_startup") or os.path.expandvars(
        r"%ProgramData%\Microsoft\Windows\Start Menu\Programs\StartUp")
    return [
        ("HKCU", perso, APPR + r"\StartupFolder", T("Dossier Démarrage (toi)")),
        ("HKLM", tous,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder",
         T("Dossier Démarrage (tous, admin requis)")),
    ]


HINTS = [
    ("securityhealth", "Sécurité Windows (antivirus). À GARDER activé.", "keep"),
    ("windowsdefender", "Antivirus Microsoft Defender. À GARDER activé.", "keep"),
    ("realtek", "Pilote audio Realtek. À garder (sinon plus de panneau son).", "keep"),
    ("rtkauduservice", "Service audio Realtek. À garder (sinon plus de panneau son).", "keep"),
    ("rtk", "Service audio Realtek. À garder (sinon plus de panneau son).", "keep"),
    ("nvidia", "Outils de ta carte graphique NVIDIA. Désactivable si tu n'en as pas l'usage.", "maybe"),
    ("razer", "Périphériques Razer (souris, clavier). Désactivable si tu n'utilises pas Razer Synapse.", "safe"),
    ("logitech", "Périphériques Logitech (G Hub, Options). Désactivable si tu gères tes périphériques autrement.", "safe"),
    ("steelseries", "Périphériques SteelSeries. Désactivable si tu n'utilises pas leur logiciel.", "safe"),
    ("discord", "Messagerie/vocal Discord. Utile au démarrage seulement si tu l'ouvres toujours tout de suite.", "safe"),
    ("spotify", "Lecteur de musique Spotify. Tu peux l'ouvrir à la main quand tu veux.", "safe"),
    ("steam", "Lanceur de jeux Steam. Tu peux le lancer toi-même avant de jouer.", "safe"),
    ("epic", "Lanceur de jeux Epic Games. Tu peux le lancer toi-même.", "safe"),
    ("ea app", "Lanceur EA (jeux EA). Désactivable, tu peux le lancer manuellement.", "safe"),
    ("battle.net", "Lanceur Blizzard (WoW, Overwatch, etc.). Désactivable, lance-le quand tu joues.", "safe"),
    ("onedrive", "Synchronise tes dossiers avec le cloud Microsoft. À garder si tu t'en sers pour sauvegarder.", "maybe"),
    ("teams", "Microsoft Teams. Désactivable si tu ne l'utilises pas chaque jour.", "safe"),
    ("skype", "Skype. Désactivable si tu ne l'utilises plus.", "safe"),
    ("adobe", "Outils de mise à jour Adobe. Désactivable : les applis Adobe se mettent à jour à l'ouverture.", "safe"),
    ("googleupdate", "Mises à jour Google. Désactivable, Chrome se met à jour seul.", "safe"),
    ("acrobat", "Adobe Acrobat Reader. Désactivable, ouvre-le quand tu as besoin d'un PDF.", "safe"),
    ("java", "Java Update Scheduler. Désactivable si tu n'utilises pas Java régulièrement.", "safe"),
    ("sunjava", "Java Update Scheduler. Désactivable si tu n'utilises pas Java régulièrement.", "safe"),
    ("vmware", "VMware Tools / Workstation. Désactivable si tu n'utilises pas de machines virtuelles.", "safe"),
    ("virtualbox", "VirtualBox. Désactivable si tu n'utilises pas de VM.", "safe"),
    ("docker", "Docker Desktop. Désactivable si tu ne développes pas avec Docker en ce moment.", "safe"),
    ("wsl", "Windows Subsystem for Linux. Désactivable si tu n'utilises pas WSL quotidiennement.", "safe"),
    ("vpn", "Client VPN. Désactivable, mais le VPN ne se lancera plus tout seul : "
            "à toi de l'ouvrir avant de te connecter.", "maybe"),
    ("nordvpn", "NordVPN. Désactivable, mais le VPN ne se lancera plus tout seul.", "maybe"),
    ("expressvpn", "ExpressVPN. Désactivable, mais le VPN ne se lancera plus tout seul.", "maybe"),
    ("cisco", "Cisco AnyConnect VPN. Désactivable, mais le VPN ne se lancera plus tout seul.", "maybe"),
    ("anyconnect", "Cisco AnyConnect VPN. Désactivable, mais le VPN ne se lancera plus tout seul.", "maybe"),
    ("mullvad", "Mullvad VPN. Désactivable, mais le VPN ne se lancera plus tout seul.", "maybe"),
    ("windscribe", "Windscribe VPN. Désactivable, mais le VPN ne se lancera plus tout seul.", "maybe"),
    ("icloud", "Apple iCloud pour Windows. Désactivable si tu ne synchronises pas avec un appareil Apple.", "safe"),
    ("itunes", "Apple iTunes. Désactivable si tu ne synchronises pas d'iPod/iPhone.", "safe"),
    ("apple", "Services Apple (bonjour, etc.). Désactivable si tu n'as pas d'appareil Apple.", "safe"),
    ("amazon", "Amazon Music / Alexa. Désactivable si tu ne l'utilises pas quotidiennement.", "safe"),
    ("netflix", "Application Netflix. Désactivable, ouvre-la quand tu veux regarder.", "safe"),
    ("obs", "OBS Studio (streaming/enregistrement). Désactivable si tu ne streams pas.", "safe"),
    ("streamlabs", "Streamlabs (streaming). Désactivable si tu ne streams pas.", "safe"),
    ("zoom", "Zoom (visioconférence). Désactivable si tu n'as pas de réunion régulière.", "safe"),
    ("webex", "Cisco Webex (visioconférence). Désactivable si tu ne l'utilises pas chaque jour.", "safe"),
    ("slack", "Slack (messagerie pro). Désactivable si tu peux l'ouvrir à la demande.", "safe"),
    ("telegram", "Telegram (messagerie). Désactivable si tu peux l'ouvrir à la demande.", "safe"),
    ("whatsapp", "WhatsApp Desktop. Désactivable si tu peux l'ouvrir à la demande.", "safe"),
    ("signal", "Signal (messagerie sécurisée). Désactivable si tu peux l'ouvrir à la demande.", "safe"),
    ("bitdefender", "Antivirus Bitdefender. À GARDER si c'est ton antivirus principal.", "keep"),
    ("avast", "Antivirus Avast. À GARDER si c'est ton antivirus principal.", "keep"),
    ("avg", "Antivirus AVG. À GARDER si c'est ton antivirus principal.", "keep"),
    ("mcafee", "Antivirus McAfee. À GARDER si c'est ton antivirus principal.", "keep"),
    ("kaspersky", "Antivirus Kaspersky. À GARDER si c'est ton antivirus principal.", "keep"),
    ("norton", "Antivirus Norton. À GARDER si c'est ton antivirus principal.", "keep"),
    ("malwarebytes", "Anti-malware Malwarebytes. Désactivable si tu lances des scans manuels.", "safe"),
    ("ccleaner", "CCleaner. Désactivable, lance-le quand tu veux nettoyer.", "safe"),
    ("winrar", "WinRAR. Désactivable, ouvre-le quand tu as besoin de dézipper.", "safe"),
    ("7zip", "7-Zip. Désactivable, ouvre-le quand tu as besoin d'archiver.", "safe"),
    ("vlc", "Lecteur VLC. Désactivable, ouvre-le quand tu veux regarder une vidéo.", "safe"),
    ("gimp", "GIMP (retouche photo). Désactivable, ouvre-le quand tu en as besoin.", "safe"),
    ("blender", "Blender (3D). Désactivable, ouvre-le quand tu en as besoin.", "safe"),
    ("photoshop", "Adobe Photoshop. Désactivable, ouvre-le quand tu en as besoin.", "safe"),
    ("lightroom", "Adobe Lightroom. Désactivable, ouvre-le quand tu en as besoin.", "safe"),
    ("autocad", "AutoCAD. Désactivable, ouvre-le quand tu en as besoin.", "safe"),
    ("solidworks", "SolidWorks. Désactivable, ouvre-le quand tu en as besoin.", "safe"),
    ("matlab", "MATLAB. Désactivable, ouvre-le quand tu en as besoin.", "safe"),
    ("python", "Python / Anaconda. Désactivable si tu ne développes pas en continu.", "safe"),
    ("nodejs", "Node.js. Désactivable si tu ne développes pas en continu.", "safe"),
    ("git", "Git / GitHub Desktop. Désactivable si tu ne codes pas en continu.", "safe"),
    ("vscode", "Visual Studio Code. Désactivable si tu ne codes pas en continu.", "safe"),
    ("visualstudio", "Visual Studio. Désactivable si tu ne codes pas en continu.", "safe"),
    ("jetbrains", "JetBrains (IntelliJ, PyCharm, etc.). Désactivable si tu ne codes pas en continu.", "safe"),
    ("phpstorm", "JetBrains PhpStorm (éditeur PHP). Désactivable si tu ne codes pas en continu.", "safe"),
    ("motorola", "Motorola Device Manager (téléphones Motorola). Désactivable si tu ne branches pas de téléphone Motorola.", "safe"),
    ("android", "Android Studio / ADB. Désactivable si tu ne développes pas Android.", "safe"),
    ("unity", "Unity Editor. Désactivable si tu ne développes pas de jeux.", "safe"),
    ("unreal", "Unreal Engine. Désactivable si tu ne développes pas de jeux.", "safe"),
    ("xbox", "Xbox App / Game Bar. Désactivable si tu ne joues pas aux jeux Xbox.", "safe"),
    ("gamebar", "Xbox Game Bar. Désactivable si tu n'utilises pas les overlays Xbox.", "safe"),
    ("epicgameslauncher", "Epic Games Launcher. Désactivable, lance-le quand tu joues.", "safe"),
    ("riotvanguard", "Riot Vanguard (anti-triche de Valorant et League of Legends). À garder si tu joues à Valorant ou LoL.", "keep"),
    ("vgtray", "Riot Vanguard (anti-triche de Valorant et League of Legends). À garder si tu joues à Valorant ou LoL.", "keep"),
    ("vgc", "Riot Vanguard (anti-triche de Valorant et League of Legends). À garder si tu joues à Valorant ou LoL.", "keep"),
    ("riotclient", "Riot Client (lanceur de Valorant, LoL et des autres jeux Riot). Désactivable, lance-le quand tu joues.", "safe"),
    ("riot", "Riot Client (Valorant, LoL). Désactivable, lance-le quand tu joues.", "safe"),
    ("battlestate", "Battlestate Games (Escape from Tarkov). Désactivable, lance-le quand tu joues.", "safe"),
    ("rockstar", "Rockstar Games Launcher (GTA, RDR2). Désactivable, lance-le quand tu joues.", "safe"),
    ("uplay", "Ubisoft Connect (ex-Uplay). Désactivable, lance-le quand tu joues.", "safe"),
    ("ubi", "Ubisoft Connect. Désactivable, lance-le quand tu joues.", "safe"),
    ("gog", "GOG Galaxy. Désactivable, lance-le quand tu joues.", "safe"),
    ("mousex", "X-Mouse Button Control. Désactivable si tu n'utilises pas de souris personnalisée.", "safe"),
    ("autohotkey", "AutoHotkey. Désactivable si tu n'utilises pas de scripts AHK.", "safe"),
    ("powerautomate", "Microsoft Power Automate. Désactivable si tu n'automatises pas de tâches.", "safe"),
    ("copilot", "Microsoft Copilot. Désactivable si tu n'utilises pas l'assistant IA.", "safe"),
    ("edgeupdate", "Microsoft Edge Update. Désactivable, Edge se met à jour seul.", "safe"),
    ("windowsupdate", "Windows Update. À GARDER pour la sécurité du système.", "keep"),
    ("searchindexer", "Indexeur de recherche Windows. Désactivable si tu n'utilises pas la recherche Windows.", "safe"),
    ("sysmain", "SysMain (Superfetch). Désactivable sur SSD (inutile, peut user le disque).", "safe"),
    ("superfetch", "Superfetch. Désactivable sur SSD (inutile, peut user le disque).", "safe"),
    ("wsearch", "Windows Search. Désactivable si tu n'utilises pas la recherche Windows.", "safe"),
    ("taskhost", "Task Host Windows. À GARDER (composant système).", "keep"),
    ("ctfmon", "CTFMON (clavier, langue). À GARDER (indispensable pour taper).", "keep"),
    ("rdpclip", "Presse-papiers RDP. Désactivable si tu ne fais pas de bureau à distance.", "safe"),
    ("mstsc", "Bureau à distance Windows. Désactivable si tu ne te connectes pas à distance.", "safe"),
    ("teamviewer", "TeamViewer (contrôle à distance). Désactivable si tu n'en as pas besoin en continu.", "safe"),
    ("anydesk", "AnyDesk (contrôle à distance). Désactivable si tu n'en as pas besoin en continu.", "safe"),
    ("splashtop", "Splashtop (contrôle à distance). Désactivable si tu n'en as pas besoin en continu.", "safe"),
    ("logmein", "LogMeIn (contrôle à distance). Désactivable si tu n'en as pas besoin en continu.", "safe"),
    ("gotomeeting", "GoToMeeting. Désactivable si tu n'as pas de réunion régulière.", "safe"),
    ("citrix", "Citrix Workspace. Désactivable si tu n'utilises pas de bureau virtuel.", "safe"),
    ("vmwareview", "VMware Horizon. Désactivable si tu n'utilises pas de bureau virtuel.", "safe"),
    ("paragon", "Paragon Software (disques, VPN). Désactivable selon ton usage.", "safe"),
    ("acronis", "Acronis (sauvegarde). Désactivable si tu fais des sauvegardes manuelles.", "safe"),
    ("macrium", "Macrium Reflect (sauvegarde). Désactivable si tu fais des sauvegardes manuelles.", "safe"),
    ("easeus", "EaseUS (récupération/sauvegarde). Désactivable selon ton usage.", "safe"),
    ("wondershare", "Wondershare (outils variés). Désactivable selon ton usage.", "safe"),
    ("iobit", "IObit (outils système). Désactivable selon ton usage.", "safe"),
    ("glary", "Glary Utilities. Désactivable, lance-le quand tu veux nettoyer.", "safe"),
    ("ashampoo", "Ashampoo (outils système). Désactivable selon ton usage.", "safe"),
    ("nexus", "Nexus Mods / Vortex. Désactivable si tu ne modes pas de jeux.", "safe"),
    ("vortex", "Vortex (Nexus Mods). Désactivable si tu ne modes pas de jeux.", "safe"),
    ("curseforge", "CurseForge (mods WoW, etc.). Désactivable si tu ne modes pas.", "safe"),
    ("modio", "Mod.io. Désactivable si tu ne modes pas de jeux.", "safe"),
    ("lghub", "Logitech G Hub. Désactivable si tu n'utilises pas de périphérique Logitech G.", "safe"),
    ("ghub", "Logitech G Hub. Désactivable si tu n'utilises pas de périphérique Logitech G.", "safe"),
    ("razer_synapse", "Razer Synapse. Désactivable si tu n'utilises pas de périphérique Razer.", "safe"),
    ("synapse", "Razer Synapse. Désactivable si tu n'utilises pas de périphérique Razer.", "safe"),
    ("icue", "Corsair iCUE. Désactivable si tu n'utilises pas de périphérique Corsair.", "safe"),
    ("corsair", "Corsair Software. Désactivable si tu n'utilises pas de périphérique Corsair.", "safe"),
    ("msi", "MSI Center / Dragon Center. Désactivable si tu n'utilises pas les outils MSI.", "safe"),
    ("asus", "ASUS Armoury Crate / AI Suite. Désactivable si tu n'utilises pas les outils ASUS.", "safe"),
    ("gigabyte", "Gigabyte Control Center. Désactivable si tu n'utilises pas les outils Gigabyte.", "safe"),
    ("asrock", "ASRock Tool. Désactivable si tu n'utilises pas les outils ASRock.", "safe"),
    ("lenovo", "Lenovo Vantage / Services. Désactivable si tu n'utilises pas les outils Lenovo.", "safe"),
    ("hp", "HP Support Assistant. Désactivable si tu n'utilises pas les outils HP.", "safe"),
    ("dell", "Dell Support / SupportAssist. Désactivable si tu n'utilises pas les outils Dell.", "safe"),
    ("acer", "Acer Care Center. Désactivable si tu n'utilises pas les outils Acer.", "safe"),
    ("samsung", "Samsung Magician / Settings. Désactivable si tu n'utilises pas les outils Samsung.", "safe"),
    ("intel", "Intel Graphics / Rapid Storage. Désactivable si tu n'utilises pas les outils Intel.", "maybe"),
    ("amd", "AMD Software / Radeon Settings. Désactivable si tu n'utilises pas les outils AMD.", "maybe"),
    ("razerzone", "Razer Zone. Désactivable si tu n'utilises pas de périphérique Razer.", "safe"),
    ("steelseriesgg", "SteelSeries GG. Désactivable si tu n'utilises pas de périphérique SteelSeries.", "safe"),
    ("madcatz", "Mad Catz / Nacon. Désactivable si tu n'utilises pas de périphérique Mad Catz.", "safe"),
    ("saitek", "Saitek / Mad Catz. Désactivable si tu n'utilises pas de périphérique Saitek.", "safe"),
    ("thrustmaster", "Thrustmaster (volants, joysticks). Désactivable si tu ne simules pas.", "safe"),
    ("logigaming", "Logitech Gaming Software. Désactivable si tu n'utilises pas de périphérique Logitech Gaming.", "safe"),
    ("wacom", "Wacom (tablette graphique). Désactivable si tu n'utilises pas de tablette Wacom.", "safe"),
    ("huion", "Huion (tablette graphique). Désactivable si tu n'utilises pas de tablette Huion.", "safe"),
    ("gaomon", "Gaomon (tablette graphique). Désactivable si tu n'utilises pas de tablette Gaomon.", "safe"),
    ("xp_pen", "XP-Pen (tablette graphique). Désactivable si tu n'utilises pas de tablette XP-Pen.", "safe"),
    ("xppen", "XP-Pen (tablette graphique). Désactivable si tu n'utilises pas de tablette XP-Pen.", "safe"),
    ("elgato", "Elgato (capture vidéo/streaming). Désactivable si tu ne captures pas.", "safe"),
    ("avermedia", "AVerMedia (capture vidéo). Désactivable si tu ne captures pas.", "safe"),
    ("rode", "RØDE (micros). Désactivable si tu n'utilises pas de micro RØDE.", "safe"),
    ("blue", "Blue Microphones (Yeti, etc.). Désactivable si tu n'utilises pas de micro Blue.", "safe"),
    ("fifine", "Fifine (micros). Désactivable si tu n'utilises pas de micro Fifine.", "safe"),
    ("behringer", "Behringer (audio). Désactivable si tu n'utilises pas d'audio Behringer.", "safe"),
    ("focusrite", "Focusrite (audio). Désactivable si tu n'utilises pas d'audio Focusrite.", "safe"),
    ("audient", "Audient (audio). Désactivable si tu n'utilises pas d'audio Audient.", "safe"),
    ("presonus", "PreSonus (audio). Désactivable si tu n'utilises pas d'audio PreSonus.", "safe"),
    ("steinberg", "Steinberg (audio/DAW). Désactivable si tu n'utilises pas de DAW Steinberg.", "safe"),
    ("ableton", "Ableton Live (DAW). Désactivable si tu ne produis pas de musique.", "safe"),
    ("flstudio", "FL Studio (DAW). Désactivable si tu ne produis pas de musique.", "safe"),
    ("reaper", "REAPER (DAW). Désactivable si tu ne produis pas de musique.", "safe"),
    ("cubase", "Cubase (DAW). Désactivable si tu ne produis pas de musique.", "safe"),
    ("protools", "Pro Tools (DAW). Désactivable si tu ne produis pas de musique.", "safe"),
    ("logic", "Logic Pro (DAW). Désactivable si tu ne produis pas de musique.", "safe"),
    ("garageband", "GarageBand (DAW). Désactivable si tu ne produis pas de musique.", "safe"),
    ("audacity", "Audacity (audio). Désactivable si tu n'enregistres pas d'audio.", "safe"),
    ("obsstudio", "OBS Studio. Désactivable si tu ne streams pas.", "safe"),
    ("streamdeck", "Elgato Stream Deck. Désactivable si tu n'utilises pas de Stream Deck.", "safe"),
    ("touchportal", "Touch Portal. Désactivable si tu n'utilises pas de console tactile.", "safe"),
    ("bitfocus", "Bitfocus (Touch Portal). Désactivable si tu n'utilises pas de console tactile.", "safe"),
    ("midi", "Périphériques MIDI. Désactivable si tu ne produis pas de musique.", "safe"),
    ("loopback", "Audio Loopback. Désactivable si tu ne routes pas d'audio.", "safe"),
    ("voicemod", "Voicemod (modulateur de voix en direct). Désactivable si tu ne changes pas de voix en stream ou en appel.", "safe"),
    ("voicemeeter", "VoiceMeeter (mixage audio). Désactivable si tu ne mixe pas d'audio.", "safe"),
    ("cheatengine", "Cheat Engine. Désactivable (outil de triche, pas de démarrage nécessaire).", "safe"),
    ("xboxgaming", "Xbox Gaming Services. Désactivable si tu ne joues pas aux jeux Xbox.", "safe"),
    ("gameinput", "GameInput (périphériques de jeu). Désactivable si tu ne joues pas.", "safe"),
    ("xinput", "XInput (manettes Xbox). Désactivable si tu n'utilises pas de manette.", "safe"),
    ("ds4windows", "DS4Windows (manette PS4/PS5). Désactivable si tu n'utilises pas de manette PlayStation.", "safe"),
    ("rewasd", "reWASD (mapping manette/clavier). Désactivable si tu ne remaps pas tes périphériques.", "safe"),
    ("joytokey", "JoyToKey (mapping manette). Désactivable si tu ne remaps pas tes périphériques.", "safe"),
    ("x360ce", "x360ce (manette Xbox 360). Désactivable si tu n'utilises pas de manette Xbox 360.", "safe"),
    ("inputmapper", "Input Mapper. Désactivable si tu ne remaps pas tes périphériques.", "safe"),
    ("keyremap", "Key Remapper. Désactivable si tu ne remaps pas ton clavier.", "safe"),
    ("sharpkeys", "SharpKeys (remap clavier). Désactivable si tu ne remaps pas ton clavier.", "safe"),
    ("ahk", "AutoHotkey. Désactivable si tu n'utilises pas de scripts AHK.", "safe"),
    ("powertoys", "Microsoft PowerToys. Désactivable si tu n'utilises pas les outils avancés Windows.", "safe"),
    ("power toys", "Microsoft PowerToys. Désactivable si tu n'utilises pas les outils avancés Windows.", "safe"),
    ("flow", "Microsoft PowerToys Flow. Désactivable si tu n'utilises pas Flow.", "safe"),
    ("run", "Microsoft PowerToys Run. Désactivable si tu n'utilises pas Run.", "safe"),
    ("fancyzones", "Microsoft PowerToys FancyZones. Désactivable si tu n'utilises pas FancyZones.", "safe"),
    ("colorpicker", "Microsoft PowerToys ColorPicker. Désactivable si tu n'utilises pas le sélecteur de couleurs.", "safe"),
    ("textextractor", "Microsoft PowerToys TextExtractor. Désactivable si tu n'utilises pas l'extraction de texte.", "safe"),
    ("imageresizer", "Microsoft PowerToys ImageResizer. Désactivable si tu ne redimensionnes pas d'images.", "safe"),
    ("keyboardmanager", "Microsoft PowerToys Keyboard Manager. Désactivable si tu ne remaps pas le clavier.", "safe"),
    ("awake", "Microsoft PowerToys Awake. Désactivable si tu n'utilises pas Awake.", "safe"),
    ("findmymouse", "Microsoft PowerToys FindMyMouse. Désactivable si tu n'utilises pas FindMyMouse.", "safe"),
    ("mousewithoutborders", "Microsoft Mouse Without Borders. Désactivable si tu ne partages pas souris/clavier entre PC.", "safe"),
    ("keyboardwithoutborders", "Microsoft Keyboard Without Borders. Désactivable si tu ne partages pas souris/clavier entre PC.", "safe"),
    ("commandpalette", "Microsoft Command Palette. Désactivable si tu n'utilises pas la palette de commandes.", "safe"),
    ("workspaces", "Microsoft Workspaces. Désactivable si tu n'utilises pas Workspaces.", "safe"),
    ("peek", "Microsoft Peek. Désactivable si tu n'utilises pas Peek.", "safe"),
    ("advancedpaste", "Microsoft Advanced Paste. Désactivable si tu n'utilises pas Advanced Paste.", "safe"),
    ("newplus", "Microsoft New Plus. Désactivable si tu n'utilises pas New Plus.", "safe"),
    ("showdesktop", "Show Desktop. Désactivable si tu n'utilises pas cette fonction.", "safe"),
    ("quickassist", "Windows Quick Assist. Désactivable si tu n'utilises pas l'assistance à distance.", "safe"),
    ("remoteassist", "Windows Remote Assistance. Désactivable si tu n'utilises pas l'assistance à distance.", "safe"),
    ("faststartup", "Démarrage rapide Windows. Désactivable si tu préfères un démarrage complet.", "safe"),
    ("startuprepairs", "Réparation du démarrage. À GARDER (composant système).", "keep"),
    ("defender", "Windows Defender. À GARDER (antivirus).", "keep"),
    ("firewall", "Pare-feu Windows. À GARDER (sécurité).", "keep"),
    ("windowsfirewall", "Pare-feu Windows. À GARDER (sécurité).", "keep"),
    ("securitycenter", "Centre de sécurité Windows. À GARDER.", "keep"),
    ("wscsvc", "Centre de sécurité Windows. À GARDER.", "keep"),
    ("wuauserv", "Windows Update. À GARDER (mises à jour de sécurité).", "keep"),
    ("bits", "Background Intelligent Transfer. À GARDER (téléchargements Windows).", "keep"),
    ("cryptsvc", "Services cryptographiques. À GARDER (sécurité).", "keep"),
    ("rpcss", "Remote Procedure Call. À GARDER (composant système critique).", "keep"),
    ("dcomlaunch", "DCOM Launch. À GARDER (composant système critique).", "keep"),
    ("svchost", "Service Host Windows. À GARDER (composant système).", "keep"),
    ("lsass", "Local Security Authority. À GARDER (sécurité critique).", "keep"),
    ("csrss", "Client/Server Runtime. À GARDER (composant système critique).", "keep"),
    ("wininit", "Windows Init. À GARDER (composant système critique).", "keep"),
    ("smss", "Session Manager. À GARDER (composant système critique).", "keep"),
    ("services", "Contrôleur des services. À GARDER (composant système critique).", "keep"),
    ("winlogon", "Windows Logon. À GARDER (composant système critique).", "keep"),
    ("userinit", "User Init. À GARDER (composant système critique).", "keep"),
    ("explorer", "Explorateur Windows. À GARDER (interface graphique).", "keep"),
    ("taskmgr", "Gestionnaire des tâches. Désactivable au démarrage (ouvre-le avec Ctrl+Shift+Esc).", "safe"),
    ("controlpanel", "Panneau de configuration. Désactivable, ouvre-le à la demande.", "safe"),
    ("settings", "Paramètres Windows. Désactivable, ouvre-les à la demande.", "safe"),
    ("store", "Microsoft Store. Désactivable, ouvre-le à la demande.", "safe"),
    ("edge", "Microsoft Edge. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("chrome", "Google Chrome. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("firefox", "Mozilla Firefox. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("brave", "Brave Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("opera", "Opera Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("vivaldi", "Vivaldi Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("tor", "Tor Browser. Désactivable, ouvre-le quand tu as besoin d'anonymat.", "safe"),
    ("bravebrowser", "Brave Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("chromium", "Chromium. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("safari", "Safari (via iCloud). Désactivable si tu utilises un autre navigateur.", "safe"),
    ("maxthon", "Maxthon Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("k-meleon", "K-Meleon Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("palemoon", "Pale Moon Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("waterfox", "Waterfox Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("librewolf", "LibreWolf Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("falkon", "Falkon Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("midori", "Midori Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("konqueror", "Konqueror (KDE). Désactivable si tu utilises un autre navigateur.", "safe"),
    ("epiphany", "Epiphany (GNOME). Désactivable si tu utilises un autre navigateur.", "safe"),
    ("surf", "Surf (suckless). Désactivable si tu utilises un autre navigateur.", "safe"),
    ("luakit", "Luakit. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("qutebrowser", "qutebrowser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("nyxt", "Nyxt Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("zen", "Zen Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("floorp", "Floorp Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("cromite", "Cromite. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("bromite", "Bromite. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("ungoogled", "Ungoogled Chromium. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("iridium", "Iridium Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("slimjet", "Slimjet Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("centbrowser", "Cent Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("sleipnir", "Sleipnir Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("avirabrowser", "Avira Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("avastbrowser", "Avast Secure Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("avgbrowser", "AVG Secure Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("nortonbrowser", "Norton Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("kasperskybrowser", "Kaspersky Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("comodo", "Comodo Dragon Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("torch", "Torch Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("sputnik", "Sputnik Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("yandex", "Yandex Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("mailru", "Mail.ru Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("amilite", "AmiLite Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("citrio", "Citrio Browser. Désactivable si tu utilises un autre navigateur.", "safe"),
    ("element", "Element (Matrix chat). Désactivable si tu peux l'ouvrir à la demande.", "safe"),
    ("matrix", "Matrix / Element. Désactivable si tu peux l'ouvrir à la demande.", "safe"),
    ("rocketchat", "Rocket.Chat. Désactivable si tu peux l'ouvrir à la demande.", "safe"),
    ("mattermost", "Mattermost. Désactivable si tu peux l'ouvrir à la demande.", "safe"),
    ("zello", "Zello (radio push-to-talk). Désactivable si tu ne l'utilises pas en continu.", "safe"),
    ("mumble", "Mumble (voIP). Désactivable si tu ne l'utilises pas en continu.", "safe"),
    ("teamspeak", "TeamSpeak (voIP). Désactivable si tu ne l'utilises pas en continu.", "safe"),
    ("viber", "Viber. Désactivable si tu peux l'ouvrir à la demande.", "safe"),
    ("line", "LINE. Désactivable si tu peux l'ouvrir à la demande.", "safe"),
    ("kakao", "KakaoTalk. Désactivable si tu peux l'ouvrir à la demande.", "safe"),
    ("wechat", "WeChat. Désactivable si tu peux l'ouvrir à la demande.", "safe"),
    ("qq", "QQ. Désactivable si tu peux l'ouvrir à la demande.", "safe"),
    ("dingtalk", "DingTalk. Désactivable si tu peux l'ouvrir à la demande.", "safe"),
    ("feishu", "Feishu / Lark. Désactivable si tu peux l'ouvrir à la demande.", "safe"),
    ("lark", "Lark / Feishu. Désactivable si tu peux l'ouvrir à la demande.", "safe"),
    ("wemeet", "Tencent Meeting. Désactivable si tu n'as pas de réunion régulière.", "safe"),
    ("tencent", "Tencent Meeting / WeChat. Désactivable si tu peux l'ouvrir à la demande.", "safe"),
    ("jitsi", "Jitsi Meet. Désactivable si tu n'as pas de réunion régulière.", "safe"),
    ("jami", "Jami (visioconférence). Désactivable si tu n'as pas de réunion régulière.", "safe"),
    ("ring", "Ring (visioconférence). Désactivable si tu n'as pas de réunion régulière.", "safe"),
    ("linphone", "Linphone (VoIP). Désactivable si tu ne passes pas d'appels SIP en continu.", "safe"),
    ("zoiper", "Zoiper (VoIP). Désactivable si tu ne passes pas d'appels SIP en continu.", "safe"),
    ("microsip", "MicroSIP (VoIP). Désactivable si tu ne passes pas d'appels SIP en continu.", "safe"),
    ("bria", "Bria (VoIP). Désactivable si tu ne passes pas d'appels SIP en continu.", "safe"),
    ("counterpath", "CounterPath (Bria). Désactivable si tu ne passes pas d'appels SIP en continu.", "safe"),
    ("3cx", "3CX (VoIP). Désactivable si tu ne passes pas d'appels SIP en continu.", "safe"),
    ("grandstream", "Grandstream (VoIP). Désactivable si tu ne passes pas d'appels SIP en continu.", "safe"),
    ("yealink", "Yealink (VoIP). Désactivable si tu ne passes pas d'appels SIP en continu.", "safe"),
    ("snom", "snom (VoIP). Désactivable si tu ne passes pas d'appels SIP en continu.", "safe"),
    ("polycom", "Polycom (VoIP). Désactivable si tu ne passes pas d'appels SIP en continu.", "safe"),
    ("jabra", "Jabra (casques/micros). Désactivable si tu n'utilises pas de casque Jabra.", "safe"),
    ("plantronics", "Plantronics (casques/micros). Désactivable si tu n'utilises pas de casque Plantronics.", "safe"),
    ("poly", "Poly (casques/micros). Désactivable si tu n'utilises pas de casque Poly.", "safe"),
    ("sennheiser", "Sennheiser (casques/micros). Désactivable si tu n'utilises pas de casque Sennheiser.", "safe"),
    ("bose", "Bose (casques/enceintes). Désactivable si tu n'utilises pas d'appareil Bose.", "safe"),
    ("sony", "Sony (casques/enceintes). Désactivable si tu n'utilises pas d'appareil Sony.", "safe"),
    ("jbl", "JBL (enceintes/casques). Désactivable si tu n'utilises pas d'appareil JBL.", "safe"),
    ("harman", "Harman Kardon. Désactivable si tu n'utilises pas d'appareil Harman.", "safe"),
    ("marantz", "Marantz (audio). Désactivable si tu n'utilises pas d'appareil Marantz.", "safe"),
    ("denon", "Denon (audio/vidéo). Désactivable si tu n'utilises pas d'appareil Denon.", "safe"),
    ("onkyo", "Onkyo (audio/vidéo). Désactivable si tu n'utilises pas d'appareil Onkyo.", "safe"),
    ("pioneer", "Pioneer (audio/vidéo). Désactivable si tu n'utilises pas d'appareil Pioneer.", "safe"),
    ("yamaha", "Yamaha (audio). Désactivable si tu n'utilises pas d'appareil Yamaha.", "safe"),
    ("kef", "KEF (enceintes). Désactivable si tu n'utilises pas d'enceintes KEF.", "safe"),
    ("b&w", "Bowers & Wilkins. Désactivable si tu n'utilises pas d'enceintes B&W.", "safe"),
    ("focal", "Focal (enceintes/casques). Désactivable si tu n'utilises pas d'appareil Focal.", "safe"),
    ("audio-technica", "Audio-Technica (micros/casques). Désactivable si tu n'utilises pas d'appareil Audio-Technica.", "safe"),
    ("shure", "Shure (micros). Désactivable si tu n'utilises pas de micro Shure.", "safe"),
    ("neumann", "Neumann (micros). Désactivable si tu n'utilises pas de micro Neumann.", "safe"),
    ("akg", "AKG (casques/micros). Désactivable si tu n'utilises pas d'appareil AKG.", "safe"),
    ("beyerdynamic", "Beyerdynamic (casques/micros). Désactivable si tu n'utilises pas d'appareil Beyerdynamic.", "safe"),
    ("ultrasone", "Ultrasone (casques). Désactivable si tu n'utilises pas de casque Ultrasone.", "safe"),
    (" Grado", "Grado Labs (casques). Désactivable si tu n'utilises pas de casque Grado.", "safe"),
    ("stax", "STAX (casques électrostatiques). Désactivable si tu n'utilises pas de casque STAX.", "safe"),
    ("hi-fi", "Hi-Fi / Audio. Désactivable selon ton usage.", "safe"),
    ("hi-res", "Hi-Res Audio. Désactivable selon ton usage.", "safe"),
    ("bluetooth", "Bluetooth. Désactivable si tu n'utilises pas de périphérique Bluetooth.", "safe"),
    ("wifi", "Wi-Fi. À GARDER si tu te connectes sans fil.", "keep"),
    ("wlan", "Wi-Fi. À GARDER si tu te connectes sans fil.", "keep"),
    ("network", "Services réseau. À GARDER (connectivité).", "keep"),
    ("lanman", "Services de partage réseau. Désactivable si tu ne partages pas de fichiers.", "safe"),
    ("smb", "SMB (partage de fichiers). Désactivable si tu ne partages pas de fichiers.", "safe"),
    ("nfs", "NFS (partage réseau). Désactivable si tu n'utilises pas NFS.", "safe"),
    ("ftp", "FTP. Désactivable si tu ne transfères pas de fichiers par FTP.", "safe"),
    ("sftp", "SFTP. Désactivable si tu ne transfères pas de fichiers par SFTP.", "safe"),
    ("rsync", "Rsync. Désactivable si tu ne synchronises pas de fichiers.", "safe"),
    ("syncthing", "Syncthing (synchronisation). Désactivable si tu ne synchronises pas de fichiers.", "safe"),
    ("resilio", "Resilio Sync. Désactivable si tu ne synchronises pas de fichiers.", "safe"),
    ("btsync", "BitTorrent Sync. Désactivable si tu ne synchronises pas de fichiers.", "safe"),
    ("freefilesync", "FreeFileSync. Désactivable, lance-le quand tu synchronises.", "safe"),
    ("goodsync", "GoodSync. Désactivable si tu ne synchronises pas en continu.", "safe"),
    ("arq", "Arq Backup. Désactivable si tu ne sauvegardes pas en continu.", "safe"),
    ("duplicati", "Duplicati (sauvegarde). Désactivable si tu ne sauvegardes pas en continu.", "safe"),
    ("restic", "Restic (sauvegarde). Désactivable si tu ne sauvegardes pas en continu.", "safe"),
    ("borg", "BorgBackup. Désactivable si tu ne sauvegardes pas en continu.", "safe"),
    ("rdiff", "rdiff-backup. Désactivable si tu ne sauvegardes pas en continu.", "safe"),
    ("carboncopy", "Carbon Copy Cloner. Désactivable si tu ne clonnes pas de disques.", "safe"),
    ("superduper", "SuperDuper!. Désactivable si tu ne clonnes pas de disques.", "safe"),
    ("clonezilla", "Clonezilla. Désactivable si tu ne clonnes pas de disques.", "safe"),
    ("acronis_true_image", "Acronis True Image. Désactivable si tu ne sauvegardes pas en continu.", "safe"),
    ("veeam", "Veeam (sauvegarde). Désactivable si tu ne sauvegardes pas en continu.", "safe"),
    ("unitrends", "Unitrends (sauvegarde). Désactivable si tu ne sauvegardes pas en continu.", "safe"),
    ("zerto", "Zerto (sauvegarde). Désactivable si tu ne sauvegardes pas en continu.", "safe"),
    ("asigra", "Asigra (sauvegarde). Désactivable si tu ne sauvegardes pas en continu.", "safe"),
    ("commvault", "Commvault (sauvegarde). Désactivable si tu ne sauvegardes pas en continu.", "safe"),
    ("veritas", "Veritas (sauvegarde). Désactivable si tu ne sauvegardes pas en continu.", "safe"),
    ("netbackup", "NetBackup (sauvegarde). Désactivable si tu ne sauvegardes pas en continu.", "safe"),
    ("backupexec", "Backup Exec (sauvegarde). Désactivable si tu ne sauvegardes pas en continu.", "safe"),
    ("windows_server_backup", "Windows Server Backup. Désactivable si tu ne sauvegardes pas en continu.", "safe"),
    ("azure_backup", "Azure Backup. Désactivable si tu ne sauvegardes pas sur Azure.", "safe"),
    ("aws_backup", "AWS Backup. Désactivable si tu ne sauvegardes pas sur AWS.", "safe"),
    ("google_cloud_backup", "Google Cloud Backup. Désactivable si tu ne sauvegardes pas sur GCP.", "safe"),
    ("backblaze", "Backblaze (sauvegarde cloud). Désactivable si tu ne sauvegardes pas en continu.", "safe"),
    ("carbonite", "Carbonite (sauvegarde cloud). Désactivable si tu ne sauvegardes pas en continu.", "safe"),
    ("mozy", "Mozy (sauvegarde cloud). Désactivable si tu ne sauvegardes pas en continu.", "safe"),
    ("spideroak", "SpiderOak (sauvegarde cloud). Désactivable si tu ne sauvegardes pas en continu.", "safe"),
    ("dropbox", "Dropbox. Désactivable si tu ne synchronises pas en continu.", "safe"),
    ("googledrive", "Google Drive. Désactivable si tu ne synchronises pas en continu.", "safe"),
    ("box", "Box. Désactivable si tu ne synchronises pas en continu.", "safe"),
    ("megasync", "MEGA. Désactivable si tu ne synchronises pas en continu.", "safe"),
    ("mega", "MEGA. Désactivable si tu ne synchronises pas en continu.", "safe"),
    ("pcloud", "pCloud. Désactivable si tu ne synchronises pas en continu.", "safe"),
    ("sync.com", "sync.com. Désactivable si tu ne synchronises pas en continu.", "safe"),
    ("wuala", "Wuala. Désactivable si tu ne synchronises pas en continu.", "safe"),
    ("teamdrive", "TeamDrive. Désactivable si tu ne synchronises pas en continu.", "safe"),
    ("hightail", "Hightail. Désactivable si tu ne synchronises pas en continu.", "safe"),
    ("yousendit", "YouSendIt. Désactivable si tu ne synchronises pas en continu.", "safe"),
    ("wetransfer", "WeTransfer. Désactivable si tu ne transfères pas de fichiers en continu.", "safe"),
    ("transfernow", "TransferNow. Désactivable si tu ne transfères pas de fichiers en continu.", "safe"),
    ("send-anywhere", "Send Anywhere. Désactivable si tu ne transfères pas de fichiers en continu.", "safe"),
    ("send_space", "Send Space. Désactivable si tu ne transfères pas de fichiers en continu.", "safe"),
]
UNKNOWN = ("Programme non reconnu par TidyDeck : cherche son nom sur internet avant de décider. "
           "Désactiver reste de toute façon réversible.")


UWP_ROOT = r"Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppModel\SystemAppData"
UWP_NAMES = [
    ("microsoft.yourphone", "Mobile connecté (Lien avec Windows)",
     "Synchronise ton téléphone avec le PC (notifications, SMS, photos). Désactivable sans risque si tu ne t'en sers pas.", "safe"),
    ("microsoftwindows.crossdevice", "Mobile connecté (expérience multi-appareils)",
     "Même famille que « Lien avec Windows » : liaison PC ↔ téléphone. Désactivable si tu ne l'utilises pas.", "safe"),
    ("msteams", "Microsoft Teams", "Désactivable si tu ne l'utilises pas chaque jour.", "safe"),
    ("microsoft.549981c3f5f10", "Cortana", "Assistant vocal Microsoft, rarement utilisé.", "safe"),
    ("microsoft.skypeapp", "Skype", "Désactivable si tu ne l'utilises plus.", "safe"),
    ("spotifyab.spotifymusic", "Spotify (Microsoft Store)", "Tu peux l'ouvrir à la main quand tu veux.", "safe"),
    ("microsoft.windowsterminal", "Terminal Windows", "Désactivable sans risque.", "safe"),
    ("microsoftcorporationii.windowsapp", "Application Windows (Store)", "Selon ton usage.", "maybe"),
]


def _uwp_entries():
    out = []
    for pkg in registry.list_subkeys("HKCU", UWP_ROOT):
        for task in registry.list_subkeys("HKCU", UWP_ROOT + "\\" + pkg):
            key = f"{UWP_ROOT}\\{pkg}\\{task}"
            st = registry.read("HKCU", key, "State")
            if not isinstance(st, int) or not 0 <= st <= 4:
                continue
            low = pkg.lower()
            name, hint, level = next(((n, h, l) for pre, n, h, l in UWP_NAMES if low.startswith(pre)),
                                     (f"{pkg.split('_')[0]} ({task})", UNKNOWN, "unknown"))
            out.append({"kind": "uwp", "hive": "HKCU", "name": name, "command": T("Application du Microsoft Store : {v0}").format(v0=pkg),
                        "key": key, "approved": None, "scope": T("Application du Store (comme dans le Gestionnaire des tâches)"),
                        "where": registry.full_path("HKCU", key), "hint": hint, "level": level,
                        "enabled": st in (2, 4), "policy": st in (3, 4)})
    return out


def _mots(texte):
    """Mots d'un nom : coupé aux séparateurs, plus l'éclatement CamelCase
    (« SecurityHealthSystray » -> security, health, systray)."""
    out = []
    for bloc in re.split(r"[^0-9A-Za-z]+", str(texte or "")):
        if not bloc:
            continue
        camel = re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z]+|[a-z]+|\d+", bloc)
        out.extend(m.lower() for m in (camel if len(camel) > 1 else [bloc]))
    return out


def _exe_nom(command):
    """Nom du programme visé par la commande : sans chemin, sans extension,
    sans arguments (--runinbk ou un dossier du chemin ne déclenchent donc
    JAMAIS une règle)."""
    c = str(command or "").strip()
    if c.startswith('"'):
        morceaux = c.split('"')
        c = morceaux[1] if len(morceaux) >= 2 else ""
    else:
        c = c.split(" ")[0] if c else ""
    c = c.replace("\\", "/").rsplit("/", 1)[-1]
    if c.lower().endswith(".exe") or "." in c:
        c = os.path.splitext(c)[0]
    return c


_RULES = []
for _cle, _texte, _niveau in HINTS:
    _km = _mots(_cle)
    if _km:
        _RULES.append((_km, "".join(_km), _texte, _niveau))
# Priorité : la règle la plus spécifique gagne (le plus de mots, puis la clé
# la plus longue) : « riotvanguard » avant « riot », « streamdeck » garde la
# main sur « stre-a-m-d » qui n'est plus jamais une sous-chaîne recherchée.
_RULES.sort(key=lambda r: (len(r[0]), len(r[1])), reverse=True)


def _hint(name, command):
    """Conseil sur une entrée de démarrage : uniquement sur le NOM de l'entrée
    et le nom de l'exécutable, en mots entiers ou CamelCase complet
    (« streamdeck » ne contient plus « amd », « motorola » plus « tor »).
    Une clé matche si ses mots forment une tranche contiguë des mots du nom,
    prononcés séparément ou collés. Dans le doute : « Programme non reconnu »."""
    mots = _mots(name) + _mots(_exe_nom(command))
    for km, cle_jointe, texte, niveau in _RULES:
        n = len(km)
        for i in range(len(mots) - n + 1):
            if mots[i:i + n] == km:
                return texte, niveau
        for i in range(len(mots)):
            colle = ""
            for j in range(i, len(mots)):
                colle += mots[j]
                if colle == cle_jointe and j - i + 1 >= n:
                    return texte, niveau
                if len(colle) >= len(cle_jointe):
                    break
    return UNKNOWN, "unknown"


def is_disabled(hive, approved, name):
    """StartupApproved : 2 = activé, 3 = désactivé (+horodatage). Certaines machines
    portent d'autres octets (7 observé) : la règle du Gestionnaire des tâches est
    « impair = désactivé », et un octet inconnu ne doit JAMAIS compter comme actif."""
    data = registry.read(hive, approved, name)
    if not isinstance(data, (bytes, bytearray)) or len(data) == 0:
        return False
    return data[0] != 2


def _exe_existe(cmd) -> bool:
    """Le fichier visé par la commande existe-t-il encore ? Une commande qui ne vise
    pas un chemin (URL, ms-settings, vide) compte comme existante : on ne déclare
    « introuvable » que ce qu'on peut prouver disparu.

    Sans guillemets, le chemin peut contenir des espaces sans délimiteur
    ("C:\\Program Files\\App\\app.exe -min") : on teste les préfixes de mots
    dans l'ordre croissant, chacun nu ou suffixé ".exe". Un dossier ne prouve
    rien (seul un fichier compte) ; si aucun préfixe n'est un chemin absolu,
    on ne peut rien prouver : la commande reste « existante »."""
    c = str(cmd or "").strip()
    if not c or c.lower().startswith(("http://", "https://", "file:", "ms-settings", "cmd ", "explorer")):
        return True
    if c.startswith('"'):
        parts = c.split('"')
        path = os.path.expandvars(parts[1] if len(parts) >= 2 else c)
        if not os.path.isabs(path):
            return True
        return os.path.exists(path)
    mots = c.split()
    candidats = []
    for i in range(1, len(mots) + 1):
        cand = " ".join(mots[:i])
        candidats.append(cand)
        candidats.append(cand + ".exe")
    absolus = 0
    for cand in candidats:
        p = os.path.expandvars(cand)
        if os.path.isabs(p):
            absolus += 1
            if os.path.isfile(p):
                return True
    return absolus == 0


def list_entries():
    """Liste identique au Gestionnaire des tâches : clés Run (HKCU/HKLM/32 bits) + dossiers Démarrage + tâches UWP.
    L'état activé/désactivé est lu dans StartupApproved, exactement comme Windows."""
    out = []
    for hive, key, approved, scope in SOURCES:
        for name, cmd in registry.list_values(hive, key):
            text, level = _hint(name, str(cmd))
            absent = not _exe_existe(cmd)
            out.append({"kind": "reg", "hive": hive, "name": name, "command": str(cmd), "approved": approved,
                        "value_name": name, "scope": scope, "missing": absent,
                        "where": registry.full_path(hive, key), "hint": text, "level": level,
                        "enabled": not absent and not is_disabled(hive, approved, name)})
    for hive, folder, approved, scope in dossiers_demarrage():
        try:
            files = [f for f in os.listdir(folder) if f.lower() != "desktop.ini"]
        except OSError:
            continue
        for f in files:
            text, level = _hint(f, f)
            out.append({"kind": "reg", "hive": hive, "name": os.path.splitext(f)[0], "command": os.path.join(folder, f),
                        "approved": approved, "value_name": f, "scope": scope,
                        "where": folder, "hint": text, "level": level,
                        "enabled": not is_disabled(hive, approved, f)})
    seen_uwp = set()
    for e in _uwp_entries():
        pkg = e["name"].split(" (")[0].strip().lower()
        if pkg in seen_uwp:
            continue
        seen_uwp.add(pkg)
        out.append(e)
    for i, e in enumerate(out):
        e["id"] = f"s{i}"
    return out


def _write_state(hive, approved, name, enabled):
    if enabled:
        data = b"\x02" + b"\x00" * 11
    else:
        ft = int((time.time() + 11644473600) * 10_000_000)
        data = b"\x03\x00\x00\x00" + struct.pack("<Q", ft)
    registry.write(hive, approved, name, data, kind=3)


def set_many(entries, enabled, journal):
    done, failed, items = [], [], []
    for e in entries:
        try:
            if e["kind"] == "uwp":
                prev = registry.read("HKCU", e["key"], "State")
                registry.write("HKCU", e["key"], "State", 2 if enabled else 1)
                ok = (registry.read("HKCU", e["key"], "State") in (2, 4)) == enabled
                it = {"kind": "uwp", "hive": "HKCU", "key": e["key"], "name": e["name"], "prev": prev}
            else:
                vname = e.get("value_name") or e["name"]
                _write_state(e["hive"], e["approved"], vname, enabled)
                ok = is_disabled(e["hive"], e["approved"], vname) != enabled
                it = {"kind": "reg", "hive": e["hive"], "approved": e["approved"], "name": e["name"],
                      "value_name": vname, "was_enabled": not enabled}
            if ok:
                done.append(e)
                items.append(it)
            else:
                failed.append((e["name"], T("Windows n'a pas gardé le changement : ce programme "
                                         "est protégé par Windows ou par une règle de ton "
                                         "organisation. Rien n'est cassé, réessaie depuis "
                                         "« Applications au démarrage » si besoin.")))
        except (PermissionError, OSError) as ex:
            failed.append((e["name"], refus.motif_refus(T("modifier le démarrage de « {v0} »").format(v0=e["name"]),
                                                       erreur=ex)))
        except Exception as ex:
            failed.append((e["name"], refus.motif_refus(T("modifier le démarrage de « {v0} »").format(v0=e["name"]),
                                                       erreur=ex)))
    if done:
        if len(done) == 1:
            verb = T("activé") if enabled else T("désactivé")
            line = T("Démarrage : {v0} programme {v1}").format(v0=len(done), v1=verb)
        else:
            verb = T("activés") if enabled else T("désactivés")
            line = T("Démarrage : {v0} programmes {v1}").format(v0=len(done), v1=verb)
        journal.add("startup", line, ", ".join(e["name"] for e in done), {"items": items})
    return len(done), failed


@register_undo("startup")
def _undo(d):
    items = d.get("items") or [{"kind": "reg", "hive": d["hive"], "approved": d.get("approved", APPR + r"\Run"),
                                "name": d["name"], "was_enabled": d["was_enabled"]}]
    for it in items:
        if it.get("kind") == "uwp":
            if it["prev"] is None:
                registry.delete(it["hive"], it["key"], "State")
            else:
                registry.write(it["hive"], it["key"], "State", it["prev"])
        else:
            _write_state(it["hive"], it["approved"], it.get("value_name") or it["name"], it["was_enabled"])
    return (T("{v0} programme remis à l'état d'origine.") if len(items) == 1
            else T("{v0} programmes remis à l'état d'origine.")).format(v0=len(items))
