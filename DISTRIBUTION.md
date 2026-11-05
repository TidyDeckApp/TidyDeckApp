# Distribution — TidyDeck

## 1. Livrables et intégrité

| | Source | Exécutable Windows |
|---|---|---|
| Fichier | `TidyDeck-0.6.1.zip` | `TidyDeck-0.6.1-win64.zip` |
| Contenu | dossier unique `TidyDeck/` (source Python, aucun binaire, aucun `__pycache__`) | `TidyDeck/TidyDeck.exe` + `TidyDeck/_internal/` (Python 3.12 + Tcl/Tk embarqués) |
| Prérequis | Python **3.10+** sur Windows · **aucune dépendance pip** | **Rien à installer** · Windows 10 ou 11 64 bits · pas de droit administrateur au démarrage |
| Lancement | `python main.py` | double-clic sur `TidyDeck.exe` |
| Empreinte | **`TidyDeck-0.6.1.zip.sha256`** (à côté du zip) | **`TidyDeck-0.6.1-win64.zip.sha256`** |

L'empreinte **ne peut pas** être écrite dans un fichier contenu dans l'archive qu'elle
authentifie (elle changerait en l'écrivant). Elle est publiée **à côté** de chaque zip,
jamais à l'intérieur, et le nom du livrable porte la version (`0.6.1`) et non un petit
nom de dossier.

Vérifier après téléchargement :

```bat
certutil -hashfile TidyDeck-0.6.1.zip SHA256
certutil -hashfile TidyDeck-0.6.1-win64.zip SHA256
```

Publier l'empreinte **avec** le téléchargement. **Un fichier dont le SHA-256 ne
correspond pas ne doit pas être exécuté.**

Les tailles ne sont pas recopiées ici : elles bougent à chaque build, la valeur exacte
est celle du fichier livré avec son empreinte.

## 2. Licence du projet et licences tierces

- **Projet : GNU General Public License v3.0.** Le fichier `LICENSE` à la racine est le
  texte officiel intégral récupéré depuis `gnu.org` (35 149 octets, SHA-256
  `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986`), copié tel quel,
  sans réécriture ni coupe. Auteur : **Florius**.
- Conséquence assumée : la GPLv3 **autorise** la revente et la modification, à condition
  de redonner le code source sous les mêmes conditions. L'ancienne idée d'une « licence
  personnalisée interdisant la revente » est donc écartée : ce choix est fait, il ne faut
  pas le contredire ailleurs dans le texte.
- **Code tiers embarqué** : `vendor/qrcode` (QR de profil), **BSD 3-Clause** —
  *Copyright (c) 2011, Lincoln Loop*, lui-même dérivé de *pyqrnative*
  (© 2009 Kazuhiko Arase, MIT). L'avis de droits d'origine est conservé intact dans
  `vendor/qrcode/LICENSE` (2 143 octets, SHA-256
  `40dfb903c94ee3f789500131311186548ecba5cefd3557623d7700e2522ab994`) : c'est une
  obligation de cette licence quand on redistribue la bibliothèque. Ne pas le supprimer,
  même en cas de ménage dans les fichiers.

## 3. Système de don — UN SEUL, pas trois

**Règle : un unique canal de don, affiché à un seul endroit.**

- Emplacement : page **« À propos »**, une seule ligne, un seul bouton.
- Interdits explicites : popup au démarrage, rappel sur l'Accueil, bandeau dans la
  sidebar, imploration à la fin d'un nettoyage, plusieurs prestataires (PayPal **ou**
  Ko-fi **ou** Buy Me a Coffee — pas les trois), paliers de contribution, « débloquer
  la version premium ».
- **Canal retenu : Ko-fi** (`DONATION_URL = "https://ko-fi.com/tidydeck"` dans
  `Shared/Utils/common.py`). Un seul prestataire, un seul bouton, sur la page
  « À propos », avec la phrase « Aucun don n'est requis, aucun n'est rappelé, aucun ne
  débloque quoi que ce soit » affichée juste au-dessus.

