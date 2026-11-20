# TidyDeck

**Nettoyer, ranger et calmer Windows.** · **Clean, tidy, and calm Windows.**

🇫🇷 [Français](#français) · 🇬🇧 [English](#english)

Gratuit · Libre (GPL-3.0) · Windows 10 et 11 · Sans compte · Sans télémétrie

[⬇️ Télécharger / Download](https://github.com/TidyDeckApp/TidyDeckApp/releases/latest) · [🌐 Site / Website](https://tidydeckapp.github.io)

---

## Français

TidyDeck est un logiciel gratuit qui montre avant d'agir, range sans rien supprimer d'un coup, et fait taire ce qui te distrait. Il est pensé pour les profils TDAH, les gamers et les daltoniens.

### Télécharger

Version **0.6.2** pour Windows 10 et 11. Il n'y a rien à installer : décompresse le dossier où tu veux et lance `TidyDeck.exe`. Pour le retirer, supprime le dossier.

➡️ [Page de téléchargement](https://github.com/TidyDeckApp/TidyDeckApp/releases/latest) · [Site](https://tidydeckapp.github.io)

### Nouveautés de la 0.6.2

- **Rappels** : chaque rappel (hydratation, repas, snacks, pause visuelle, étirements, créneaux personnalisés) règle son **Son**, son **Visuel**, les deux ou aucun. Un lien « Appliquer à tous les rappels » reprend un réglage pour toute la page.
- **Mode Discret** : il masque ce que TidyDeck affiche (nom d'utilisateur, nom du PC, chemins personnels), pas les autres applications. Le nom du PC est aussi masqué dans `debug.log`.
- **Fichiers et résidus** : protections renforcées (dossiers de sauvegardes et de données, fichiers `.bak`). Seul le premier niveau sous une zone est proposé. Rien n'est supprimé.
- **Mise en page** : en fenêtre étroite, les textes et cases ne sont plus coupés.

### Ce qu'il fait

- **Nettoyer** : fichiers temporaires et caches. Tu vois la liste et la place gagnée avant de valider. Ce qui est nettoyé va en quarantaine pendant 7 jours : tu peux le récupérer.
- **Calmer Windows** : moins de suggestions, d'applications recommandées et de messages « Découvrez Windows ». Seuls tes réglages utilisateur sont touchés, et chacun s'annule en le décochant.
- **Les plus gros fichiers** : la liste de ce qui prend de la place, en lecture seule. TidyDeck te montre, il ne supprime rien pendant qu'il regarde.
- **Rappels bien-être** : des notifications douces pour faire une pause, t'hydrater ou lâcher l'écran, entièrement paramétrables ou désactivables, avec un minuteur de rendez-vous conçu pour les profils TDAH.
- **Journaux** : un journal de tout ce qui a été fait, et un mode spécial pour le jeu et le live.

### Ce qu'il ne fait pas

- Pas de « nettoyeur de registre », pas de « boost » miracle.
- Pas de compte, pas de publicité, pas de télémétrie.
- Pas de service, de tâche planifiée ni de pilote installés.
- Aucune donnée envoyée. Le seul accès au réseau est le bouton « Mises à jour », et seulement si tu cliques dessus.

**Une seule chose est définitive : vider la Corbeille.** C'est ce qu'on demande à TidyDeck, et il te le rappelle à chaque fois.

### Quatre modes

Tu choisis comment TidyDeck te parle et ce qu'il te montre. Tu peux en combiner plusieurs.

- **Sérénité** : six entrées visibles seulement, des phrases courtes, rien qui change sans ton accord.
- **Avancé** : toutes les pages et plus d'options.
- **Daltonien** : un symbole, un mot et une différence de luminosité pour chaque état. Jamais la couleur seule.
- **Discret** : masque à l'écran ton nom d'utilisateur, le nom du PC et les chemins personnels. Pratique en live.

### Vérifier le fichier

Empreintes SHA-256 de la version 0.6.2 :

| Fichier | SHA-256 |
|---|---|
| `TidyDeck-0.6.2-win64.zip` | `669cdf877344dc7724c133459bd054abab2df7939890a5c2da9c3b4ee4916cd0` |
| `TidyDeck-0.6.2.zip` (code source) | `2feb56baa9bb84ae4316699ef03c3194c5df966f6d70c7eb94247e374195579e` |

Sur ton PC, dans une invite de commandes :

```
certutil -hashfile "TidyDeck-0.6.2-win64.zip" SHA256
```

Si le résultat est différent, n'ouvre pas le fichier.

Analyses VirusTotal du 20 novembre 2026 : [win64 : 0 / 63](https://www.virustotal.com/gui/file/669cdf877344dc7724c133459bd054abab2df7939890a5c2da9c3b4ee4916cd0/detection) · [source : 0 / 64](https://www.virustotal.com/gui/file/2feb56baa9bb84ae4316699ef03c3194c5df966f6d70c7eb94247e374195579e/detection). Un score est une photo à un instant donné, pas une garantie : c'est pour cela que le code est ouvert. Détails sur la [page d'analyse](https://tidydeckapp.github.io/analyse-antivirus.html).

**Un avertissement de Windows ?** TidyDeck n'est pas encore signé numériquement. Windows (SmartScreen) peut afficher « Windows a protégé votre ordinateur ». Si tu as vérifié l'empreinte, choisis « Informations complémentaires », puis « Exécuter quand même ». Détails dans la [FAQ](https://tidydeckapp.github.io/faq.html#smartscreen).

### Lancer depuis les sources

Python 3.10 ou plus, avec Tkinter. Aucune dépendance à installer.

```
python main.py
```

### Signaler un problème, proposer une idée

Sur la [page des signalements](https://github.com/TidyDeckApp/TidyDeckApp/issues). Décris ce que tu as fait, ce que tu attendais et ce qui s'est passé. Une capture d'écran aide beaucoup.

### Licence et soutien

GPL-3.0 · © 2026 Florius. Sans aucune garantie, dans les limites permises par la loi.
TidyDeck est gratuit et le restera. Un don est possible, jamais nécessaire : [ko-fi.com/tidydeck](https://ko-fi.com/tidydeck).

---

## English

TidyDeck is a free tool that shows you before taking action, tidies without deleting everything at once, and silences distractions. It is designed for ADHD profiles, gamers and colorblind users.

### Download

Version **0.6.2** for Windows 10 and 11. There is nothing to install: unzip the folder anywhere and run `TidyDeck.exe`. To remove it, delete the folder.

➡️ [Download page](https://github.com/TidyDeckApp/TidyDeckApp/releases/latest) · [Website](https://tidydeckapp.github.io/index-en.html)

### What's new in 0.6.2

- **Reminders**: each reminder (hydration, meals, snacks, eye break, stretching, custom slots) sets its own **Sound**, **Visual**, both, or neither. An "Apply to all reminders" link copies a setting across the page.
- **Discreet mode** hides what TidyDeck displays (user name, PC name, personal paths), not other apps. The PC name is also masked in `debug.log`.
- **Files and leftovers**: stronger protections (backup and data folders, `.bak` files). Only the first level under a zone is proposed. Nothing is deleted.
- **Layout**: in narrow windows, text and checkboxes are no longer cut off.

### What it does

- **Clean**: temporary files and caches. You see the list and the space recovered before confirming. Cleaned items go into quarantine for 7 days, so you can restore them.
- **Calm Windows**: fewer suggestions, recommended apps and "Discover Windows" messages. Only your user settings are changed, and each one can be undone by unchecking it.
- **Largest files**: the list of what takes up space, read-only. TidyDeck shows you; it deletes nothing while it looks.
- **Wellness reminders**: gentle notifications to take a break, hydrate or step away from the screen, fully customizable or disableable, with an appointment timer built for ADHD profiles.
- **Logs**: a record of everything that was done, and a dedicated mode for gaming and livestreaming.

### What it does not do

- No registry cleaner, no miracle "boost".
- No account, no ads, no telemetry.
- No service, scheduled task or driver installed.
- Nothing is sent anywhere. The only network access is the "Check for updates" button, and only if you click it.

**Only one thing is permanent: emptying the Recycle Bin.** That is what you ask TidyDeck to do, and it reminds you every time.

### Four modes

You choose how TidyDeck talks to you and what it shows. You can combine several.

- **Serenity**: only six visible entries, short sentences, nothing changes without your consent.
- **Advanced**: all pages and more options.
- **Colorblind**: a symbol, a word and a brightness difference for every state. Never color alone.
- **Discreet**: hides your username, the PC name and personal paths on screen. Handy when streaming.

### Verify the file

SHA-256 hashes for version 0.6.2:

| File | SHA-256 |
|---|---|
| `TidyDeck-0.6.2-win64.zip` | `669cdf877344dc7724c133459bd054abab2df7939890a5c2da9c3b4ee4916cd0` |
| `TidyDeck-0.6.2.zip` (source code) | `2feb56baa9bb84ae4316699ef03c3194c5df966f6d70c7eb94247e374195579e` |

On your PC, in a Command Prompt:

```
certutil -hashfile "TidyDeck-0.6.2-win64.zip" SHA256
```

If the result is different, do not open the file.

VirusTotal scans of 20 November 2026: [win64: 0 / 63](https://www.virustotal.com/gui/file/669cdf877344dc7724c133459bd054abab2df7939890a5c2da9c3b4ee4916cd0/detection) · [source: 0 / 64](https://www.virustotal.com/gui/file/2feb56baa9bb84ae4316699ef03c3194c5df966f6d70c7eb94247e374195579e/detection). A score is a snapshot in time, not a guarantee, which is why the code is open. Details on the [analysis page](https://tidydeckapp.github.io/analyse-antivirus-en.html).

**A Windows warning?** TidyDeck is not digitally signed yet. Windows SmartScreen may show "Windows protected your PC". If you have checked the hash, click "More info", then "Run anyway". Details in the [FAQ](https://tidydeckapp.github.io/faq-en.html#smartscreen).

### Run from source

Python 3.10 or later, with Tkinter. No dependencies to install.

```
python main.py
```

### Report a problem or suggest an idea

On the [issues page](https://github.com/TidyDeckApp/TidyDeckApp/issues). Describe what you did, what you expected and what happened. A screenshot helps a lot.

### License and support

GPL-3.0 · © 2026 Florius. Without any warranty, to the extent permitted by law.
TidyDeck is free and will stay that way. A donation is possible, never required: [ko-fi.com/tidydeck](https://ko-fi.com/tidydeck).
