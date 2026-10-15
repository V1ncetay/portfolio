# Sorcery / Sorcery+ (Virgin Games, 1984-85) - Spécification de clone

> Légende de fiabilité : **[V]** = vérifié par au moins une source consultée ;
> **[C]** = sources contradictoires ; **[I]** = inféré / mémoire / proposition de conception (non vérifié).
>
> AVERTISSEMENT DE RECHERCHE : lors de la recherche, WebFetch et curl n'ont pas pu joindre
> les sites (échec DNS / tunnel proxy 403). Seuls les extraits de résultats WebSearch ont été
> exploitables (pas de lecture des pages complètes : Wikipedia, CPCWiki, EveryGameGoing,
> CPCRulez, MobyGames, Retro Arcadia). Aucune carte ni solution complète n'a pu être consultée.
> La carte des salles, la table objet/porte/captif/monstre sont donc majoritairement **[I]** :
> ce sont des propositions de conception, à recouper avec une partie réelle (émulateur
> + longplay YouTube « [Amstrad CPC] Sorcery - Longplay », CPCRulez `GamesTest/sorcery_plus.htm`,
> articles Amstrad Action n°1 et Computer Gamer n°8).

## 1. Sources consultées (via extraits de recherche)
- CPCWiki Zone reviews (titres 699, 798 = Sorcery ; 799 = Sorcery Plus), Amstrad Computer User (EGG 51416),
  Amstrad Action (EGG 25702 / 25711), Computer Gamer n°8 (EGG 38849), Commodore User, CVG n°51.
- MobyGames, GamesDatabase.org, Retro Replay, UVList, VideoGameGeek, Wikidata (le jeu a des pages WP fr/it/gl, pas en).
- Blogs : retroarcadia.blog (« Discovering Sorcery on Amstrad CPC »), videogames.bearblog.dev (« All Aboard The Flying Train »).

## 2. Historique et versions
- Original 1984 ZX Spectrum / C64, Virgin Games ; attribué à Martin Wheeler (schoolboy) selon un blog **[C]**.
  La conversion CPC (1985) est créditée à The Gang of Five **[V]**. Sorties CPC : cassette (Virgin) et
  disquette (Amsoft/Virgin « Sorcery+ ») **[V]**.
- Contradiction sur la taille : MobyGames/GamesDatabase décrivent la base 8 bits à **17 écrans, 3 sorciers captifs** ;
  les critiques CPC parlent de **8 sorciers captifs et ~40 écrans** **[C]**. Hypothèse la plus cohérente : les
  chiffres « 17 / 3 » concernent une description de l'original Spectrum/C64, les « 40 / 8 » la version CPC.
- Sorcery+ (disque CPC) **[V]** : Amstrad Action n°1 : écrans passés de 40 à **75**, « nouvelles sections au décor
  inédit et sorciers repositionnés » ; Computer Gamer n°8 : Chapitre 1 = 47 écrans, Chapitre 2 = **+28 écrans**
  (47+28 = 75, cohérent). Le Chapitre 2 est celui où l'on **doit vaincre le Nécromancien** **[V]**.
  CVG n°51 : en partie 2 on collecte des **cœurs** au lieu de libérer des sorciers **[V]** (nature exacte [I]).

## 3. Histoire et objectif
- Le Nécromancien (Necromancer) a enlevé/emprisonné des sorciers ; le joueur incarne un sorcier volant qui doit
  les libérer **dans une limite de temps** **[V]**. Nombre de captifs : 8 (CPC) **[C]**.