Justification : le public visé est TDAH. Un canal unique et discret reste compatible avec
l'usage ; un harcèlement de don casse la promesse du logiciel.

> Ces règles sont tenues par `tests/test_don.py` : le lien ne doit apparaître que dans
> `common.py` (la définition) et `UI/Pages/about_page.py` (l'affichage), les rappels
> bien-être ne doivent contenir aucun mot d'argent, et aucun vocabulaire de palier payant
> (« premium », « débloquer la version ») n'est admis.

## 4. Vérification du nom

### Ce qui a été vérifié (31 octobre 2026)

- **Un dépôt homonyme existe bel et bien** : `github.com/wenhuiwu/tidydeck`, décrit comme
  « *Electron desktop cleaner for AI skills, Maven caches, and node_modules* »
  (TypeScript, licence MIT, créé le 12 août 2026, 0 étoile, aucune release). Vérifié via
  l'API GitHub le 31/10/2026. **L'ancienne mention « aucun logiciel nommé TidyDeck trouvé
  était donc fausse** — elle est corrigée ici.
  Distance avec notre produit : même nom, autre public (caches de développement, pile
  Electron), aucune notoriété, aucune marque identifiée. Le risque de confusion reste
  faible mais il n'est plus nul : ce sont deux logiciels de nettoyage, donc potentiellement
  les mêmes classes 9 et 42.
- **Domaines (RDAP, protocoles publics des registres, 31/10/2026)** :

  | Domaine | État RDAP | Détail |
  |---|---|---|
  | `tidydeck.com` | **pris** | GoDaddy, enregistré le 20/01/2009, expire le 20/01/2027, verrouillé (ni suppression, ni transfert, ni modification) |
  | `tidydeck.fr` | **libre** | 404 dans le registre |
  | `tidydeck.io` | **libre** | 404 dans le registre |
  | `tidydeck.app` | **libre** | 404 dans le registre |
  | **`tidydeckapp.app`** | **libre** | 404 dans le registre — **domaine choisi** |

  Observation DNS annexe : `tidydeck.net` et `tidydeck.org` résolvent vers les mêmes
  hôtes Wix que `tidydeck.com` (185.230.63.107 / .171 / .186) ; leur état au registre
  n'a pas été interrogé.
- **Registres de marques : INACCESSIBLES depuis cet environnement, le 31/10/2026.**
  Les tentatives ont été faites et ont échoué pour des raisons techniques, pas par oubli :

  | Registre | Résultat de la tentative |
  |---|---|
  | `data.inpi.fr` (API marques) | **403** — protection « Just a moment… » (Cloudflare), aucune donnée |
  | `data.inpi.fr` (API paquets) | **403** — même protection |
  | `tmdn.org/tmview/api/...` (GET et POST) | 200 mais **page applicative JavaScript**, pas les données de recherche |
  | `euipo.europa.eu/eSearch/api/...` | 200 mais page Apache vide (« It works! ») |
  | `tmsearch.uspto.gov/api/...` | **404** (endpoint inexistant) |
  | moteur de recherche web | indisponible ce jour-là (« fetch failed ») |

  **Conclusion honnête : aucune recherche INPI ni TMview n'a pu être menée à bien. Ces
  vérifications restent à faire à la main, par quelqu'un qui a un navigateur.**

### À faire avant toute publication (obligatoire)

| Registre | Où | Chercher |
|---|---|---|
| France | `data.inpi.fr` (navigateur) | « TidyDeck », classes **9** (logiciels) et **42** (services logiciels) |
| Europe | `euipo.europa.eu` · **TMview** `tmdn.org/tmview` | idem, classes 9 et 42 |
| USA | `tmsearch.uspto.gov` | « TidyDeck » / « TIDY DECK », classes 9 et 42 |
| Microsoft Store | Partner Center → ajout d'app | disponibilité du nom d'affichage |
| Domaine | registrar | réserver `tidydeckapp.app` tant qu'il est libre (l'état ci-dessus date, il ne vaut pas réservation) |

### Risque analysé

