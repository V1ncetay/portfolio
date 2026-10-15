# Sorcery (CPC, disquette) : analyse binaire de l'image DSK

> Objet : apporter la **preuve binaire** des mécaniques que `DESIGN.md` décrit à partir de sources
> externes ([V]) ou par inférence ([I]). Tout ce qui suit a été lu dans le code Z80 et les tables
> du jeu ; chaque affirmation porte une adresse. Les déductions non certaines sont marquées
> **(hypothèse, confiance haute / moyenne / basse)**.
>
> Aucun binaire, aucun graphisme et aucune table complète du jeu ne sont versionnés : les
> fichiers extraits restent hors du dépôt (scratchpad). Seuls de courts extraits (quelques
> octets ou instructions) sont cités comme preuves.

## 1. Pièce analysée

| | |
|---|---|
| Fichier | `Sorcery (1985)(Virgin Games)[t +4].dsk` (194 816 octets) |
| SHA-256 | `d0a4df5c7e553014505cd803057d6c2282ba4543ba0bd309e8045860afbb45d4` |
| Format | en-tête `MV - CPCEMU Disk-File` (DSK standard, pas EDSK), 40 pistes, 1 face, Track-Info de &1300 octets |
| Secteurs | 9 par piste, ID &C1..&C9, N=2 (512 o), aucun ST1/ST2, aucun ID ou taille hors format |
| Protection | **aucune** au niveau disque (tous les secteurs sont réguliers ; c'est un format DATA AMSDOS ordinaire) |
| Version | `SORCERY ... COPYRIGHT 1985 VIRGIN GAMES LTD. DISC CONVERSION BY TREVOR. PROGRAMMED BY THE GANG OF SIX.` (texte du titre, &206F) : c'est **Sorcery**, pas Sorcery+ (40 salles, 8 sorciers, pas de chapitre 2 ni de Nécromancien) |
| Crack | « [t +4] » : chargeur BASIC modifié (questions en **espagnol**) offrant 4 options de triche |

## 2. Catalogue AMSDOS (piste 0, secteurs C1-C4)

Sortie de `tools/dsk_extract.py` (blocs de 1 Ko, 180 blocs dont 2 de répertoire, 41 utilisés,
aucun bloc libre contenant des données : pas de fichier effacé ni de données cachées) :

| Fichier | Extents | Blocs | Type AMSDOS | Chargement | Exécution | Longueur | Checksum en-tête |
|---|---|---|---|---|---|---|---|
| `SORCERY .BAS` | 0 | &2A | BASIC (0) | &0170 | - | 534 (&0216) | &03CC OK |
| `SORCERY1.BIN` | 0, 1 | &02-&20 | binaire (2) | &27C6 | &0000 | 31 550 (&7B3E) | &0C43 OK |
| `SORCERY2.BIN` | 0 | &21-&29 | binaire (2) | &05CF | &05CF | 8 695 (&21F7) | &0D71 OK |

SHA-256 des corps (sans en-tête) : SORCERY1 `5d581b8f…f20f`, SORCERY2 `5f1e14c3…e0d9`,
BAS `e19dae44…dbb2`. SORCERY2 se termine exactement là où SORCERY1 commence (&05CF + &21F7 = &27C6).

## 3. Chaîne de chargement

1. `RUN"SORCERY"` : le BASIC détokenisé (`tools/basic_detok.py`) fait, dans l'ordre :
   - `MODE 1`, `MEMORY &27C5 : LOAD "SORCERY1.BIN",&27C6` ;
   - `OPENOUT "ms" : MEMORY &5CE : LOAD "SORCERY2.BIN",&5CF` (le `OPENOUT` sert à faire allouer
     le tampon AMSDOS avant d'abaisser HIMEM, astuce classique pour éviter « Memory full »
     **(hypothèse, confiance moyenne)**) ;
   - 4 questions de triche (§4), puis `CALL &5CF`.
2. **&05CF** : `ld bc,&7B3A / ld de,&AAFE / ld hl,&A2FF / lddr` : SORCERY1 est **décalé de &7FF
   octets vers le haut** (&27C6-&A2FF → &2FC5-&AAFE). C'est une simple relocalisation, **il n'y a
   pas de décompacteur** ni de chiffrement. La zone &27C6-&2FC4 garde un reste de l'ancienne
   copie (seuls ses 5 derniers octets, &2FC0-&2FC4, servent : début de l'image du sablier).
3. `di`, `ld sp,&C000`, gate array `&7F8C` (mode 0, ROM coupées), coupure du PSG (&1BDD),
   `ld iy,&AB28` (bloc d'état), CRTC R12/R13 = &30/&00 (écran en &C000), installation d'un
   `jp &1D93` en &0038 (IM 1), `ei`, puis écran titre.

## 4. Le trainer « +4 » (POKE avant `CALL &5CF`)

Toutes les POKE tombent dans SORCERY2 (code non relocalisé) ; elles désignent donc directement
les routines de jeu. C'est le meilleur point d'entrée pour retrouver énergie et dangers.

| Question (espagnol) | POKE | Instruction d'origine | Effet |
|---|---|---|---|
| « Inmune a los bichos » | &1ADA,0 / &1ADB,0 | `1AD7 ld a,(iy+6) / 1ADA sub &01 / daa / ld (iy+6),a` | supprime la décrémentation d'énergie au contact d'un ennemi (routine &1AB3) |
| « Inmune a las pocimas malas y el fuego » | &1504-&1505 = 0 ; &107A-&107B = 0 | `1504 sub &01` (chaudron nocif, &14DD) ; `107A sub &01` (case nocive, &1048) | chaudrons empoisonnés et cases « feu » ne retirent plus d'énergie |
| « Flotar en el agua » | &0FDD = &18 | `0FDB cp &81 / 0FDD jr nz,&1006` devient `jr &1006` | plus jamais de noyade : l'eau devient un sol |
| « Facilidad en abrir las puertas » | &1558-&155A, &159C-&159E = 0 ; &18D9-&18DB = 0 ; &0861-&0863 = 0 | `cp (iy+5)` (objet porté) dans les deux routines de barrière ; `cp (iy+5) / jr nz` dans le test d'arme | barrières ouvertes sans l'objet requis ; **effet de bord** : le test d'arme devient `FD 00 / 00 / 00 / 2C`, tout ennemi touché avec FEU meurt quel que soit l'objet. Le patch &0861 (comparaison objet porté / ancien objet pour rafraîchir la ligne d'état) n'a pas d'effet sur les portes : il force seulement le rafraîchissement du texte (patch probablement erroné du cracker, **hypothèse, confiance moyenne**). Les deux portes verrouillées par blason / fleur de lys (&1BAF, &1BB7) ne sont **pas** patchées. |

## 5. Carte mémoire (après relocalisation)

| Zone | Contenu | Preuve |
|---|---|---|
| &0038 | `jp &1D93` (interruption) | &0601-&0609 |
| &05CF-&22F0 | code de jeu, textes, tables | désassemblage récursif (5,5 Ko de code tracé) |
| &1C36-&1C3A | sablier : adresse écran, compteurs ligne/colonne, prédiviseur | &1BF2 |
| &1C3B | graine aléatoire (incrémentée pendant le titre) | &06D6, &0DD4 |
| &1C3C-&1C4F | 5 × 4 n° de salles dont le chaudron devient nocif | &073B |
| &1C56 | accumulateur de dégâts (fraction /256) | &1ACF, &106E |
| &1C5F-&1C61 | **score**, 3 octets BCD (6 chiffres) | &1B8C, &08BB |
| &1C96 / &1C97 / &1C98 | compteur de trame, n° de tranche d'interruption, table de tranches | &1D93 |
| &1CB2 / &1CC3 / &1CD4 | palettes (16 encres + bordure, couleurs matérielles) | &1BBF |
| &1CF5 | 19 identifiants d'objet (0 = rien) → noms en &1F1B | &1AF4 |
| &1D07 | 8 projectiles de sort × 4 octets (Y, X, dY, dX) | &1A56 |
| &1D80 | 5 départs (salle, Y, X) | &06EA |
| &1D8F | 2 gestionnaires de verrou de porte (&1BAF, &1BB7) | &1496 |
| &122D | **nombre de sorciers libérés** | &1A02, &1270 |
| &2299-&2410 | pilote d'effets sonores + données ; &2411-&27C5 musique du titre (3 voix) | §12 |
| &2FC0-&323F | image du sablier (16 octets × 40 lignes, mode 1) | &07B9 |
| &3240-&59EB | cartes de tuiles des salles, RLE | &0E4E |
| &5A40-&5B7F | objets posés : 40 salles × 2 × (Y, X, id, déjà-pris) | &0718 |
| &5B80-&62FF | fiches de salle : 40 × 48 octets | &0723 |
| &6300- | police 8×8 (code ASCII × 8 + &6200) | &1B62 |
| &6500- | tuiles 4×8 px mode 0 (16 octets) | &0E92 |
| &7500-&AAxx | sprites 12×24 px mode 0 (144 octets, n° × 144 + &7500) | &0D96 |
| &AB00-&AB27 | 40 drapeaux « salle déjà visitée » | &0B72 |
| &AB28-&AB31 | **bloc d'état joueur (IY)**, voir §6 | |
| &AB32-&AB61 | copie de travail de la fiche de la salle courante (iy+10..iy+57) | &0B65 |
| &AB68-&ACA7 | copie de travail des objets posés | &0718 |
| &ACA8-&AF77 | carte de collision 40 × 18 cellules | &0EB4 |
| &AF78-&B6F7 | copie de travail des 40 fiches de salle (état persistant) | &0723, &13BA |
| &C000-&FFFF | écran ; pile sous &C000 | &05DD |

## 6. Variables d'état (IY = &AB28)

| Adresse | Champ | Valeurs |
|---|---|---|
| &AB28 (iy+0) | bits 0-2 : état du sorcier (table &1D70) ; bit 3 : sous-phase ; bit 4 : temps écoulé ; bit 5 : pause ; bit 6 : fin de partie ; bit 7 : sprite affiché | états : 0 attente (64 trames), 1 apparition, 2 **jeu**, 3 chute après énergie nulle, 4 agonie, 5 noyade, 6 fin de noyade |
| &AB29 (iy+1) | **Y du sorcier** (lignes, 0..120, coin haut) | butées : `cp &78` (&11D2), `sub 2 / ret c` (&11BB) |
| &AB2A (iy+2) | **X du sorcier** (pixels mode 0, 0..148) | butées : `cp &94` (&1195), `sub 2 / ret c` (&117E) |
| &AB2B (iy+3) | n° de sprite affiché : &1C-&1F vers la gauche, &20-&23 de face, &24-&27 vers la droite (+ animation toutes les 4 trames) | &1023-&1042 |
| &AB2C (iy+4) | compteur d'animation | |
| &AB2D (iy+5) | **objet porté** (id = n° de sprite, 0 = rien) | |
| &AB2E (iy+6) | **énergie**, BCD, **99** au départ (`ld (iy+6),&99`, &07F1), affichée « ENERGY 99% » | |
| &AB2F (iy+7) | minuterie d'état / cible de déplacement | &07F5 (`&C0`) |
| &AB30 (iy+8) | **salle courante** (0..39 ; 40 = décor du titre) | &0B53 |
| &AB31 (iy+9) | ligne clavier 9 = **joystick 0** (actif bas) : b0 haut, b2 gauche, b3 droite, b4 feu, b7 DEL (pause) | &112D |
| &AB32… | fiche de salle courante (§8) | |

## 7. Cadence, physique et commandes

### 7.1 Synchronisation
- Interruption IM 1 (&1D93) à **300 Hz** ; à chaque VSYNC (bit 0 du port PPI B `&F5xx`) la tranche
  est recalée à 3. Six tranches par trame (table &1C9A en jeu) : 0 effets sonores (&2299),
  1 bascule **mode 1 + encre 0 bleue** pour le bandeau (`&7F00`,`&44`,`&8D`, après une boucle
  d'attente), 2 **sablier** (&1BF2), 3 rien, 4 retour **mode 0 + encre 0 noire** (`&54`,`&8C`),
  5 lecture du joystick (&112D). Chaque tranche est donc appelée à **50 Hz**.
- &1C96 est décrémenté à chaque interruption ; la boucle principale (&07FC) attend qu'il passe
  négatif puis le remet à 7 : **une itération toutes les 8 interruptions = 37,5 Hz** au mieux
  (4 seulement juste après un changement de salle, &0BC4). Les routines d'affichage attendent en
  plus la VBL par `in a,(&F5xx) / rra` (&1605). Cadence réelle = 37,5 Hz si le travail tient dans
  26,7 ms **(hypothèse sur la tenue du budget, confiance moyenne)**.

### 7.2 Déplacement du sorcier (état 2, &0F2F-&1045)
| Grandeur | Valeur binaire | Preuve |
|---|---|---|
| Boîte | **12 × 24 px** mode 0 (3 × 3 cellules) | tests de collision &11B4/&11CB/&1177/&118E sur 3 (ou 4 si non aligné) cellules |
| Montée (joystick haut) | **2 lignes par trame** | `dec (iy+1)` × 2 (&0F3A) |
| Chute (haut relâché) | **2 lignes par trame**, vitesse constante, pas d'accélération | `inc (iy+1)` × 2 (&0FC9) |
| Bas | **non utilisé** : le bit 1 du joystick n'est jamais testé | recherche de `(iy+9)` |
| Horizontal | **2 px mode 0 par trame**, sans inertie | `dec/inc (iy+2)` × 2 (&0F4B, &0F8A) |
| En px/s (à 37,5 Hz) | 75 px/s horizontal, 75 lignes/s en montée comme en chute | |
| Limites | Y 0..120, X 0..148 ; **les bords de l'écran sont des murs** (pas de flip-screen) | &11D2, &1195 |

- Collision : une cellule est bloquante si son attribut a le bit 7 (`rla / ret c`, &11E5).
- Sortie d'une salle : uniquement par une **porte** (§8.3).

### 7.3 Bouton feu
- Front montant uniquement (verrou &1C58, &1155).
- Si un objet posé est à |dY| ≤ 18 et |dX| ≤ 9 : **échange** objet porté / objet posé (&17C5) ;
  premier ramassage d'un objet : +250 points.
- Sinon, si l'objet porté est l'**étoile filante** (&37) ou le **sac de sorts** (&46) : il est
  consommé et lance un sort (&1842, §10.3).
- Il est **impossible de poser un objet dans le vide** : sans objet à portée, rien ne se passe.
- Contre un ennemi : voir §10.2. DEL = pause, feu = reprise (&080C).

## 8. Les salles

### 8.1 Nombre et géométrie
- **40 salles** (0..39) + une 41e carte de tuiles (n° 40) qui sert de décor à l'écran titre
  (`ld (iy+8),&28`, &0629). Fiches : 40 × 48 octets copiées de &5B80 vers &AF78 (`ld bc,&0780`).
- Aire de jeu : **40 × 18 cellules de 4 × 8 px** = 160 × 144 px en mode 0 ; le bandeau d'état
  (lignes 144-199) est en **mode 1** par bascule en cours de balayage.
- Carte de tuiles (&3240) : flux RLE ; un octet ≠ 0 = n° de tuile, `00 n` = n cellules vides,
  `FF` = fin de salle ; la salle r est la (r+2)e liste (la première est une liste factice).
- Attributs de collision calculés au chargement (&0EB4) :

| Tuiles | Attribut | Sens (preuve) |
|---|---|---|
| &00, &DF-&FF | &00 | vide |
| &01-&1F | &81 | **eau** : solide ; se poser avec les 3 (ou 4) cellules sous les pieds en &81 = **noyade** immédiate (&0FD1-&1003) ; animée sur 4 images (&194C) |
| &20-&47 | &01 | traversable, animé sur 4 images (&1966) ; rôle visuel exact non établi **(hypothèse : décor animé, confiance basse)** |
| &48-&6F | &02 | **nocif (« fuego » du trainer)** : la rangée basse du sorcier sur une telle case coûte 50/256 d'énergie par trame (&1048-&1084) ; animé sur 2 images (&1980) |
| &70-&DE | &80 | solide |

Les tuiles &01-&6F donnent leur attribut à la cellule **et à sa voisine de droite** (objets de 2 cellules).

### 8.2 Fiche de salle (48 octets, copiée en &AB32 = iy+10)
| Octets | Champ |
|---|---|
| 0 | n° de nom de lieu (18 textes, &1E3A) ; 1 : inutilisé (toujours 0) |
| 2-9, 10-17 | deux ennemis : type (bits 0-3), Y, X, sprite, compteur, -, direction, - |
| 18-21, 22-25 | portes gauches 1 et 2 : Y, X, destination, verrou |
| 26-29, 30-33 | portes droites 1 et 2 |
| 34-36 | chaudron bienfaisant : Y, X, - |
| 37-39 | chaudron nocif : Y, X, dégâts |
| 40-42 | barrière verticale (sprite &43, porte de cage) : Y, X, objet requis |
| 43-45 | barrière horizontale (sprite &42, trappe) : Y, X, objet requis |
| 46-47 | sorcier captif : Y, X |

`FF` en Y = absent. La fiche est recopiée dans &AF78 en sortant (&13BA) : **l'état d'une salle
(ennemis tués, barrières ouvertes) persiste toute la partie**.

### 8.3 Portes
- 109 liens de porte au total (106 réciproques, 3 à sens unique : 17→9, 38→18, 39→38).
- Octet destination : bits 0-5 = salle, bit 7 = arrivée par une porte droite, bit 6 = porte n° 2.
- On franchit une porte en poussant contre elle, au **même Y exactement** et à 12 px (&0F53-&0F7C).
- Verrou (octet 4) : 0 = libre ; 1 = exige de porter le **COAT OF ARMS** (&3B, &1BAF) ;
  2 = exige la **FLEUR DE LYS** (&2B, &1BB7). L'objet **n'est pas consommé**. Le verrou ne
  concerne que le sens où il est déclaré. 8 portes verrouillées (4 + 4).
- Premier passage dans une salle : +500 points (&0B6D-&0B7D).

### 8.4 Barrières (portes de cage et trappes)
- 28 barrières (14 verticales &43, 14 horizontales &42). Verticale : le sorcier doit être au même
  Y et à 8 px (&1584) ; horizontale : 8 lignes au-dessus et au même X (&1542). Il faut **porter
  l'objet requis**, qui est **consommé** (`ld (iy+5),0`) ; la barrière disparaît (3 × 3 cellules
  libérées, &15C6) définitivement.

### 8.5 Départ aléatoire et chaudrons
- Index = graine &1C3B modulo 5 (&06D6). Départs (salle, Y, X) : (0, 0, 64), (24, 0, 76),
  (29, 32, 124), (15, 56, 116), (22, 16, 64).
- **9 chaudrons** (sprite &36, tous identiques) dans les salles 4, 13, 19, 22, 23, 27, 31, 33, 39.
  Selon l'index, **2 d'entre eux deviennent nocifs** (déplacés dans le champ « nocif » avec
  dégâts = 2, &0749-&0775) : {22, 4}, {13, 33}, {19, 23}, {23, 27} ou {19, 31}.
- Chaudron bienfaisant : sorcier posé dessus (Y = Ychaudron − 16, |dX| ≤ 4) : **+1 point
  d'énergie par trame** jusqu'à 99 (&14A1). Il ne rend pas de temps.
- Chaudron nocif : **−1 point par VBL, 2 fois par trame** (boucle `djnz` avec attente VBL, &14FE).

### 8.6 Table des salles (lue dans le binaire)
Ennemis : T1 = poursuivant volant, T2 = marcheur, T3 = spectre ondulant (§10) ; aspect d'après
le n° de sprite (identification visuelle, **hypothèse, confiance moyenne**). Barrières :
V = porte de cage verticale, H = trappe.

| # | Lieu | Ennemis | Portes (côté→salle) | Chaudron | Barrières (objet requis) | Captif | Objets posés |
|---|---|---|---|---|---|---|---|
| 0 | NEAR THE VILLAGE | T1 masque, T2 moine | G→1, G→39 |  |  |  | BALL & CHAIN, SHOOTING STAR |
| 1 | NEAR THE VILLAGE | T2 moine, T1 masque | G→23, D→0 |  |  |  | LARGE BOTTLE, STRONG SWORD |
| 2 | OUTSIDE THE CASTLE | T1 oeil, T2 moine | G→3, G→27 [verrou blason], D→16, D→10 |  |  |  | DOOR KEY, LARGE BOTTLE |
| 3 | IN THE CASTLE | T3 fantome | G→4, G→27 [verrou blason], D→2 |  |  |  | COAT OF ARMS, SCROLL |
| 4 | IN THE CASTLE | T2 moine, T1 masque | G→5, D→3 | oui | V:LARGE BOTTLE |  | SACK OF SPELLS, BALL & CHAIN |
| 5 | OUTSIDE THE CASTLE | T2 moine | G→29, D→4 |  |  |  | STRONG SWORD, SHARP AXE |
| 6 | NEAR THE CHATEAU | T3 fantome, T1 masque | G→7, G→18 [verrou fleur de lys], D→23 |  |  |  | SHARP AXE, GOLDEN CHALICE |
| 7 | ABOVE THE CHATEAU | T1 oeil, T2 moine | G→8, D→6 |  |  |  | LARGE BOTTLE, STRONG SWORD |
| 8 | ABOVE THE CHATEAU | T2 moine, T3 fantome | G→24, G→38 [verrou fleur de lys], D→7 |  | H:SPELL BOOK | **oui** | SPELL BOOK, SHOOTING STAR |
| 9 | NEAR THE CHATEAU | T2 moine, T1 sanglier | G→10, D→24, D→18 [verrou fleur de lys] |  |  |  | DOOR KEY, FLEUR DE LYS |
| 10 | AT THE WATERFALL | T1 oeil, T3 fantome | G→11, G→2, D→11, D→9 |  |  |  | BALL & CHAIN, LITTLE LYRE |
| 11 | AT THE WATERFALL | T1 masque, T3 fantome | G→16, G→10, D→12, D→10 |  |  |  | LARGE BOTTLE, DOOR KEY |
| 12 | IN THE PALACE | T2 moine, T3 fantome | G→11, D→13 |  | V:LARGE BOTTLE |  | GOBLET OF WINE, SHOOTING STAR |
| 13 | IN THE PALACE | T2 moine, T1 oeil | G→12, D→14, D→24 | oui | H:DOOR KEY |  | BALL & CHAIN, SORCERER'S MOON |
| 14 | IN THE PALACE | T3 fantome, T1 masque | G→15, D→13 |  | H:LITTLE LYRE | **oui** | MAGIC WAND, SHOOTING STAR |
| 15 | IN THE PALACE | T1 sanglier, T3 fantome | G→16, D→14 |  |  |  | SHOOTING STAR, SHARP AXE |
| 16 | NEAR THE PALACE |  | G→28, G→11, D→15, D→2 |  |  |  | SACK OF SPELLS, SHOOTING STAR |
| 17 | IN THE TUNNEL | T2 moine, T2 moine | G→9, G→19, D→18 |  | H:DOOR KEY |  | DOOR KEY, BALL & CHAIN |
| 18 | IN THE CHATEAU | T2 moine, T1 sanglier | G→9, G→17, D→6 |  | V:DOOR KEY, H:DOOR KEY |  | DOOR KEY, MAGIC WAND |
| 19 | IN THE TUNNEL | T1 oeil, T3 fantome | G→20, D→17 | oui | V:LARGE BOTTLE |  | DOOR KEY, BALL & CHAIN |
| 20 | IN THE TUNNEL | T2 moine, T3 fantome | G→21, D→19 |  | V:MAGIC WAND | **oui** | STRONG SWORD, LARGE BOTTLE |
| 21 | IN THE TUNNEL | T2 moine, T3 fantome | G→22, D→20 |  | H:DOOR KEY |  | JEWELLED CROWN, COAT OF ARMS |
| 22 | IN THE TUNNEL | T2 moine, T2 moine | G→25, D→21 | oui | V:DOOR KEY, H:COAT OF ARMS |  | STRONG SWORD, SPELL BOOK |
| 23 | IN THE WOODS | T1 masque, T1 oeil | G→6, D→1 | oui | V:LARGE BOTTLE |  | FLEUR DE LYS, SHOOTING STAR |
| 24 | ABOVE THE CHATEAU | T2 moine, T1 oeil | G→13, G→9, D→8 |  |  |  | LARGE BOTTLE, BALL & CHAIN |
| 25 | IN THE STRONGROOM | T2 moine, T2 moine | G→26, G→32, D→22 |  | V:JEWELLED CROWN, H:DOOR KEY | **oui** | SACK OF SPELLS, LARGE BOTTLE |
| 26 | IN THE DUNGEONS | T2 moine, T2 moine | G→29, D→27, D→25 |  | H:LARGE BOTTLE |  | DOOR KEY, STRONG SWORD |
| 27 | IN THE DUNGEONS | T3 fantome, T1 masque | G→3 [verrou fleur de lys], G→26, D→2 | oui | V:SCROLL, H:LARGE BOTTLE | **oui** | SHARP AXE, LARGE BOTTLE |
| 28 | AT SANCTUARY |  | D→16 |  |  |  |  |
| 29 | IN THE WASTELANDS | T1 sanglier, T1 oeil | G→30, G→30, D→5, D→26 [verrou blason] |  |  |  | SHOOTING STAR, JEWELLED CROWN |
| 30 | IN THE WASTELANDS | T3 fantome | G→31, G→31, D→29, D→29 |  | V:GOBLET OF WINE | **oui** | STRONG SWORD, SHARP AXE |
| 31 | IN THE WASTELANDS | T2 moine | G→36, G→35, D→30, D→30 | oui | H:LARGE BOTTLE |  | LARGE BOTTLE, SACK OF SPELLS |
| 32 | IN THE TUNNEL | T2 moine, T1 sanglier | G→33, D→25 [verrou blason] |  | H:DOOR KEY |  | SORCERER'S MOON, COAT OF ARMS |
| 33 | IN THE TUNNEL | T2 moine, T1 sanglier | G→34, G→34, D→32 | oui | V:DOOR KEY, H:LARGE BOTTLE |  | GOBLET OF WINE, DOOR KEY |
| 34 | AT THE TUNNEL MOUTH | T1 sanglier, T1 sanglier | G→35, D→33, D→33 |  |  |  | SACK OF SPELLS, DOOR KEY |
| 35 | AT THE TUNNEL MOUTH | T2 moine, T1 sanglier | G→36, D→31, D→34 |  |  |  | LARGE BOTTLE, DOOR KEY |
| 36 | NEAR STONEHENGE | T1 sanglier | G→37, D→31, D→35 |  |  |  | STRONG SWORD, BALL & CHAIN |
| 37 | AT STONEHENGE | T3 fantome | D→36 |  | V:SORCERER'S MOON | **oui** | LARGE BOTTLE, SHARP AXE |
| 38 | IN THE CHATEAU | T2 moine, T2 moine | G→18, D→8, D→39 |  | V:GOLDEN CHALICE, H:DOOR KEY |  | DOOR KEY, LARGE BOTTLE |
| 39 | IN THE CHATEAU | T1 masque, T3 fantome | G→38, G→38, D→0 | oui | V:LARGE BOTTLE | **oui** | BALL & CHAIN, SACK OF SPELLS |

Graphe : les 40 salles sont toutes atteignables depuis la salle 0 en ignorant verrous et
barrières. Le sanctuaire (28) n'a qu'une porte (vers 16) ; Stonehenge (37) n'a qu'une porte (vers 36).

## 9. Objets

- 17 objets nommés + « rien » ; l'identifiant est le n° de sprite (&1CF5, noms en &1F1B).
  78 objets posés au départ (2 emplacements par salle, &5A40) ; chaque salle ne peut contenir
  que 2 objets (on échange).

| Id | Nom | Rôle prouvé |
|---|---|---|
| &28 | JEWELLED CROWN | ouvre la cage de la salle 25 |
| &29 | LARGE BOTTLE (×12) | ouvre 11 barrières, dont la cage de la salle 39 |
| &2A | DOOR KEY (×11) | ouvre 11 barrières (surtout des trappes) |
| &2B | FLEUR DE LYS (×2) | verrou de porte type 2 |
| &2C | SHARP AXE (×6) | tue les ennemis T3 |
| &2D | BALL & CHAIN (×9) | tue les ennemis T1 |
| &37 | SHOOTING STAR (×8) | sort : 8 projectiles |
| &38 | SCROLL | cage de la salle 27 |
| &39 | GOLDEN CHALICE | barrière V de la salle 38 |
| &3A | LITTLE LYRE | trappe-cage de la salle 14 |
| &3B | COAT OF ARMS (×3) | verrou de porte type 1 ; barrière H de la salle 22 |
| &40 | GOBLET OF WINE (×2) | cage de la salle 30 |
| &41 | STRONG SWORD (×8) | tue les ennemis T2 |
| &44 | SPELL BOOK (×2) | trappe-cage de la salle 8 |
| &45 | MAGIC WAND (×2) | cage de la salle 20 |
| &46 | SACK OF SPELLS (×6) | sort : 4 projectiles |
| &47 | SORCERER'S MOON (×2) | cage de Stonehenge (37) |

Aucun objet ne rend d'énergie ni de temps : seuls les chaudrons rechargent l'énergie.

## 10. Ennemis, captifs et sorts

### 10.1 Types (table de sauts &1D62, indexée par l'octet 0 & &0F)
| Type | Routine | Comportement | Tué par (FEU + contact) | Dégâts (fraction /256 par trame) | Nombre |
|---|---|---|---|---|---|
| 1 | &160F | vole droit vers le sorcier, **1 px en X et 1 ligne en Y par trame**, bloqué par les murs ; sprites &00 (masque), &3C (œil), &58-&5B (tête de sanglier) | BALL & CHAIN (&2D) | **75** (≈ 0,29 %/trame) | 27 |
| 2 | &167A | marcheur : ne bouge qu'en X, **1 px par trame** vers le sorcier, après une animation de demi-tour (sprites &10-&1B, moine) | STRONG SWORD (&41) | **60** (≈ 0,23 %) | 28 |
| 3 | &16E7 | spectre : **2 px par trame** en X vers le sorcier avec demi-tours animés, **1 ligne par trame** en Y vers lui, traverse les murs (sprites &04-&0F) | SHARP AXE (&2C) | **50** (≈ 0,20 %) | 15 |
| 4 | &189D | explosion de mort (sprites &4C-&4F), puis type 0 | | | |
| 5 | &19E0 | sorcier captif (sprites &54-&57) | | | 8 |
| 6 | &1A34 | sorcier libéré qui s'envole (2 lignes par trame) | | | |

- Les ennemis n'agissent que pendant l'état 2 du joueur. Contact : |dY| ≤ 18 et |dX| ≤ 9 (&1AB3).
- Dégâts : l'accumulateur &1C56 (partagé avec les cases nocives) est diminué de la valeur
  ci-dessus à chaque trame de contact ; à chaque retenue, énergie −1 (BCD).
- Tuer : contact + **bouton feu** + porter l'arme du type (&18B9) ; l'arme est **consommée**,
  +1000 points, et l'ennemi est **mort pour toute la partie** (type 0 sauvegardé dans la fiche).

### 10.2 Captifs
- 8 captifs (salles 8, 14, 20, 25, 27, 30, 37, 39), dans une cage fermée par une barrière.
  **Aucun objet n'est testé pour les libérer** : il suffit de les toucher (|dY| ≤ 22,
  |dX| ≤ 10, &19E0) ; l'objet sert à ouvrir la barrière de la cage (§8.4) et y est consommé.
  Libération : compteur &122D +1, **+2000 points**, le captif s'envole.
- Objet de cage (géométrie barrière / captif vérifiée sur rendu) : 8 SPELL BOOK, 14 LITTLE LYRE,
  20 MAGIC WAND, 25 JEWELLED CROWN, 27 SCROLL, 30 GOBLET OF WINE, 37 SORCERER'S MOON,
  39 LARGE BOTTLE **(attribution haute confiance)**.
- Noms (message final, &220C) : FRANK, BILL, FRED, SAM, BOB, JIM, MICK, JOE ; l'association
  nom/salle n'existe pas dans le code.

### 10.3 Sorts
- SHOOTING STAR : 8 projectiles depuis le centre du sorcier (dY ±4, dX ±2 ; table &1D07) ;
  SACK OF SPELLS : 4 projectiles (haut, bas, gauche, droite). Ils avancent de 4 lignes / 2 px
  par trame jusqu'au bord, tuent tout ennemi de type 1-3 touché (+500 points, &1909).

## 11. Énergie, temps, score, fin de partie

| | Valeur binaire | Preuve |
|---|---|---|
| Énergie | 0..**99** BCD, départ 99, affichée « ENERGY nn% » | &07F1, &1AA9 |
| Temps | sablier : image de 16 × 40 octets effacée **d'un octet toutes les 72 VBL** ; 640 × 72 / 50 = **921,6 s = 15 min 22 s** ; s'arrête en pause | &1BF2, &1C38 = &2810, &1C3A = &47 |
| Vies | **une seule** | |
| Morts | énergie nulle (« YOU HAVE RUN OUT OF ENERGY »), noyade (« YOU HAVE DROWNED IN THE RIVER »), sablier vide (« YOUR LUCK AND TIME RAN OUT ») | &1006, &0FD1, &1C26 |
| Score | +500 nouvelle salle, +250 premier ramassage d'un objet, +1000 ennemi tué à l'arme, +500 ennemi tué par sort, +2000 captif libéré ; **pas de bonus de temps** ; affiché seulement en fin de partie | &0B79, &1807, &18FD, &1A0E |
| Victoire | 8 sorciers libérés **et** sorcier au sanctuaire (salle 28) en Y = 24, X = 72 : fondu de palette, « CONGRATULATIONS! YOU HAVE SAVED … » | &1270-&1331, &08FC |
| Sanctuaire | les sorciers libérés y apparaissent et s'animent (&0BE3, &11F0) | |
| Meilleurs scores | 5 entrées (DAVE, ANDY, IAN, STEVE, TRICIA), nom de 16 caractères | &2194 |
| Œuf de Pâques | un nom proche de « HUGH BAND » affiche « HELLO HUGH! STICK TO TABLE FOOTBALL! » | &0A9B |

## 12. Textes, écran, palette, son

- **Textes** (bit 7 = fin de chaîne, codes < &20 = jetons de mots « YOU ARE », « CARRYING A »,
  « IN THE », « NEAR THE », « WITH A », table &1E0D) : 18 noms de lieux (WOODS, OUTSIDE THE CASTLE,
  CASTLE, CHATEAU ×2, ABOVE THE CHATEAU, WASTELANDS, VILLAGE, AT THE WATERFALL, PALACE ×2,
  TUNNEL, DUNGEONS, STRONGROOM, AT SANCTUARY, AT THE TUNNEL MOUTH, NEAR STONEHENGE,
  AT STONEHENGE), 17 noms d'objets (§9), 3 messages de mort, titre défilant (&206F), fin.
  Le bandeau affiche une phrase « YOU ARE IN THE WOODS, CARRYING A SHARP AXE. ».
- **Écran** : mode 0 (gate array `&8C`) pour l'aire de jeu, mode 1 (`&8D`) pour le bandeau ;
  CRTC R12/R13 = &30/&00 ; R1 animé à l'écran titre (&063C). Sprites dessinés en XOR.
- **Palette de jeu** (&1CB2, couleurs firmware) : encres 0-15 = 0 noir, 24 jaune vif, 15 orange,
  6 rouge vif, 20 cyan vif, 26 blanc vif, 14 bleu pastel, 17 magenta pastel, 18 vert vif,
  10 cyan, 3 rouge, 9 vert, 25 jaune pastel, 19 vert d'eau, 13 gris, 12 jaune (olive) ; bordure 1
  (bleu). Le bandeau mode 1 a l'encre 0 en **bleu** (matériel &44). Titre (&1CC3) : noir, blanc
  vif, bleu ciel, reste gris. Écrites directement au gate array (`&7F00+n`), pas par le firmware.
- **Son** : PSG AY-3-8912 écrit directement via le PPI (&22F1 : port A `&F4xx` = donnée,
  port C `&F6xx` = &C0 sélection de registre, &80 écriture). Deux canaux d'effets à 50 Hz :
  bruit (registres 6 et 8) et ton sur la voie B (registres 2, 3, 9), séquences
  (durée, période, volume) en &2312-&2410 (douleur &2408, ramassage &23E7, porte &238D/&23BA,
  mort/meurtre &2371, sort/libération &2346, noyade &2315). Musique de titre sur 3 voix (&2411).

## 13. Méthode et outils (reproductible)

```
python3 -I sorcery/tools/dsk_extract.py IMAGE.dsk /chemin/hors/depot/dsk_out
python3 -I sorcery/tools/basic_detok.py /chemin/hors/depot/dsk_out/SORCERY.BAS
python3 -I sorcery/tools/sorcery_dump.py /chemin/hors/depot/dsk_out --mem /chemin/hors/depot/mem.bin [--map N]
python3 -I sorcery/tools/z80dis.py /chemin/hors/depot/mem.bin 0 1AB3 +40
```
- `dsk_extract.py` : DSK/EDSK, secteurs hors format, catalogue, extents, blocs, en-têtes AMSDOS
  (checksum vérifié), blocs libres non vides.
- `basic_detok.py` : détokeniseur Locomotive BASIC.
- `z80dis.py` : désassembleur Z80 complet (CB/ED/DD/FD/DDCB) écrit pour l'occasion (ni rizin ni
  capstone disponibles ; Ghidra présent mais non nécessaire). Le désassemblage récursif
  (graines &05CF, &1D93 + tables de sauts &1D62/&1D70, chaînes en ligne après `call &1B32`)
  couvre ≈ 5,5 Ko de code ; les zones non tracées sont des données (vérifié).
- `sorcery_dump.py` : refait la relocalisation, décode départs, salles, portes, barrières,
  captifs, objets, palettes, et la classe de collision des cellules.
- Vérification visuelle : rendu des tuiles et sprites dans le scratchpad (non versionné) ; les
  positions de la fiche tombent exactement sur portes, cages, chaudrons et objets dessinés.

## 14. Limites

- Analyse **statique** uniquement (pas d'exécution dans un émulateur) : la cadence de 37,5 Hz
  suppose que la boucle tient dans son budget de 8 interruptions.
- Rôle visuel des tuiles &20-&47 (attribut &01, animé) non établi.
- Les mouvements fins des ennemis (demi-tours, ordre des sprites) sont résumés, pas modélisés
  à la trame près ; les noms d'ennemis (masque, œil, sanglier, moine, spectre) viennent d'une
  identification visuelle des sprites.
- La musique et les enveloppes sonores ne sont pas transcrites (et ne doivent pas l'être).
- Cette disquette est **Sorcery** ; les chiffres de Sorcery+ (75 écrans, chapitre 2) ne
  peuvent pas être vérifiés ici.

## 15. Écarts avec la recréation actuelle

Les valeurs « binaire » sont exprimées dans les unités de la recréation (logique à 50 Hz,
pixels Mode 0, énergie sur 100) ; facteur 37,5/50 = 0,75 pour passer « par trame » à « par tick ».

### 15.1 `config.py`
| Constante | Actuel | Binaire | Note |
|---|---|---|---|
| `TILE` / `COLS` / `ROWS` | 8 / 20 / 19 | cellules **4 × 8**, **40 × 18** | grille carrée 8×8 → cellules 4 px de large |
| `PLAY_H` / `HUD_Y` | 152 / 152 | **144 / 144** | bandeau de 56 lignes en mode 1 |
| `TICK_HZ` | 50 | **37,5** (ou garder 50 et multiplier les vitesses par 0,75) | §7.1 |
| `TIME_LIMIT_MIN` | 30 | **15,36** (921,6 s) | §11 |
| `ENERGY_MAX` | 100.0 | **99** (départ 99) | BCD |
| `SPEED_X` | 1.0 | **1.5** px/tick (2 px/trame) | §7.2 |
| `SPEED_UP` | 1.0 | **1.5** | |
| `SPEED_FALL` | 0.5 | **1.5** (même vitesse que la montée) | |
| `SPEED_DOWN` | 1.0 | **sans objet** (pas de commande « bas ») ; à défaut = `SPEED_FALL` | |
| `SCORE_KILL` | 100 | **1000** (arme) / **500** (sort) | |
| `SCORE_FREE` | 500 | **2000** | |
| `SCORE_TIME_PER_S` | 10 | **0** (aucun bonus de temps) | |
| (nouveau) | - | +500 première visite d'une salle ; +250 premier ramassage d'un objet | |
| `PALETTE` | 16 couleurs génériques | encres de jeu : (0,0,0) (255,255,0) (255,128,0) (255,0,0) (0,255,255) (255,255,255) (128,128,255) (255,128,255) (0,255,0) (0,128,128) (128,0,0) (0,128,0) (255,255,128) (0,255,128) (128,128,128) (128,128,0) ; bordure / fond du bandeau (0,0,128) | §12 |

### 15.2 `entities.py`
| Élément | Actuel | Binaire |
|---|---|---|
| `Player.w, Player.h` | 6, 16 | **12, 24** |
| `Player.update` : `inp.down` → `SPEED_DOWN` | plongée | supprimer : seul « haut » compte ; sinon chute à vitesse constante |
| Bords d'écran | `_check_transition` (flip-screen) | murs ; changement de salle par porte seulement |
| Taille des ennemis | 6-8 × 6-15 | **12 × 24** ; contact si \|dY\| ≤ 18 et \|dX\| ≤ 9 |
| Mouvements | sine, chase, erratic, yoyo, jump, patrol | **3 comportements** : T1 poursuite 2 axes 1 px/trame (0,75/tick) ; T2 marche horizontale 1 px/trame avec demi-tour ; T3 2 px/trame en X (1,5/tick) + 1 ligne/trame en Y, traverse les murs |

### 15.3 `world.py`
| Élément | Actuel | Binaire |
|---|---|---|
| Nombre de salles (Ch.1) | 37 + flip-screen par les bords | **40**, reliées par **109 portes** (+ sanctuaire 28 et Stonehenge 37 en cul-de-sac) |
| `START` | L2 fixe | **5 départs aléatoires** (salles 0, 24, 29, 15, 22) |
| `ENEMY_TYPES[*]["drain"]` | 0,25-0,60 par tick | T1 **0,22**, T2 **0,176**, T3 **0,146** par tick (75/60/50 ÷ 256 × 0,75) |
| `ENEMY_TYPES[*]["killed_by"]` | épée, croix, torche, hache… | T1 BALL & CHAIN, T2 STRONG SWORD, T3 SHARP AXE ; sorts SHOOTING STAR / SACK OF SPELLS contre tous |
| Poisson / bulle invincibles | présents | **absents** |
| Réapparition des monstres | à chaque retour dans la salle | **jamais** (mort définitive) ; l'arme est **consommée** |
| Tuer au contact | automatique si l'arme est portée | **il faut appuyer sur feu** au contact |
| `OBJECTS` potions/cœurs (+40) | 4 cœurs | **aucun** objet d'énergie |
| `CAPTIVES[*]["item"]` | objet testé sur le captif | le captif se libère au **toucher** ; l'objet ouvre la **porte de cage** et est consommé |
| `DOORS` | 6 portes à clé | 8 portes verrouillées (COAT OF ARMS ×4, FLEUR DE LYS ×4, non consommés) + 28 barrières à objet consommé |
| Chaudrons `plein`/`maudit` fixes | `"plein"`, `"maudit"` | 9 chaudrons identiques, **2 tirés au sort** deviennent nocifs ; bienfaisant **+0,75/tick** (actuel 0,5), nocif **−1,5/tick** (actuel −0,4) |
| Eau | −0,4/tick (lave −0,7) | **noyade instantanée** si l'on se pose dessus ; aucun drain |
| Cases nocives (feu) | lave seulement (Ch.2) | cases « feu » au Ch.1 : **0,146/tick** au niveau des pieds |
| `FINAL_WEAPON`, vortex, `BOSS_*` | Sceptre, Nécromancien, Ch.2 | **absents de cette version** : victoire = 8 libérés + retour au sanctuaire |

### 15.4 `game.py` (comportements)
- `self.time_left` : 15 min 22 s, s'arrête pendant la pause.
- Bouton feu : échange uniquement (pas de « poser dans le vide »), plus lancement de sort
  avec SHOOTING STAR / SACK OF SPELLS.
- HUD : texte « YOU ARE … CARRYING A … », « ENERGY nn% », sablier qui s'efface ; score et
  nombre de libérés affichés seulement en fin de partie.

### 15.5 `DESIGN.md` (statut des marques)
- [C] « 17 écrans / 3 sorciers » vs « 40 / 8 » : **40 salles et 8 sorciers** pour Sorcery CPC.
- [C] chaudrons qui rechargent / qui pompent : **les deux**, tirage aléatoire par partie.
- [I] vies : confirmé, **une seule vie**.
- [I] contrôles 4 directions : **faux**, la direction « bas » n'existe pas.
- [V] « chaque sorcier exige un objet précis » : à nuancer, l'objet ouvre la cage, pas le sorcier.
- [V] « trappes ouvertes par des clés » : confirmé (barrières H, souvent DOOR KEY).
- [V] Stonehenge : confirmé comme lieu (salle 37, un captif) ; pas de Nécromancien dans cette version.
- [I] objets « Épée, Hache, Croix, Clé dorée, Torche… » : remplacer par la liste du §9.
