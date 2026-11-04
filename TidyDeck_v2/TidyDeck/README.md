# TidyDeck

Nettoyer, ranger et calmer Windows — pour les gamers, les profils TDAH, les daltoniens et tout le monde.
Windows 10 / 11 · **aucune dépendance** · `TidyDeck.exe` fourni,
ou `python main.py` depuis la source (Python **3.10+**)

## Installer et lancer

**Depuis l'exécutable — rien à installer (recommandé)**

1. Télécharge `TidyDeck-0.6.0-win64.zip` (l'exécutable), vérifie l'empreinte (section suivante).
2. Décompresse le dossier `TidyDeck\` où tu veux, par exemple `C:\TidyDeck`.
3. Double-clique sur `TidyDeck.exe`. Windows 10 ou 11, **aucun droit administrateur
   au démarrage** : l'élévation n'est demandée que si tu cliques une fonction qui la
   réclame vraiment (services, point de restauration), et c'est Windows qui te la demande.

**Depuis la source — pour lire et modifier le code**

- Python **3.10 ou plus récent**, **aucune dépendance pip** : `python main.py`
- `python main.py --minimized` démarre réduit dans la barre des tâches (c'est ce que
  TidyDeck utilise quand il se lance avec Windows).
- Tu veux un vrai programme d'installation ? `packaging/tidydeck.iss` (Inno Setup 6) est
  fourni, optionnel : TidyDeck reste portable, l'installeur ne fait que poser le dossier
  et créer les raccourcis. La construction de l'exécutable est décrite dans
  `DISTRIBUTION.md` (`packaging/TidyDeck.spec`).
- **Premier lancement** : une fenêtre « Bienvenue 👋 » demande le thème, la taille de texte
  et les modes (Sérénité, avancé, daltonien, Discret, son, rappels). Tout part
  **désactivé** : c'est toi qui actives ce qui te va, et chaque choix est **enregistré
  immédiatement** — il sera retrouvé au lancement suivant. Rien n'est définitif : tout se
  change à tout moment dans « Apparence et modes ».

## Vérifier ton téléchargement

Chaque livrable est accompagné de son empreinte **à côté** du zip
(`TidyDeck-0.6.0.zip.sha256`, `TidyDeck-0.6.0-win64.zip.sha256`) et jamais à l'intérieur :
une empreinte écrite dans le fichier qu'elle authentifie changerait en l'écrivant.

```bat
certutil -hashfile TidyDeck-0.6.0-win64.zip SHA256
certutil -hashfile TidyDeck-0.6.0.zip SHA256
```

Compare le résultat avec `TidyDeck-0.6.0.zip.sha256`. **Si les empreintes diffèrent,
n'exécute pas le fichier** : le téléchargement est corrompu ou modifié.

## Désinstaller

TidyDeck n'ajoute rien au registre de désinstallation, aucun service, aucune tâche
planifiée, aucun pilote, aucun fichier hors de son dossier et de `%LOCALAPPDATA%\TidyDeck\`.

1. Ferme TidyDeck (icône dans la barre des tâches → Quitter).
2. Supprime son dossier.
3. Pour tout effacer, supprime aussi `%LOCALAPPDATA%\TidyDeck\` (configuration,
   journaux, quarantaine).

**Avant de supprimer, deux choses à savoir :**

- **Ce qui est encore en quarantaine est perdu avec le dossier.** Récupère tes fichiers
  ou vide la quarantaine depuis **Journaux** avant de supprimer.
- **Les réglages « Calmer Windows » déjà appliqués restent appliqués.** Ouvre la page,
  décoche-les et valide pour remettre Windows comme avant : sinon tes réglages restent
  modifiés, sans TidyDeck pour les annuler.
- **Si tu as déplacé ou supprimé le dossier puis relancé TidyDeck ailleurs**, l'ancienne valeur
  « démarrer avec Windows » qui pointait vers le fichier disparu est retirée d'office au premier
  lancement, et le retrait est noté dans **Journaux** : rien à chercher dans le Registre, et pas
  d'erreur de Windows à chaque ouverture de session.

## Principes (vérifiables dans le code)

- **Aperçu par défaut, mode express en option.** Normalement tu vois la liste et la place concernée avant
  de confirmer. Si tu coches **« Mode express »** sur l'Accueil, TidyDeck range directement les fichiers
  de la liste blanche (Temp + Caches) : l'étape de confirmation saute, tout reste annulable.
- **Annulable, sauf une exception assumée.** Les fichiers nettoyés sont *déplacés en quarantaine*
  (7 jours par défaut) et annulables depuis **Journaux**. La seule exception, signalée partout où elle
  compte : **vider la Corbeille est immédiat et définitif** — c'est justement ce qu'on lui demande.
  L'aperçu du Nettoyage le rappelle explicitement quand la Corbeille est dans la sélection.
- **Point de restauration Windows** tenté avant les réglages (nécessite le mode admin ; sinon on prévient).
- **Pas de nettoyeur de registre**, pas de « boost ». Seulement : temporaires, caches, démarrage
  (désactivé, pas supprimé), réglages utilisateur Windows.
- **Aucune collecte, aucun envoi.** Le seul accès réseau est le bouton « Mises à jour », sur clic.
- **Transparence** : chaque ligne montre *ce que c'est, où c'est (chemin réel), le risque*, avec un
  bouton « Ouvrir l'emplacement ».
- **La couleur ne porte jamais l'information seule** : symbole + mot + luminance, dans les 3 thèmes et
  les 2 palettes. Contrastes texte ≥ 4,5:1, jauges ≥ 3:1.

## Où est la liste de TOUT ce qui peut être touché ?

| Quoi | Fichier |
|---|---|
| Fichiers/caches nettoyables | `Shared/Constants/catalog.py` |
| Réglages Windows (clés de registre exactes) | `Core/Tweaks/tweaks.py` |
| Démarrage (clés `Run` / `StartupApproved`) | `Core/Startup/startup.py` |
| Catégories de tri des Téléchargements | `Core/Storage/storage.py` |
| Applications préinstallées (liste noire + protégées) | `Core/Debloat/debloat.py` |

Données de TidyDeck : `%LOCALAPPDATA%\TidyDeck\` (journal, quarantaine, config).

## Sécurité du débloat (`Core/Debloat/debloat.py`)

Trois verrous, dans cet ordre, avant toute désinstallation :

1. **Regex du nom** — `^[A-Za-z0-9][A-Za-z0-9.\-]{0,127}$`. Aucun caractère d'injection
   (`;`, `|`, backtick, `&`, guillemets) ne passe dans le PowerShell.
2. **Liste protégée** — Xbox, Game Bar / GameOverlay, `SecHealthUI`, Windows App Runtime,
   codecs vidéo/image (HEIF, WebP, HEVC, MPEG2, AV1, AVC, RAW), Language Experience Pack,
   Winget, Store Purchase App. Jamais décochables, jamais listés comme nettoyables.
3. **Refus système** — toute package `NonRemovable` ou `IsFramework` est refusée. Si la lecture
   de ces flags échoue, on refuse aussi (fail-closed).

Les applis sponsorisées tierces sont détectées par mots-clés sur les paquets **réellement installés**,
jamais en dur.

## Modes

| Mode | Clé | Effet | Indépendant ? |
|---|---|---|---|
| 🎮 Mode Jeu | `game_mode_on` | Les rappels bien-être attendent la fin de la session | Oui |
| 🕶️ Mode Discret | `stream_mode` | Masque à l'écran nom d'utilisateur, nom du PC et chemins personnels | Oui |

Les deux sont **totalement indépendants** : activer l'un n'active jamais l'autre. Ils partagent
**une seule bannière** (`UI/components.py` → `ModeBanner`), avec un bouton de sortie immédiate
par mode — **un clic, aucune confirmation**. Le Mode Discret masque ce qui s'affiche à l'écran
dans TidyDeck uniquement ; il n'a aucun effet sur les fenêtres des autres applications.

## Accessibilité

- **3 thèmes** : Clair chaleureux, Sombre, Chaleureux (TDAH).
- **Palette daltonien** (Okabe-Ito) en surcouche, jamais rouge/vert seuls.
- **2 tailles de texte** (Normale, Grande) ; la sidebar suit la taille choisie (polices *et* espacements).
- **2 langues** : français (défaut) et anglais. Choix au premier lancement et dans
  « Apparence et modes », appliqué **immédiatement** (toute l'interface se reconstruit).
  Quasi tout est traduit — menus, boutons, textes, dialogues, messages d'état, titre de la
  fenêtre (~550 entrées, `Shared/Utils/translations.py`). Les conseils détaillés de l'onglet
  Démarrage restent en français pour l'instant : une phrase non traduite reste en français,
  sans plantage ni clé brute à l'écran.
- **Navigation clavier complète** dans la sidebar : ↑ ↓ pour circuler, Entrée pour ouvrir,
  → pour déplier une section, ← pour la replier et remonter. Anneau de focus visible.
- **Sérénité** : 6 entrées visibles, le reste sous « PLUS » (replié). Les nombres laissent
  place à des mots qualitatifs, pas de rouge ni d'orange.
- **Mode avancé** : « Applications préinstallées » n'est accessible qu'avec le mode avancé activé ;
  sinon l'entrée reste visible mais grisée, non cliquable, badge `[Avancé]`. La Sérénité ne
  change que son *placement* (niveau 1 ou sous « PLUS »), jamais sa disponibilité.

## Rappels bien-être

Tout est **désactivé par défaut** (hydratation, repas, 20-20-20, étirements, notifications).
Pas de bouton « Appliquer » : les réglages s'enregistrent tout seuls, comme Apparence et Configuration.

- **Réarmement au démarrage** : le minuteur de rendez-vous est reconstruit depuis la config.
  Si l'heure est passée pendant que TidyDeck était fermé, tu reçois un **« Rendez-vous manqué »**
  (une seule fois, et seulement si c'était dans les 12 h).
- Le rendez-vous est stocké en **date et heure complètes** (`rdv_at`), pas en `HH:MM` seul :
  un RDV après minuit n'est plus pris pour un RDV déjà passé.
- ⚠️ **TidyDeck doit rester ouvert pour te rappeler** — réduit-le dans la barre des tâches,
  mais ne le ferme pas, sinon aucun rappel ne part.

## Version 0.6

### Ce qui change pour toi
- Tu peux voir **ce qui prend le plus de place** sur ton PC, fichier par fichier et dossier par
  dossier, sans rien risque : cette vue ne supprime rien et ne propose aucun bouton pour supprimer.
- TidyDeck sait maintenant **retrouver les résidus d'applications désinstallées** : ces dossiers
  oubliés dans AppData ou ProgramData qui ne correspondent à **aucun** logiciel installé.
  Bouton 🧹 dans *Fichiers et résidus*, **en mode avancé seulement**. Pour l'instant c'est **pour
  consulter** (pourquoi ce dossier est soupçonné, taille, dernière activité, « Ouvrir
  l'emplacement », « Copier ») ; rien ne sera déplacé ni supprimé, et la mise à l'écart
  n'arrivera qu'après validation sur au moins cinq vraies machines.
- **Calmer Windows** dit enfin les vraies choses : « ✔ Appliqué » au lieu de « Actif », et le nom de
  chaque réglage décrit ce qu'il fait (« Masquer les pubs du menu Démarrer », « Empêcher
  l'installation automatique d'applis sponsorisées »…).
- Quand tu retires des applis préinstallées, la page te dit si Windows est **empêché de les
  réinstaller** — et te le fait activer d'abord si ce n'est pas le cas.
- Plus moyen de rester bloqué devant un bouton qui ne fait rien : **« Ouvrir l'emplacement » est grisé
  tant qu'il n'y a rien à ouvrir**, et quand ça échoue on te dit pourquoi et où aller à la place.
- Quand un réglage renvoie au registre, **le chemin complet est copié** pour que tu n'aies qu'à le
  coller, avec la mention « rien n'a été modifié ».

### Notes techniques (0.6)
- **Nouveau : « Les plus gros fichiers / plus gros dossiers »** dans la page *Fichiers et résidus*
  (bouton 🔎). **Pas d'entrée de menu en plus** — la vue remplace la liste de la page, et en
  Sérénité elle reste sous « Plus ».
  - Moteur en **lecture seule stricte** : aucune suppression, aucune écriture, **rien dans le journal**.
    Aucun bouton de suppression nulle part dans la vue.
  - Deux onglets **Fichiers** / **Dossiers**. Les dossiers sont classés **au premier niveau seulement**
    et on **descend dedans** en cliquant (double-clic ou bouton « Entrer »), avec « ↑ Remonter » :
    un dossier et ses sous-dossiers n'apparaissent donc jamais en doublon de comptage.
  - **Zone par défaut = les dossiers de l'utilisateur** (Téléchargements, Documents, Bureau,
    Vidéos, Images), **jamais le disque entier**.
  - **Ignorés sans erreur** : accès refusés, liens symboliques et jonctions (rien n'est compté deux
    fois, on ne sort pas de la zone), ainsi que `Windows`, `Program Files`, `pagefile.sys`,
    `hiberfil.sys`. En mode avancé les dossiers système sont malgré tout listés, marqués
    **« Système, ne pas toucher »**, sans bouton d'action.
  - Chaque ligne : **nom, chemin, taille, date de modification, « Ouvrir l'emplacement »**.
    « Ouvrir l'emplacement » **sélectionne** le fichier dans l'Explorateur (`explorer /select,`)
    au lieu de le lancer.
  - Analyse en arrière-plan avec **drapeau d'annulation testé à chaque dossier** et bouton
    « Arrêter » (« Ça suffit » en Sérénité).
  - **Sérénité** : « Voici ce qui prend le plus de place. Rien n'est supprimé. », **5 premiers
    puis « Voir plus »** jusqu'à 20, tailles arrondies (« environ 4 Go »), couleur **« info »**
    uniquement, jamais d'alerte.
  - **Avancé** : 20 · 50 · 100 lignes, et le bouton **« Copier »** (le chemin complet). En Sérénité + Avancé, ces options sont
    regroupées dans un bloc **« Options » replié**.
  - **Pas de barre de taille dans les lignes** : la taille chiffrée, triée du plus gros au
    plus petit, suffit à comparer ; le visuel reste aéré.
  - **Discret** : chemins masqués, **noms de fichiers non masqués** (un nom n'est pas un chemin) ;
    « Ouvrir l'emplacement » **demande confirmation** avant d'afficher le vrai chemin à l'écran.
  - **Thèmes** : aucune différence.
- **Retrait de la recherche de doublons.** Elle posait trop de problèmes sur les vraies
  machines (fichiers dans le nuage, très gros fichiers relus, faux positifs). Le moteur est
  sauvegardé et pourra revenir un jour avec un vrai banc de test ; la page devient
  **« Fichiers et résidus »**.
- **Retrait de « Ton espace disque en un coup d'œil » de la page *Fichiers et résidus*.**
  Ces cartes existent déjà dans l'« État des lieux » ; elles ne servaient deux fois. La vue
  « Résidus d'applications » adopte au passage le même design que « Fichiers oubliés » :
  tableau « Dossier / Taille · Confiance » et panneau du bas qui explique la ligne
  sélectionnée (zone, chemin, pourquoi, confiance, dernière activité).
- **« Relancer en administrateur » fonctionne enfin avec le Python du Microsoft
  Store.** Le bouton ouvrait la demande UAC, la fenêtre se fermait… et rien ne revenait :
  relancé en élevé, l'alias `WindowsApps\python.exe` du Store échoue en silence, et
  l'enfant élevé arrivait parfois avant que l'ancienne fenêtre ait rendu le mutex « instance
  unique » — il croyait donc voir un autre TidyDeck ouvert et partait sans rien dire.
  La relance résout désormais le **vrai interpréteur** (`pythoncore`/`pythonw`, jamais
  l'alias), passe toujours des chemins absolus, et l'enfant **attend jusqu'à 8 s** la
  libération du mutex du parent avant de déclarer la place prise.
- **Formulations allégées partout où le texte doublait ou peinait** : pluriels honnêtes
  (« 1 fichier ignoré », « 4 fichiers oubliés ») au lieu des « fichier(s) » dans
  « Fichiers oubliés », « Les plus gros fichiers/dossiers » et « Résidus » ; la note
  « dans le nuage » réécrite proprement (« a été ignoré pour éviter de déclencher son
  téléchargement ») ; la phrase d'explication du mode Discret sous la liste retirée
  (surtout de la pédagogie) ; sur Accueil, la phrase du mode express dit franchement que
  l'étape de confirmation saute, et le pavé administrateur tient en une ligne ; dans
  Services, le détail d'un service ne coupe plus sa dernière phrase (les doublons avec le
  sous-titre de page sont tombés) ; « Rappels bien-être » : les quatre positions des
  pop-ups tiennent sur une seule ligne ; dans « Les plus gros », la barre proportionnelle
  entre le nom et la taille a été retirée (la taille chiffrée et le tri suffisent).
- **Scans annoncés par une barre de chargement** (« Les plus gros fichiers », « Résidus ») :
  le texte « Analyse en cours… rien n'est supprimé » doublait le sous-titre de la page ;
  il disparaît, la barre animée prend le relais. Dans « Les plus gros fichiers », la ligne
  « Zone analysée : Mes dossiers / Disque entier… » et le rappel « Zone : … » sont retirés —
  chaque ligne affiche déjà son chemin, et les onglets Fichiers/Dossiers suffisent.
- **Encore moins de doublons à l'écran** : dans « Résidus d'applications », la phrase
  « TidyDeck ne fait que te les montrer : rien n'est supprimé » (déjà dite plus haut) est
  retirée, comme le rappel « Consultation seule… » en bas de page ; l'espace gagné profite
  à la liste. « ↑ Remonter » n'apparaît plus qu'après un double-clic dans un dossier.
  Une infobulle « Copier le chemin d'accès » guide le bouton « Copier ».
- **Jeu et live : deux contrôles corrigés.** « Applications en arrière-plan » a disparu
  (le réglage n'existe plus sous Windows 11). « Planification GPU accélérée » ne crie plus
  « Désactivée ou non prise en charge » quand la clé `HwSchMode` est absente : beaucoup de
  pilotes récents l'activent par défaut sans rien écrire dans le registre — la ligne dit
  désormais « Réglée par le pilote (valeur par défaut) : fie-toi à l'affichage de Windows ».
- **Réglages — Configuration : ordre Lancement automatique, puis Notifications, puis Son**,
  juste sous le comportement de la fenêtre ; tout tient dans un seul bloc.
- **Réglages — Configuration : tout est vraiment enregistré.** Le choix sonore du mode live,
  le son des notifications, « Ne pas déranger », le rappel différé… étaient affichés mais
  perdus au redémarrage (seuls l'apparence et le lancement automatique étaient sauvés).
  Chaque changement est maintenant écrit dans la configuration sur-le-champ et retrouvé au
  lancement suivant — vérifié par `tests/test_prefs_persistance.py`.
- **Le bouton « ← Retour » a disparu** de « Les plus gros fichiers » et de « Résidus
  d'applications » : on change de page avec les boutons du haut de la fenêtre, le bouton du
  bas ne faisait que prendre la place.
- **« Résidus d'applications » plus lisible** : la liste occupe au moins 4 lignes (avant : 2,
  il fallait agrandir la fenêtre pour voir quoi que ce soit), l'introduction tient en une
  phrase, et l'espace gagné va à la liste.
- **« Désactiver les programmes inutiles au démarrage » ne touche jamais un VPN.** Les clients
  VPN (Mullvad, NordVPN, ExpressVPN, Cisco AnyConnect) sont classés « ⚖ Selon ton usage »
  avec la phrase « le VPN ne se lancera plus tout seul », jamais « sans risque » : le bouton
  rapide du mode Sérénité les laisse toujours tranquilles, comme les antivirus et le cœur de
  Windows (`tests/test_demarrage_surete.py`).
- **Nouveau : « Résidus d'applications désinstallées »** (page *Fichiers et résidus*, bouton 🧹,
  **mode avancé uniquement, invisible en Sérénité**). Phase 0 : **lecture seule stricte** — la
  vue ne déplace rien, ne supprime rien, n'écrit nulle part ; la quarantaine est reportée à une
  Phase 1 qui n'arrivera qu'après validation sur au moins 5 machines de test sans faux positif.
  - Moteur `Core/Storage/residus.py` : les programmes installés viennent de **trois sources du
    registre** (`Uninstall` HKLM 64 bits, `Wow6432Node`, HKCU — lecture pure, jamais d'écriture),
    du menu Démarrer et des noms de paquets Microsoft Store. **Aucun PowerShell, aucune
    commandlet, zéro réseau.**
  - Zones analysées : `%APPDATA%`, `%LOCALAPPDATA%`, `%PROGRAMDATA%`, **premier niveau seulement**.
    Jamais de suivi de lien ou de
    jonction, jamais un dossier nuage (OneDrive, Dropbox), jamais les zones de sauvegardes de
    jeux, de documents ou de navigateurs.
  - Un dossier n'est proposé que si **aucun logiciel installé n'y correspond** : le nom du
    dossier est comparé au nom, à l'éditeur et au dossier d'installation de chaque logiciel
    (égalité, inclusion, distance d'édition ≤ 2). Le moindre doute — `Adobe Acrobad` à côté
    d'`Adobe Acrobat`, un dossier `Google` alors que Chrome est installé — **protège** le
    dossier : il n'est jamais affiché. Les anciens motifs « Programme installé / Éditeur /
    Plus d'un Go sans activité » sont supprimés ; le seul motif restant est
    « **Aucun logiciel installé de ce nom · inactif depuis N mois** ». Confiance
    **« ✔ Élevée »** au-delà de 6 mois d'inactivité, sinon **« ~ Moyenne »**. Chaque ligne
    porte son « Pourquoi : … », sa taille arrondie et sa dernière activité.
  - Tailles minuscules écartées (**moins de 1 Mo = bruit**), et les dossiers dont le nom porte
    « save », « profile », « config » ou « backup » ne sont **jamais** proposés, même sans
    correspondance. Garde-fou : si la liste des logiciels installés est **illisible**
    (compte limité) — ou même simplement **amputée du registre** (il ne resterait que
    le menu Démarrer et le Store) —, **rien** n'est proposé et la vue le dit franchement.
  - Garde-fous de temps : budget d'analyse, bouton **« Arrêter »**, mention « certains dossiers
    n'ont pas pu être vérifiés » si la liste est partielle ; un dossier illisible est compté
    « non lu », **jamais affiché comme 0 octet**.
  - Tests `tests/test_residus.py` : moteur sur arbre factice (T1-T9, zéro écriture vérifiée par
    empreinte avant/après) + vue (T10-T12 : textes, mode Discret, absence totale de code de
    suppression ou de quarantaine).
- **Suppression de la taille de texte « Très grande ».** Elle n'apparaît plus dans le thème
  (Apparence) ni à l'installation. Une configuration qui la contenait encore bascule
  automatiquement sur « Grande », et le rendu ne plante sur aucune valeur inconnue.
- **Calmer Windows : le vocabulaire dit ce qui se passe.** La colonne État affiche
  « ✔ Appliqué » (et non « Actif ») — « ✕ Pas appliqué » et « ⚠ Défait (mise à jour ?) »
  restent tels quels. Le sous-titre et le message « Rien à changer » suivent la même logique
  (appliquer / remettre, plus « activer »). Le bloc « À quoi ça sert ? » nomme enfin le vrai
  problème : les **pubs, suggestions et applis sponsorisées**, pas les « sons de système ».
- **Noms des réglages = une action.** Chaque réglage se lit maintenant comme ce qu'on fait :
  « Masquer les pubs et suggestions du menu Démarrer », « Masquer les astuces et notifications
  “découvrez Windows” », « Masquer les pubs de l'écran de verrouillage », « Masquer les
  suggestions dans Paramètres », « Empêcher l'installation automatique d'applis sponsorisées »,
  « Masquer les annonces de l'Explorateur », « Désactiver l'identifiant publicitaire ».
  **Seuls les libellés changent : les identifiants (`start_ads`, `tips`, `silent_apps`…) et les
  clés de registre sont inchangés**, donc le journal et l'annulation continuent de fonctionner.
- **Applications préinstallées : le lien avec Calmer Windows est rappelé.** En haut de la page, une
  ligne dit si le réglage « Empêcher l'installation automatique d'applis sponsorisées » est
  appliqué : soit « Déjà fait : … ce que tu retires ne reviendra pas », soit l'invitation à
  l'activer avant de retirer quoi que ce soit. Si le réglage est illisible, l'avertissement
  s'affiche (fail-safe).
- **Audit complet des redirections** (tout ce sur quoi on clique pour « aller vérifier ») :
  - **`ms-settings:startup` n'existe pas.** La valeur par défaut de l'ouvreuse de page était
    cette page fantôme ; c'est maintenant `startupapps` (vérifié par test).
  - **Repli réel sur les pages retirées.** `os.startfile()` *réussit* même sur une URI
    `ms-settings:` inconnue — Windows ouvre « Paramètres introuvables » sans signaler d'erreur.
    Le repli `["privacy-backgroundapps", "appsfeatures"]` ne se déclenchait donc **jamais** sous
    Windows 11. Une table `MS_SETTINGS_REMOVED` (par numéro de build) + `MS_SETTINGS_ALIASES`
    résout maintenant la vraie page avant d'ouvrir.
  - **Registre : on te donne le chemin.** `regedit` ne sait pas se positionner sur une clé, il
    s'ouvrait à la racine. Le chemin complet (`HKEY_CURRENT_USER\…`) est maintenant **copié dans
    le presse-papiers** et affiché dans le détail, avec la mention « Rien n'a été modifié : tu es
    en consultation ». Les 8 clés des réglages Calmer Windows ont été vérifiées **réellement
    présentes** sur la machine.
  ### Rapidité — on ne fait plus attendre l'utilisateur
Chiffré sur machine réelle (Windows 11, Ryzen 7 5800X, SSD) :

| Action | Avant | Après |
|---|---|---|
| Page **Info PC** (1ʳᵉ visite, cache chaud) | **5 254 ms** | **151 ms** |
| Relecture du matériel à chaque lancement | 4,6 s | **0–9 ms** |
| Fin d'une tâche de fond (latence d'affichage) | jusqu'à 120 ms | **40 ms** |
| Changement d'onglet (moyenne, visite ≥ 2) | 37 ms | 37 ms (inchangé, déjà instantané) |

- **Le relevé matériel est caché sur disque 12 h** (`hardware.json` dans le dossier de
  TidyDeck — spécifications matériel uniquement, rien qui identifie personne). Le matériel
  ne change pas d'un jour au lendemain : le payer 4,5 s à chaque lancement était absurde.
- **Pré-chargement dès l'ouverture de la fenêtre** : même le tout premier relevé part en
  tâche de fond pendant que tu prends tes marques, il ne tombe jamais sur un clic.
- **Deux fois la même lecture = une seule lecture.** Un verrou évite que deux pages ouvertes
  en même temps paient deux fois 4,5 s.
- **Cache intelligent** : fichier absent, abîmé, périmé ou relevé de démo → on relit, et
  seulement. Un cache raté ne casse jamais l'affichage.
- **Les scans qui font attendre se voient.** « Fichiers oubliés » et « Clips et captures de jeu »
  affichaient une simple ligne de texte sans barre d'avancement : ils ont maintenant la barre
  avec le temps estimé (appris des scans précédents) et le carillon de fin, comme les clips.
- **Fermer la fenêtre pendant un scan ne crache plus d'erreur** : le résultat est abandonné
  en silence.

### Le reste des corrections
- **Un mot par situation, pas un mot pour tout.** « ✔ Appliqué » / « ✕ Pas appliqué » désigne
  un réglage que **toi** tu as appliqué : c'est le vocabulaire de *Calmer Windows*. *Démarrage* et
  *Services* parlent de l'état d'une chose qui tourne : « **✔ Actif** » / « **✕ Désactivé** ».
  Dire « Appliqué » pour un service qui tournait déjà faisait croire que TidyDeck avait modifié
  quelque chose qu'il n'avait pas touché. Le symbole ✔/✕ reste collé au mot — la couleur ne porte
  jamais l'information seule, Sérénité et Daltonien compris. Les textes d'attente restent
  explicites : « ⏻ Sera désactivé », « ⏼ Sera réactivé », « ↩ Sera réactivé ».
- **Les fichiers « dans le nuage » ne sont plus jamais touchés.** Un fichier OneDrive
  « matérialisé à la demande » n'existe pas vraiment sur le disque : le moindre accès en
  lecture le **télécharge en entier**. « Fichiers oubliés », « plus gros
  éléments » et clips les **ignorent** (attributs Windows `RECALL_ON_DATA_ACCESS`,
  `RECALL_ON_OPEN`, `OFFLINE`), et la mise en quarantaine **refuse** de les déplacer : un
  placeholder déplacé se transforme en vrai fichier local, et supprimer ce fichier là-bas
  demande un gestionnaire du compte. Quand une liste concerne un dossier synchronisé, un
  avertissement le dit **avant** d'agir, en ne listant que les fichiers concernés ; le pied de
  page « plus gros éléments » indique combien de fichiers ont été laissés de de côté pour
  cette raison. Un test vérifie le drapeau, les deux listes, et le refus de déplacement
  (`tests/test_nuage.py`).
- **Les dossiers sont demandés à Windows, pas devinés par leur nom.** « Téléchargements »
  affiché par l'Explorateur est en réalité `C:\Users\moi\Downloads`, et le dossier peut être
  renommé, déplacé sur un autre disque ou basculé sur OneDrive. Les dossiers Scannés
  (Téléchargements, Documents, Bureau, Vidéos, Images) sont maintenant résolus par leur
  **identifiant Windows** (`SHGetKnownFolderPath`, sans dépendance) — donc trouvés même renommés
  ou redirigés ; idem pour les deux dossiers *Démarrage*. Les noms en dur ne restent qu'un
  repli, et aucun scan ne déclenche de téléchargement (`Shared/Utils/dossiers.py`,
  `tests/test_langues_windows.py`).
- **Un refus de l'organisation n'est plus pris pour un manque de droits.** Quand l'écriture est
  refusée **alors que TidyDeck est élevé**, c'est une règle de groupe : le message le nomme et
  dit que relancer en administrateur ne changerait rien — seul le gestionnaire du poste peut
  lever le blocage. Le code Windows est lu dans le **code de retour de `sc.exe`** (numérique,
  jamais traduit) et non dans sa phrase, qui est traduite ; les codes connus sont expliqués en
  français et le numéro brut reste affiché (`Shared/Utils/refus.py`).
- **Une seule fenêtre de TidyDeck à la fois.** Une instance globale empêche le double lancement
  (le second ouverture se contente de ramener la fenêtre existante), et l'application déclare sa
  sensibilisation au DPI **avant** de créer la fenêtre : sur un écran 125 % ou 150 %, les textes
  ne sont plus flous. Si l'entrée « démarrer avec Windows » pointait vers un fichier supprimé
  (dossier déplacé à la main), elle est retirée **et journalisée** au premier lancement
  (`Shared/Utils/instance.py`, `tests/test_instance.py`).
- **La sortie audio par défaut, sans code compilé.** Matériel infos PC affichait la mauvaise
  valeur car l'ancienne méthode compilait du C# à la volée — signalé par certains antivirus et
  analysateurs de comportement, et inutilisable sous une politique d'exécution stricte.
  La lecture passe maintenant par WinRT (`IMMDeviceEnumerator` via `GetDefaultAudioRenderId`) et
  `Get-PnpDevice`, sans compilation, sans `‑ExecutionPolicy` ; la ligne n'apparaît que si
  Windows répond quelque chose.
- **La colonne « État » prend la place que son texte demande.** Elle était bloquée à 280 px :
  en taille « Grande », « ✕ Pas appliqué · Désactivable sans risque » (352 px) était coupé net.
  Elle se dimensionne maintenant sur le texte le plus long de la page, avec un point de
  suspension si la place manque vraiment — et elle se rajuste quand un choix en attente allonge
  la ligne.
- **Sérénité (Démarrage) : la phrase d'accompagnement wrappe enfin.** En « Grande », elle
  dépassait la fenêtre et se terminait net sur « …sans que tu voies » ; elle suit désormais la
  largeur réelle du bloc, comme sur Calmer Windows.
- **Sidebar : plus rien de coupé en taille « Grande ».** Le menu demandait ~849 px pour
  750 px de fenêtre : « Sauvegarde et transfert » et « À propos » passaient sous le bas
  de l'écran et devenaient inaccessibles. Il se re-compacte maintenant **verticalement**
  (espacements uniquement, jamais les polices) pour tenir, et il respire à nouveau quand on
  replie une section ou qu'on agrandit la fenêtre.
- **Panneau du bas (le détail d'une ligne) : plus jamais écrasé.** En « Grande », la
  sélection d'un réglage n'affichait que 24 px de détail sur 86 demandés — le texte était
  tranché à mi-hauteur sous le bouton. C'est maintenant le **tableau** qui se comprime
  (il a une barre de défilement) et le détail garde toute sa hauteur.
- **Noms de réglages tronqués = un point de suspension, pas une coupure nette.** La colonne
  « Réglage » prend la largeur que demande le nom le plus long dans la place disponible ;
  s'il manque vraiment de la place, le texte se termine par « … » au lieu de s'arrêter
  en plein mot (« …découvrez Wind » ne se voit plus).
- **Moteur « les plus gros fichiers / dossiers » testé pour de vrai** (`tests/test_plus_gros.py`) :
  classement, récursivité sans double comptage, fichiers système jamais comptés, liens
  symboliques et jonctions jamais suivis, annulation, et **lecture seule vérifiée par garde-fous**
  (`os.remove`, `os.rename`, `shutil.rmtree` interdits pendant le scan).
- **Dossier illisible ≠ dossier vide.** Un dossier dont on ne peut pas lire le contenu
  s'affichait « 0 octet » et trompait complétement le classement. Il est maintenant écarté
  du classement et **signalé en pied de page** (« N dossiers inaccessibles non classés —
  il faudrait les droits administrateur »).
- **Le compteur « fichiers parcourus » est juste.** Les fichiers placés directement dans la
  zone analysée n'étaient pas comptés (seuls ceux des sous-dossiers l'étaient) : le pied de
  page affichait 3 là où il y avait 6.
- **Le garde-fou « système » est réveillé.** Un test sur la longueur du dossier parent était
  faux (`dirname("C:\\Users")` fait 3 caractères, pas 2) : `C:\Windows` et
  `C:\Program Files` en racine de disque n'étaient en réalité **jamais** reconnus comme
  système et se trouvaient scannés comme des dossiers ordinaires. C'est corrigé (et testé).
- **Apostrophe droite partout.** L'apostrophe typographique U+2019 s'affiche mal dans
  Tk, dans le presse-papiers et au terminal : elle est bannie du code livré, et un test
  (`tests/test_typographie.py`) échoue si elle réapparaît quelque part.
- **Bouton « Ouvrir l'emplacement » grisé tant qu'il n'y a rien à ouvrir.** Sur les pages non
    encore analysées, il était cliquable et strictement muet ; il part maintenant désactivé.
  - **Lien « Anti-lumière bleue »** passé par l'ouvreuse de page Paramètres : s'il échoue, un
    message dit où trouver la page, au lieu d'un clic sans nouvelle.
  - **Préfixe `ms-settings:` vérifié.** Dans le code les adresses sont écrites sans préfixe
    (`gaming-gamemode`, `startupapps`…), c'est `open_windows_settings()` qui ajoute
    `ms-settings:` à l'ouverture. Trois tests (`PrefixeUriTest`) vérifient que **ce qui part
    réellement vers Windows** commence bien par `ms-settings:` (ou passe par `control.exe` pour le
    Panneau de configuration), y compris pour `gaming-gamemode` et `gaming-gamedvr`.

### Ta machine n'est pas la mienne
Ces corrections viennent du test « et si le PC n'est pas exactement le mien ».

- **Les fichiers « dans le nuage » ne sont plus jamais touchés.** Un fichier OneDrive stocké
  « à la demande » n'occupe presque rien sur le disque : le moindre accès en lecture le
  **télécharge en entier**. Doublons, « fichiers oubliés », « plus gros éléments » et clips les
  **ignorent** désormais (attributs `RECALL_ON_DATA_ACCESS`, `RECALL_ON_OPEN`, `OFFLINE`), et la
  mise en quarantaine **refuse** de les déplacer : déplacer un placeholder le fait passer pour un
  vrai fichier local, et le supprimer là-bas demande un gestionnaire du compte. Quand une liste
  touche un dossier synchronisé, un avertissement le dit **avant** d'agir, en ne listant que les
  fichiers concernés ; le pied de page « plus gros éléments » dit combien de fichiers ont été
  laissés de côté pour cette raison (`tests/test_nuage.py`).
- **Dossiers trouvés par leur identité, pas par leur nom.** « Téléchargements » affiché par
  l'Explorateur est en réalité `C:\Users\moi\Downloads`, et le dossier peut être renommé, passé
  sur un autre disque ou basculé sur OneDrive. Les dossiers scannés (Téléchargements, Documents,
  Bureau, Vidéos, Images) sont maintenant demandés à Windows par leur **GUID de dossier connu** —
  donc trouvés même renommés ou redirigés ; les noms en dur ne restent qu'un repli. Même logique
  pour les deux dossiers *Démarrage* (`Shared/Utils/dossiers.py`, `tests/test_langues_windows.py`).
- **Un blocage d'entreprise n'est plus pris pour un manque de droits.** Quand une écriture est
  refusée **alors que TidyDeck est élevé**, c'est une règle de groupe : le message le nomme et dit
  que relancer en administrateur n'y changera rien — seul le gestionnaire du poste peut lever ça.
  Le numéro d'erreur est lu dans le **code de retour de `sc.exe`**, un nombre qui ne dépend pas de
  la langue de Windows, et non dans sa phrase (`Shared/Utils/refus.py`).
- **Une seule fenêtre à la fois, et nette sur écran haute densité.** Un verrou global empêche le
  double lancement (relancer l'icône ramène la fenêtre existante) ; la sensibilisation au DPI est
  déclarée **avant** la création de la fenêtre, sinon tout est flou à 125 % ou 150 %. Si l'entrée
  « démarrer avec Windows » pointait vers un fichier supprimé (dossier déplacé à la main), elle
  est retirée **et journalisée** au premier lancement.
- **La sortie audio par défaut, sans compiler de code.** L'ancienne méthode compilait du C# à la
  volée : signalé par des antivirus et des analyseurs de comportement, et bloqué par certaines
  politiques d'exécution. Elle passe maintenant par les API Windows natives (WinRT
  `IMMDeviceEnumerator` + `Get-PnpDevice`), sans `Add-Type` et sans `-ExecutionPolicy Bypass` ;
  la ligne reste discrète quand Windows ne répond pas.
- **Nettoyage : « Tout cocher » est un vrai interrupteur.** Un seul bouton bascule tout coché /
  tout décoché (il affichait « Recommandé » quand rien n'était analysé, puis « Décocher » une fois
  le choix fait). Le préréglage sûr redevient **cochable** pour les fichiers temporaires qui
  demandent l'administration : ils restent grisés tant que TidyDeck n'est pas élevé, avec la
  mention « ▲ Droits admin requis » — avant, ils ne pouvaient jamais être cochés, même en étant élevé.
- **Info PC : l'espace disque re-actualisé.** Il affichait le chiffre mis en cache 12 heures plus
  tôt, figé jusqu'au relancement du programme ; seul l'espace libre est relu, les composants
  (CPU, disques, pilotes) gardent leur cache.

### Vérifier les pages sur TA version de Windows
Certaines pages des Paramètres ont changé de nom entre Windows 10 et Windows 11. Le script
fourni `verif_pages_windows.py` fait la vérification en deux temps.

```
python verif_pages_windows.py            # vérification automatique, rien ne s'ouvre
python verif_pages_windows.py --ouvrir   # ouvre chaque page, on coche o / n au fur et à mesure
```

- **La liste des adresses est lue dans le code** (mots-clés `settings=`, appels directs
  `open_windows_settings(...)`) : elle ne peut pas rester fausse parce qu'on a oublié de la
  mettre à jour. Une adresse présente dans le code mais absente de la doc du script est
  comptée comme **souci**.
- Pour chaque adresse il affiche **l'URI réellement transmise à Windows** (préfixe vérifié),
  la **page attendue**, la note Win10/Win11, et le ou les **fichiers d'origine**.
- Il affiche le **build de la machine** et si le repli Windows 11 s'applique, et signale les
  pages documentées mais **plus utilisées** dans le code.
- **Code de sortie** : `0` propre, `1` si un souci automatique ou une page refusée à l'œil.
- Il ne touche à rien : pas de registre, config TidyDeck isolée dans un dossier temporaire
  supprimé à la fin, seul `verif_pages_windows.txt` est écrit.

L'état connu est résumé ci-dessous.

| Adresse | Windows 10 | Windows 11 |
|---|---|---|
| `startupapps` | OK | OK |
| `nightlight` | OK | OK |
| `windowsupdate` | OK | OK |
| `gaming-gamemode` | OK | OK |
| `gaming-gamedvr` | OK | OK |
| `display-advancedgraphics` | OK (liste parfois vide selon le pilote) | OK |
| `control:Microsoft.PowerOptions` | OK (Panneau de configuration) | OK |

**Ce qui reste à confirmer sur une vraie machine Windows 10** : la table de repli est
automatique mais la page *affichée* ne peut pas être vérifiée depuis le code — c'est le rôle du
rapport à cocher. Cette version a été construite et vérifiée sur **Windows 11 build 26200** ;
Windows 10 n'était pas disponible pour un contrôle visuel.

## Version 0.5.2
- **Sidebar : largeur adaptative.** Elle était figée à 220 px et tronquait des noms en
  tailles « Grande » et « Très grande » (« Sauvegarde et transfert », « Applications préinstallées »,
  « Apparence et modes »…). Elle se dimensionne maintenant d'après la largeur réellement
  demandée par la ligne la plus longue, badge compris : 259 px (normale) → 298 (grande) →
  340 (très grande). Plus aucune troncature, et la hauteur reste sous 750 px partout.
- **Largeurs de texte adaptatives partout.** Les `wraplength` codés en dur (900 / 850 / 820)
  ne suivaient pas le rétrécissement de la zone de contenu : le texte était rogné.
  Ils sont re-ajustés automatiquement sur la largeur disponible (`clamp_wrap`, replié au
  redimensionnement). 0 dépassement sur les 72 combinaisons testées.
- **Emplacements « ms-settings » corrigés** (les miens étaient faux, la page tombait dans le vide) :
  Applications au démarrage = `ms-settings:startupapps` · Mode jeu = `gaming-gamemode` ·
  Captures = `gaming-gamedvr` · Windows Update = `windowsupdate`.
- **Services : le bouton « Ouvrir l'emplacement (pour vérifier) » fonctionne.** Il ouvre
  `services.msc` en consultation, avec le nom technique du service affiché sur le bouton.
- **Rappels bien-être** : suppression de la mention « Concerne uniquement les rappels de
  rendez-vous. 0 = silencieux. » sous le volume.
- **« À propos »** : le bloc explicatif « Mode Sérénité » a été retiré dans tous les modes,
  comme demandé. Seule la formulation des **conditions d'utilisation** change en mode Sérénité
  (ton adouci), et le texte juridique intégral reste accessible juste en dessous.

## Version 0.5.1
- **Cases à cocher : on ne coche plus qu'en cliquant sur le petit carré.** Le clic sur le texte d'une
  ligne ne change plus l'état (il sélectionne seulement la ligne). Appliqué partout : Démarrage,
  Rangement, Applications préinstallées, Services, Calmer Windows.
- **Mode daltonien : la barre de volume n'est plus jamais verte.** Elle suit le ton d'information neutre
  (bleu), comme en Sérénité — en Configuration *et* dans Rappels bien-être, dans les 3 thèmes.
- **« Ouvrir l'emplacement (pour vérifier) » fonctionne enfin.** Chaque contrôle expose maintenant son
  emplacement réel : dossier de bibliothèque Steam, page des Paramètres Windows (`ms-settings:`),
  Panneau de configuration (Options d'alimentation), Corbeille, dossier de quarantaine. Le bouton reste
  grisé seulement quand il n'existe aucun emplacement, et affiche un message explicite si l'ouverture
  échoue (droits, application absente) au lieu de ne rien faire.
- **Configuration compactée** : activer « Ne pas déranger pendant un jeu » ne fait plus défiler la page
  en taille normale (bloc réduit à une ligne de choix + une note) ; le repli rend toute la hauteur.
- **Rappels bien-être : plus aucun chevauchement** en tailles « grande » et « très grande » — les lignes
  trop larges (minuteur RDV, notifications, volume) sont réparties sur plusieurs lignes.
- **« À propos » aligné sur le ton Sérénité** : section consacrée au mode Sérénité, et en mode Sérénité
  les conditions d'utilisation sont dites dans un ton adouci — le texte juridique intégral reste
  accessible juste en dessous, rien n'est retiré sur le fond.
- **Repliement « PLUS » validé en Sérénité** : le focus est rendu à l'en-tête de section quand on replie
  depuis une sous-option, la surbrillance de la page active survit, aucune overflow à 3 tailles de texte.

## Version 0.5
Tout tient à l'écran en 1200×750, sans faire défiler la page · nouvelle navigation (sections repliables,
navigation clavier, polices qui suivent la taille de texte) · « Débloat Windows » devient **« Applications préinstallées »**
et passe sous mode avancé · trois verrous de sécurité sur le débloat (regex, liste protégée, refus `NonRemovable`/`IsFramework`) ·
Mode Discret : fail-closed (`•••` en cas de panne), masquage à l'affichage seulement, aucune table alias sur le disque ·
bannière unique partagée Mode Jeu / Mode Discret, sortie en un clic · contrastes corrigés (accent et avertissement
Chaleureux ≥ 4,5:1, jauges ≥ 3:1, titres de sidebar ≥ 4,5:1) · entrée active en gras · Rappels sans bouton
« Appliquer » (enregistrement automatique) · réarmement du minuteur de RDV au démarrage + « Rendez-vous manqué » ·
import de profil validé valeur par valeur (plus d'import QR, qui n'a jamais fonctionné) · suppression du bouton
« Purger la RAM » (purement décoratif).

## Version 0.4
Navigation fluide (chargements lents en arrière-plan avec cache) · Démarrage et Services : cocher/décocher PUIS valider · applis du Store
(« Mobile connecté ») au démarrage · tout cocher/décocher · infos en haut · turbo mesuré + température (LibreHardwareMonitor) ·
cache Opera · plan Performances maximales · Santé PC regroupe Calmer Windows / Nettoyage / Démarrage / Rangement ·
rappels bien-être (eau, repas, 20-20-20, étirements) + « Ne pas déranger pendant un jeu ».

## Version 0.3
Pop-up qui s'ajustent (boutons toujours visibles) · « Calmer Windows » : décocher remet comme avant + relecture de vérification ·
Démarrage : vérification, dossiers Démarrage, 32 bits, « tout désactiver sauf essentiels » · VRAM via nvidia-smi · cartes son USB ·
point de restauration diagnostiqué (admin / protection du système) · services Windows non essentiels · onglets à gauche · tout cocher ·
carillon de fin · jauge « jeux AAA » · mode stream · clips & captures · contrôle SSD/HDD des jeux · rappel mensuel · fiche de score.

## Version 0.2 — retours intégrés
Fenêtre adaptative + barre de boutons qui passe à la ligne · option de la croix (fermer / réduire) · Apparence ne renvoie plus à l'Accueil ·
« Mode d'alimentation » lisible (cause : décodage des accents Windows) · « Journaux et annulations » · Anti-distraction et Confort en deux catégories ·
bouton « Relancer en administrateur » · Accueil Simple/Avancé (OS exact, carte mère, CPU, RAM, GPU, son, tous les disques, S.M.A.R.T., chaleur) ·
caches Steam / Epic / Riot (Vanguard exclu) · Mode Jeu rapide · « Nettoyage doux recommandé » et bouton magique · « PC apaisé » · temps estimé des analyses ·
icônes par catégorie · double signal couleur + symbole + mot · mode Sérénité · frise « Ton parcours » · applications bloquées (fermeture propre).

## Vérification

Balayage automatique des **48 combinaisons** (3 thèmes × daltonien × Sérénité × avancé × 2 tailles de
texte), chaque page visitée : aucune exception, aucun débordement de sidebar, bannière ≤ 30 px à l'échelle
de la taille de texte, contrastes ≥ 4,5:1, aucun temps de chargement anormal (> 2,5 s).
La vue « plus gros fichiers / dossiers » est balayée séparément sur les **32 combinaisons**
(daltonien × Sérénité × avancé × Discret × 2 tailles) : aucun bouton de suppression, aucun
chemin non masqué en mode Discret, largeur de ligne jamais dépassée.

## Tests

`tests/` contient les tests non régressifs (aucune dépendance externe, `python -m unittest discover tests`).
Ils couvrent notamment : restauration de la quarantaine, rejet des profils invalides, indépendance
Mode Jeu / Mode Discret, réarmement des rendez-vous, verrous du débloat, zone de clic des cases,
couleur de la barre de volume en mode daltonien, emplacements vérifiables, compactage Configuration /
Rappels, ton Sérénité de « À propos », repliement de la section PLUS, suppression de la
taille « Très grande » (migrations comprises), et **l'intégralité des redirections** :
`tests/test_redirections.py` vérifie que chaque page `ms-settings:` citée dans le code est une page
qui existe, que les pages retirées bascullent sur leur équivalent selon le build de Windows, que les
clés de registre pointées par « Ouvrir l'emplacement » sont réellement présentes, que l'Explorateur
**sélectionne** un fichier au lieu de le lancer, et le désactivement du bouton quand il n'y a rien
à ouvrir. L'outil `verif_pages_windows.py` est testé lui aussi (couverture de la doc, détection
des adresses non documentées, détection Windows 10 / 11 par le build).

Côté moteur de place, `tests/test_plus_gros.py` vérifie le classement, la récursivité sans
double comptage, les fichiers et dossiers système ignorés, les liens et jonctions jamais suivis,
l'annulation en cours de route, les accès refusés avalés sans crash — et que le scan reste
**strictement en lecture seule** (les appels de suppression sont bloqués et surveillés pendant le
test). `tests/test_typographie.py` balaye tout le code livré et refuse la moindre apostrophe
typographique. `tests/test_rapidite.py` vérifie le cache matériel (durée de vie, cache abîmé,
une seule lecture pour plusieurs demandeurs) et les temps de fond. `tests/test_vocabulaire_etats.py`
verrouille le vocabulaire commun des états (« ✔ Appliqué » réservé à Calmer Windows, « ✔ Actif » /
« ✕ Désactivé » sur Démarrage et Services) et le fait que chaque état porte un symbole, pas
seulement une couleur.

Côté « ce PC n'est pas le mien », trois fichiers verrouillent le comportement sur machine
réelle : `tests/test_nuage.py` (les fichiers OneDrive ne sont ni hachés, ni comptés, ni déplacés),
`tests/test_langues_windows.py` (dossier renomme ou redirecte = trouve quand meme, code de retour
de `sc.exe` plutot que sa phrase traduite, GUID de plan d'alimentation memorise) et
`tests/test_refus_windows.py` (un blocage d'entreprise n'est jamais presente comme un manque de
droits). `tests/test_instance.py` vérifie qu'une seule fenêtre peut s'ouvrir et que la
sensibilisation au DPI est declarée avant la fenêtre. `tests/test_icone.py` vérifie le logo :
le `.ico` est valide et complet (16 à 48 px, canal alpha), il se colle sur la fenêtre et
**sur les fenêtres secondaires**, et il survivra au tri des fichiers de chantier.
`tests/test_don.py` verrouille le canal de don : un seul prestataire, un seul emplacement,
aucun mot d'argent dans les rappels, aucun vocabulaire de palier payant.
`tests/test_prefs_persistance.py` vérifie que les réglages de la page Configuration (mode live,
notifications, Ne pas déranger, son) survivent vraiment à un redémarrage.
`tests/test_premier_lancement.py` vérifie que tout part désactivé et que les choix de la fenêtre
« Bienvenue » sont écrits dans la config sitôt validés (« C'est parti »).
`tests/test_relance_admin.py` vérifie la relance « en administrateur » : vrai interpréteur
(jamais l'alias du Store), verbe `runas`, chemins absolus, marqueur d'attente et mutex rendu
par le parent.
`tests/test_demarrage_surete.py` refuse qu'un antivirus, un VPN ou un composant de Windows
soit proposé comme « sans risque » au démarrage.
`tests/test_corbeille.py` vérifie la somme de la Corbeille lecteur par lecteur (lecteur en
échec ignoré, plus jamais l'appel global qui comptait faux). `tests/test_demarrage_compte.py`
verrouille le compte « N trouvés, dont M actifs » (octets impairs = désactivés, exe disparu =
introuvable, doublons UWP fusionnés). `tests/test_updater.py` tient le bouton « Mises à jour » :
URLs du dépôt uniquement, .sha256 obligatoire, fichier abîmé supprimé, annulation sans résidu,
et **zéro appel réseau sans clic**. `tests/test_langue.py` vérifie la mécanique FR/EN
(repli français, pas de clé brute, sélecteur qui bascule tout).

**Total : 433 tests.**

## Soutenir TidyDeck

Le logiciel reste gratuit et le restera. Un seul canal de don existe,
`https://ko-fi.com/tidydeck`, et il n'apparaît qu'à un seul endroit : la page
**« À propos »**, sous la phrase *« Aucun don n'est requis, aucun n'est rappelé, aucun ne
débloque quoi que ce soit »*.

Pas de popup, pas de rappel sur l'Accueil, pas de bandeau dans la barre latérale, pas de
palier « premium », pas de fonction verrouillée derrière un paiement : le public visé est
TDAH, et insister casserait ce que le logiciel est venu faire. Ces règles sont écrites dans
`DISTRIBUTION.md` (§3) et tenues par `tests/test_don.py`.

## Licence

TidyDeck est publié sous **GNU General Public License v3.0**. Le fichier `LICENSE` à la
racine est le texte officiel intégral de la GPLv3, récupéré tel quel depuis `gnu.org` :
il n'a été ni réécrit, ni raccourci, ni adapté.

```
TidyDeck — Le ménage de ton PC, tout en douceur
Copyright (C) 2026 Florius

Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le modifier
selon les conditions de la GNU General Public License telle que publiée par la
Free Software Foundation, dans sa version 3 ou (à votre choix) toute version
ultérieure.

Ce programme est distribué dans l'espoir qu'il sera utile, mais SANS AUCUNE
GARANTIE, dans les limites permises par la loi. Voir la GNU General Public
License pour plus de détails.
```

En clair : tu peux lire le code, le modifier et le redistribuer, à condition de
redistribuer la licence et le code source sous les mêmes conditions.

**Code tiers embarqué.** `vendor/qrcode` (le QR de profil) est sous **BSD 3-Clause**
— *Copyright (c) 2011, Lincoln Loop*, lui-même dérivé de *pyqrnative*
(© 2009 Kazuhiko Arase, MIT). Son avis de droits d'origine est conservé intact dans
`vendor/qrcode/LICENSE`, comme cette licence l'exige quand on redistribue la
bibliothèque.