Le titulaire de `tidydeck.com` opère dans le **nettoyage de surfaces extérieures**
(classe 37), pas dans les logiciels : en droit français comme en droit de l'UE, le
conflit suppose un **risque de confusion dans l'esprit du public** pour des produits ou
services identiques ou similaires, et sur des classes distinctes sans notoriété établie le
risque direct est **faible**.

Le dépôt `wenhuiwu/tidydeck`, lui, est **dans la même classe d'usage** (nettoyeur de
fichiers pour développeurs). Son ancienneté (août 2026), sa licence MIT et son absence
totale de notoriété le rendent peu dangereux en pratique, mais c'est le point à regarder
en premier dans la recherche de marques.

**Recommandation** : avant de diffuser publiquement, faire la recherche INPI/TMview dans
un navigateur ; si les classes 9 et 42 sont libres, déposer la marque verbale
« TidyDeck » en 9 et 42, et réserver `tidydeckapp.app`. Ne pas se présenter comme
« officiel » sans cette étape.

## 5. Conditions d'utilisation

À publier telles quelles (ou adaptées) avec le livrable. Elles sont identiques, sur le
fond, à ce que montrent les pages « À propos » (mode normal et mode Sérénité).

> **TidyDeck — conditions d'utilisation**
>
> **Ce que fait TidyDeck.** TidyDeck analyse et range ta machine Windows : fichiers
> temporaires, caches, programmes au démarrage, services non essentiels, réglages
> utilisateur, applications préinstallées. Il propose des rappels bien-être et masque à
> l'écran tes informations personnelles en Mode Discret.
>
> **Ce que TidyDeck ne fait pas.** Pas de nettoyage du registre. Pas de « boost » de
> performances. Pas de télémétrie. Aucune donnée n'est collectée ni envoyée : le seul accès
> réseau est le bouton « Mises à jour », et il ne part que si tu cliques dessus.
>
> **Réversibilité.** Les fichiers nettoyés sont déplacés en quarantaine et annulables
> pendant la durée choisie (7 jours par défaut), depuis l'onglet Journaux.
> **Exception unique et assumée : vider la Corbeille est immédiat et définitif.**
> TidyDeck te le signale explicitement chaque fois que la Corbeille fait partie de la
> sélection.
>
> **Absence de garantie.** Dans les limites permises par la loi, le logiciel est fourni
> « en l'état », sans garantie d'aucune sorte, y compris implicite de qualité marchande ou
> d'adéquation à un usage particulier. Une opération sur un système d'exploitation peut
> avoir des effets inattendus. Un point de restauration Windows est proposé avant les
> réglages : **utilise-le**. Tu restes responsable de ta machine, de tes sauvegardes et
> de tes décisions.
>
> **Privilèges administrateur.** Certaines fonctions (point de restauration, services
> Windows, réglages système) demandent une élévation. TidyDeck la demande explicitement,
> une fois, et Windows te redemande ton accord. **Rien n'est élevé sans ton accord.**
>
> **Applis préinstallées.** TidyDeck liste, explique et propose. **Rien n'est désinstallé
> sans que tu valides la liste exacte** des programmes concernés ; les composants
> essentiels de Windows ne sont jamais proposés, et un programme retiré reste
> réinstallable chez son éditeur ou dans le Microsoft Store.
>
> **Vie privée.** Aucun compte, aucune inscription, aucune collecte, aucune télémétrie.
> Aucune donnée ne quitte ta machine : le seul accès réseau est le bouton
> « Mises à jour », et il ne part que si tu cliques dessus.
>
> **Rappels.** Les rappels bien-être et le minuteur de rendez-vous ne fonctionnent que si
> TidyDeck reste ouvert (réduit dans la barre des tâches). TidyDeck ne peut pas t'avertir
> s'il est fermé, et ne le promet pas.
>
> **Mode Discret.** Le Mode Discret masque à l'écran ce que **TidyDeck** affiche. Il ne
> masque pas les notifications des autres applications, ce que Windows transmet à
> Microsoft, ni le contenu des autres logiciels. Ne compte pas dessus pour autre chose.
>
> **Licence.** GPL-3.0 (GNU General Public License v3), voir le fichier `LICENSE` fourni
> avec le livrable : tu peux lire, modifier et redistribuer ce code aux mêmes conditions,
> sans aucune garantie, dans les limites permises par la loi.
>
> **Don.** Un unique lien de don, s'il existe, figure sur la page « À propos ». Aucun don
> n'est requis, aucun n'est rappelé, aucun ne débloque quoi que ce soit.