- Le Nécromancien est l'ennemi final ; sa mort se fait avec **un objet précis parmi trois candidats** trouvés en
  chemin ; lieu de la confrontation : **Stonehenge** (cercle de pierres) **[V pour l'original]**.
  Sorcery+ : une critique indique qu'il faut **trois exemplaires** d'un objet pour tuer le Nécromancien alors
  qu'il n'en existe que deux ; le troisième se « fabrique » en résolvant une énigme **[V, objet exact non connu]**.
  Les objets du monde du joueur transportés vers le monde du Nécromancien y sont réutilisés sous une autre forme
  (indice d'énigme) **[V]**.
- Condition de victoire (proposition) **[I]** : Ch.1 = libérer tous les sorciers avant la fin du temps ;
  Ch.2 = apporter l'objet final et tuer le Nécromancien.

## 4. Ressources : énergie, temps, vies
- **Énergie** : réserve limitée, drainée par le contact avec les monstres **[V]** ; certains objets/lieux la
  restaurent, d'autres la drainent (chaudrons) **[V]**. Se poser sur un **chaudron (cauldron)** reconstitue
  l'énergie mais n'agit pas sur le temps **[V]** (une critique parle aussi de chaudrons qui « pompent » l'énergie : [C],
  à résoudre par jeu : proposition = chaudron plein = recharge, vide/maudit = drain).
- **Temps** : compte à rebours global, non restauré par le chaudron **[V]**. Valeur initiale non connue : proposer
  ~ 30 min réelles de jeu **[I]** (réglable).
- **Vies** : l'original n'a pas de vies multiples classiques : énergie à 0 = fin de partie **[I]**
  (à confirmer). Proposition : une seule vie, énergie divisée en ~10 segments.
- Dégâts : contact monstre = perte continue/par touche d'une quantité fixe (ex. 1 segment/tick de 0,5 s) **[I]**.
- Perte du temps = fin de partie « le Nécromancien l'emporte » **[I]**.

## 5. Contrôles et physique (tous [I] sauf mention)
- Le sorcier **vole** en permanence ; l'original est contrôlé par joystick/clavier : 4 directions + un bouton.
- Gravité : sans entrée, le sorcier **descend lentement** (« float down ») ; maintien vers le haut = montée
  (vitesse ascendante > vitesse de chute). Valeurs proposées (écran 160x200) : montée 2 px/frame, chute 1 px/frame,
  horizontal 2 px/frame (vitesse constante, inertie nulle), 50 Hz mais logique à 25 Hz.
- Une touche **Action (feu)** : ramasser l'objet survolé si les mains sont vides ; si un objet est porté,
  le **lâcher/échanger** **[V : un seul objet porté à la fois, échange à chaque nouvel objet]**.
- Se poser (sol / chaudron) : descente jusqu'au sol, position immobile ; perd de l'énergie au contact d'eau [I].
- Collision décor : murs/sols solides ; plafond bloque ; sorties d'écran par bord (flip-screen) **[V]** ;
  portes locales exigeant un objet **[V]** ; trappes (« trapdoors ») ouvertes par des clés, sinon écran
  non quittable **[V]**.
- Passages cachés sur de nombreux écrans **[V]** (« various hidden passages in each ») : à implémenter comme
  murs traversables/sorties non évidentes **[I]**.

## 6. Écran, HUD, graphismes
- Mode CPC 0 : **160x200 px, 16 couleurs** de la palette 27 couleurs matérielle **[V pour le mode, usage [I]]**.
  Pixels très larges (2:1). Clone : canvas logique 160x200 mis à l'échelle, pixels rectangulaires 2x1 (ou 320x200 avec
  pixels doublés) + palette fixe de 16 entrées inspirée du CPC (noir, bleu, rouge, magenta, vert, cyan, jaune, blanc,
  et variantes). Graphismes procéduraux originaux : sprites générés par code, aucun asset ripé.
- Zone de jeu : écran principal (~160x150) en haut ; bandeau de statut en bas **[I]**.
- HUD **[I]** (l'original affiche une barre d'énergie, l'objet porté et le temps - sources partielles) :
  - barre d'énergie (couleur dégradée vert -> rouge) ;
  - nom/icône de l'objet porté ;
  - indicateur de temps (sablier/barre) ;
  - compteur de sorciers libérés (x/8) ;
  - score éventuel (voir §10).
- Rendu salle : sol/ciel/arrière-plan par thème (forêt, château, etc.), tuiles 8x8 procédurales.

## 7. Structure du monde
Le monde est composé de **~40 écrans (Ch.1 de Sorcery CPC) -> 47 dans Sorcery+ ; Ch.2 +28** **[V/C]**.
Navigation par flip-screen (sortie par un bord = entrée du bord opposé de l'écran voisin) **[V]**.
Lieux nommés dans l'original **[V partiel]** : plaines/landes (wastelands), rivière, bois (Woods), Stonehenge
(finale). Les autres noms (Château, Palais, etc., cités par la commande) sont **[I]** et seront utilisés comme
thèmes ; ne pas les présenter comme officiels.

### 7.1 Proposition de zones (Ch.1, 47 écrans) [I]
| Zone | Écrans | Thème |
|---|---|---|
| Home / Landes (départ) | 6 | Plaine, tour du sorcier de départ |
| Bois (Woods) | 8 | arbres, hiboux, passages cachés |
| Rivière | 5 | eau mortelle, ponts, poissons |
| Château (Chateau) | 10 | portes à clé, trappes, donjons où sont les captifs |
| Cimetière / Catacombes | 6 | fantômes, crânes |
| Palais (Palace) | 6 | gardes, grandes portes |
| Stonehenge | 6 | accès à l'objet décisif, lieu de la finale |

### 7.2 Carte d'ensemble (grille proposée, N en haut) [I]
```
        [Stonehenge 6]--[Palais 6]
              |             |
 [Bois 8]--[Landes 6]--[Château 10]--[Catacombes 6]
              |             |
         [Rivière 5]---(trappes/souterrain)
```
- Départ : Landes. Chaque zone est une sous-grille d'écrans ; connexion zone-à-zone par un seul écran pivot.
- Le Ch.2 (monde du Nécromancien, 28 écrans) s'atteint après avoir libéré tous les sorciers [I] ; il réutilise des
  objets du monde 1 sous d'autres formes **[V]**.
- Génération recommandée : décrire chaque écran en JSON (id, thème, tuiles, voisins N/S/E/O, portes, objets, monstres).

## 8. Objets, portes, captifs
Faits vérifiés **[V]** : un seul objet porté ; certains objets ouvrent des portes de salles verrouillées ; des clés
ouvrent des trappes ; certains tuent un ou plusieurs types de monstres ; certains rechargent l'énergie ;
chaque sorcier captif exige un **objet précis** pour être libéré (essais/erreurs) ; trois objets sont
candidats à l'arme finale (Ch.1) et il en faut trois exemplaires dans Sorcery+.

Table de conception **[I intégral : noms et affectations proposés]** :

| Objet | Où | Effet |
|---|---|---|
| Épée (Sword) | Landes | tue squelettes/crânes |
| Hache (Axe) | Bois | tue gobelins/araignées ; ouvre porte en bois |
| Croix (Cross) | Cimetière | tue fantômes ; (option arme finale) |
| Clé (Key) | Château | ouvre trappes |
| Clé dorée | Palais | ouvre la porte du Palais |
| Torche (Torch) | Catacombes | éclaire écrans sombres, tue chauves-souris |
| Potion / Cœur (Heart) | divers | +énergie |
| Sablier (Hourglass) | Rivière | option : +temps (non vérifié ; ne pas inclure par défaut) |
| Parchemin (Scroll) | Stonehenge | indice / sort final |
| Amulette, Bouclier, Coupe, Livre, Lanterne, Harpe | divers | libèrent un sorcier chacun (8 couples objet->captif) |
| Trois reliques (candidats finaux) | Landes/Bois/Stonehenge | une seule tue le Nécromancien ; 3 exemplaires requis en Ch.2 |

Règles de conception : 8 captifs = 8 objets distincts ; chaque objet utilisable dans une seule salle de libération ;
objets d'attaque réutilisables ; objets de porte consommés ou non (proposer : non consommés).

## 9. Ennemis
Vérifié **[V]** : « ghouls, ghoulies, crânes sans corps », monstres variés poursuivant le joueur, drain d'énergie au
contact ; certains objets tuent certaines espèces. Reste **[I]** :
| Type | Mouvement | Tuer avec |
|---|---|---|
| Crâne flottant | sinusoïde horizontale | Épée |
| Fantôme / Ghoul | poursuite lente | Croix |
| Chauve-souris | vol erratique rapide | Torche |
| Araignée | va-et-vient vertical | Hache |
| Poisson / serpent d'eau | saute hors de la rivière | Aucun (éviter) |
| Gardes (Palais) | patrouille horizontale | Épée |
| Nécromancien | boss, téléportations + projectiles | arme finale (x3 Ch.2) |
Les monstres réapparaissent à la re-entrée de l'écran [I]. Tué = disparaît jusqu'à re-entrée, score +.

## 10. Score, son, écrans de fin
- Score : l'original n'a probablement pas de score significatif ; Sorcery+ : cœurs collectés en partie 2 **[V/C]**.
  Proposition : +100/ennemi, +500/sorcier libéré, +5000/Nécromancien, + temps restant x10 **[I]**.
- Son : **musique d'intro** (mélodie sur le chip AY-3-8912 du CPC, 3 voix) et effets simples
  (ramassage, dégâts, libération) **[V : le jeu a de la musique d'intro, mélodie exacte inconnue]**.
  Clone : composer des motifs originaux courts (WebAudio, onde carrée), ne pas reprendre la mélodie.
- Game Over [I] : écran « Le Nécromancien triomphe » ; Victoire [I] : écran de félicitations avec sorciers libérés.

## 11. Différences Sorcery / Sorcery+
| | Sorcery (CPC) | Sorcery+ (disque) |
|---|---|---|
| Écrans | ~40 | 75 (47 + 28) |
| Contenu | libérer les sorciers | + Ch.2 : monde du Nécromancien, cœurs, boss |
| Support | cassette | disquette (Amsoft/Virgin) |
| Sorciers | repositionnés/nouveaux décors | |

## 12. Recommandation de périmètre pour le clone
1. **MVP** : Ch.1 seulement (~20-25 écrans écrits à la main, 8 captifs, 5 types de monstres, énergie, temps, objet unique).
2. **v2** : étendre à ~47 écrans ; chaudrons ; passages cachés ; trappes.
3. **v3** : Ch.2 (28 écrans) + boss Nécromancien + exigence de 3 reliques.
4. Avant de coder les tables §7-9, **valider contre un longplay réel** : toute la section est une proposition.
5. Architecture : données de salle en JSON, moteur à tuiles 160x200, boucle fixe 25 Hz, rendu canvas pixel-perfect.