## 6. Construire l'exécutable

Le `.exe` est construit **hors du dossier livré**, avec un Python plus ancien que celui
utilisé au quotidien : Python 3.15 est trop récent pour que l'outillage (PyInstaller et
 ses hooks) le suive, et un build cassé sur 3.15 ne dirait pas si le défaut vient du code
ou de l'outil.

La recette de build est **livrée avec le code** : `packaging\TidyDeck.spec` contient le
`.ico`, les `datas`, `console=False`, tout. Une seule commande, depuis la racine :

```bat
py -3.12 -m venv build_env
build_env\Scripts\python -m pip install --upgrade pip pyinstaller
build_env\Scripts\pyinstaller --noconfirm --clean ^
  "TidyDeck_v2\TidyDeck\packaging\TidyDeck.spec" --distpath dist --workpath work
```

Résultat : `dist\TidyDeck\TidyDeck.exe` + `dist\TidyDeck\_internal\` (dont
`_internal\vendor\qrcode`, licence comprise). La spec pose `console=False` : pas de
console noire derrière l'interface. Le dossier `dist\TidyDeck` est ensuite compressé en
`TidyDeck-0.6.1-win64.zip`.

**UPX est désactivé (`upx=False`, dans `EXE` comme dans `COLLECT`).** UPX est un emballeur :
il recolle les DLL et l'exe pour gagner quelques méga-octets, et c'est très exactement le
comportement d'un packer de malware. Un utilitaire de nettoyage qui lit le registre, vide
des caches et relance des services ressemble déjà à un suspect ; compressé par UPX, il est
signalé d'office par une bonne partie des moteurs, sans même qu'on regarde ce qu'il fait.
On accepte un livrable plus gros en échange d'une analyse propre. `upx_exclude=[]` reste
vide : il n'y a rien à exclure puisque rien n'est compressé.

**Le logo.** `assets\tidydeck.ico` (16/24/32/48/64/128/256 px, PNG + alpha) sert deux fois
dans la spec : l'option `icon=` lui donne l'icône de l'`.exe` (explorateur, barre des
tâches, Alt+Tab) et `datas` (`assets` → `assets`) l'embarque dans `_internal\assets\`, d'où
`chemin_asset()` le relit pour la barre de titre (`Shared/Utils/common.py` →
`appliquer_icone()`). Sans la seconde moitié, l'application tourne avec la plume Tk par
défaut ; le test `tests/test_icone.py` vérifie les deux côtés. `assets\tidydeck-logo.svg`
est la source du logo (couleurs `#1B2B4B` fond, `#F4F7FC` carte, `#C8610A` coche,
`#FFD27A` étincelles) : il est livré avec le code, mais l'application ne lit que l'`.ico` —
Tk ne sait pas lire un SVG. Pour régénérer l'`.ico` depuis le SVG : Inkscape
`inkscape tidydeck-logo.svg --export-type=ico --export-filename=tidydeck.ico`.

Après un rebuild, Windows peut afficher **l'ancienne icône** : le cache d'icônes est
obstiné. Renommer l'`.exe` (ou redémarrer l'explorateur) le force à relire le fichier.

**Installeur (optionnel).** TidyDeck reste un dossier portable : rien n'oblige à installer.
Pour ceux qui veulent un `.exe` d'installation, `packaging\tidydeck.iss` (Inno Setup 6) est
livré : `ISCC.exe packaging\tidydeck.iss` après le build. Il installe en `%LOCALAPPDATA%`
sans droits administrateur, reprend la même icône (`SetupIconFile`) et retire l'entrée
« démarrer avec Windows » du registre au désinstallateur, pour ne rien laisser derrière lui.

À savoir sur le `.exe` : `sys.executable` vaut `TidyDeck.exe`, donc **aucun code ne doit
relancer `sys.executable -c …`** — cela ouvrirait une fenêtre TidyDeck par processus fils.
Le chargeur de test de charge processeur (`Core/SystemInfo/sensors.py` → `_burn`) lance
donc un `powershell -NoProfile -Command` en boucle courte, jamais l'interpréteur du
programme. Un test le vérifie (`tests/test_burn_capteur.py`).

## 7. Checklist de publication

- [ ] Build régénéré **nommé avec la version** : `TidyDeck-0.6.1.zip` + `.sha256`
      (et `TidyDeck-0.6.1-win64.zip` + `.sha256` pour l'exécutable)
- [ ] **Ré-analyse VirusTotal après chaque rebuild** : l'ancien signal venait de la
      compilation de C# à la volée, supprimée (voir §6). La ré-analyse demande une clé API
      VirusTotal, donc une action humaine.
- [ ] **Build parti de `dist\` et `work\` supprimés** : PyInstaller écrase ce qu'il
      reconstruit mais ne nettoie pas le reste. Un `.dll` ou un `.pyc` d'un build antérieur
      peut survivre dans `_internal\` et se retrouver livré sans qu'on le voie.
- [ ] **UPX vérifié désactivé** (`upx=False` deux fois dans `packaging/TidyDeck.spec`) : un
      exe emballé par UPX est sur-analysé par les antivirus, ce qui ruine le signal de
      l'analyse précédente. Contrôlé par `tests/test_icone.py`.
- [ ] **Résidus d'applications (🧹, mode avancé seulement)** : Phase 0 en **lecture seule
      stricte** — aucune écriture nulle part, vérifié par `tests/test_residus.py`. La Phase 1
      (quarantaine des résidus) ne doit être codée qu'**après** un test manuel sur au moins
      5 machines différentes sans faux positif à confiance « Élevée » (cahier des charges
      résidus, §2) ; la collecte des retours se fait au cas par cas pendant ce test.
- [ ] Fichiers « dans le nuage » (OneDrive…) : jamais lus, jamais hachés, jamais déplacés —
      vérifié par `tests/test_nuage.py`. À rappeler dans la page *Fichiers & Résidus* si
      l'utilisateur voit un compteur « non comptés » incompréhensible.
- [ ] Il n'y a **pas d'installeur** : TidyDeck se copie où l'utilisateur le veut. L'entrée
      « démarrer avec Windows » qui pointait vers un dossier supprimé est donc réparée au
      premier lancement (`Services/Reminders/autostart.py`) et le retrait est journalisé.
- [ ] Ouverture sur un écran **à 125 % ou 150 %** : la sensibilisation au DPI est déclarée
      avant la création de la fenêtre, mais le rendu final sur ces écrans ne peut pas être
      vérifié depuis ce poste (dalles 96 ppp seulement).
- [ ] Empreintes publiées avec les fichiers, et vérifiées avec `certutil` après
      téléchargement
- [ ] Recherche INPI / TMview / EUIPO / USPTO faite **à la main** (classes 9 et 42) —
      impossible depuis cet environnement, voir §4
- [ ] `tidydeckapp.app` réservé
- [ ] Nom vérifié dans le Microsoft Store Partner Center
- [x] Canal de don unique choisi et écrit uniquement dans `DONATION_URL` (Ko-fi,
      verrouillé par `tests/test_don.py`)
      (vide aujourd'hui = aucun affichage)
- [ ] `LICENSE` (GPL-3.0) présent à la racine, `vendor/qrcode/LICENSE` (BSD-3) conservé
- [ ] `README.md` à jour (installation, vérification, désinstallation, licence)
- [ ] Suite de tests verte : `python -m unittest discover -s tests -t .`
- [ ] `.exe` testé lancé depuis `dist\` (ouverture, pages, aucune fenêtre en double)
