# Kingshot (Century Games, 2025) - Teardown de game design

Méthode : sources publiques uniquement (presse, wikis/guides de fans). Pas d'APK, pas de décompilation. Les guides de fans se contredisent parfois et évoluent avec les patchs : les points marqués **[?]** sont incertains ou mono-source. Plusieurs sites (kingshot.net, pocketgamer.biz) n'ont pas pu être ouverts directement ; ils ne sont cités qu'à partir des extraits de recherche.

## 1. Fiche technique publique
- Éditeur : Century Games (même studio que Whiteout Survival). Sortie : fin février 2025, mobile iOS + Android.
- Genre : 4X / stratégie de construction de royaume médiéval, avec couche tower defense/puzzle (présente aussi dans la pub).
- Modèle : free-to-play, achats intégrés (packs de gemmes ~0,99-99,99 $, abonnement type "King's Pass"), gacha de héros. Cible UA très agressive (milliers de créas/jour, Meta/TikTok/YouTube).
- Chiffres : 100 M$ en 117 jours ; ~500 M$ net en 11 mois ; ~812 M$ la première année (AppMagic). Répartition revenus : ~62 % App Store / 38 % Google Play. Backlash de baleines (whales) rapporté.
- Moteur : **non documenté publiquement dans mes sources** (Unity probable mais non confirmé). Taille d'install : **non trouvée**.

## 2. Boucles de jeu
**Core loop (minutes)** : lancer une amélioration/entraînement/recherche -> attendre (timer) -> collecter ressources, récolter -> réinvestir dans la file suivante. Le joueur se connecte pour vider les files et les relancer.

**Court terme (session, 5-15 min)** : collecter, lancer constructions/recherches/entraînement, marches sur la carte (monstres, ressources), missions quotidiennes, mini-jeu de défense initial pour la première "victoire".

**Moyen terme (jours)** : monter le Town Center (TC), débloquer héros et recherches, événements quotidiens/hebdomadaires, rallye d'alliance, Bear Hunt, progression de héros (shards).

**Long terme (semaines/mois)** : générations de troupes (Gen 1 -> Gen 7+ citées), guerres de royaume/alliances, domination serveur, VIP, héros mythiques. Le contenu endgame est social et compétitif.

## 3. Systèmes
**Bâtiments & ressources** : le Town Center est le verrou central ; son niveau conditionne tous les autres bâtiments (guides unanimes). Ordre de priorité cité : TC, Embassy, bâtiments militaires (infanterie/cavalerie/archers), Académie, bâtiments de ressources. Ressources de base de type nourriture/bois/pierre/fer **[? noms exacts non vérifiés]**, plus gemmes (premium), Forgehammers (événements), accélérateurs par catégorie (construction, recherche, entraînement).

**Troupes** : 3 types. Infanterie (PV/défense max, vitesse min), Cavalerie (équilibrée, vitesse max), Archers (dégâts élevés, fragiles). Triangle de contre décrit par la communauté : Infanterie > Cavalerie > Archers > Infanterie (pas de confirmation éditeur). Formations typiques : 50/20/30 par défaut ; Bear Hunt 10/10/80 ou 1/10/89 (Gen 4+), valeurs contestées entre sources. Générations (Gen 1...) = paliers de tiers.

**Héros** : raretés Epic puis Legendary/Mythic. Mythic : 3 compétences Conquest + 3 Expedition de base + un "widget" (bonus d'expédition/conquête + stats). Epic : 3 Conquest, 2 Expedition, pas de widget. Progression par fragments (shards) : sources = Arena, missions Intel, pêche, boutique VIP, boutique Swordland ; certains héros (Helga, Amadeus) n'acceptent que leurs propres shards. Héros cités : Jabel (Legendary cavalerie gratuit jour 2), Amadeus, Saul, Helga, Chenko, Quinn, Prince William, etc.

**Recherche (Académie)** : arbres Croissance/Militaire ; priorités conseillées : vitesse de construction/recherche, "Leadership Tactics I" (slot de marche supplémentaire) **[? mono-source]**.

**Alliance** : rallyes, garnisons, aides (réduction de timers) **[? inféré du genre]**, boosts, guerres, événements collectifs.

**PvP / carte du monde** : carte partagée par royaume, marches, rallyes contre bases ennemies et monstres, bouclier, garnisons, guerres entre royaumes **[? détails partiels]**.

**Événements** : Bear Hunt (événement d'alliance : rallyes contre l'Ours enragé ; récompenses : Forgehammers, accélérateurs, coffres de ressources ; joiners limités ~80-100k troupes ; lancements de rallye échelonnés). Autres : Arena, pêche, événements quotidiens.

**Mini-jeu tower defense / puzzle** : intro interactive en temps réel, déploiement de héros contre des vagues, donne une première victoire avant le 4X lent. Fortement utilisé dans les publicités (le pub-game est un levier d'acquisition, souvent plus simple que le jeu réel : décalage créa/produit **[? courant dans le genre, non vérifié ici]**).

## 4. Économie & monétisation
- **Timers** : constructions, recherches, entraînement s'allongent exponentiellement avec le niveau ; accélérateurs (minutes/heures) obtenus par événements ou achat.
- **Gemmes** : ~500 gemmes/dollar (taux uniforme des packs VIP) ; servent à accélérer, acheter, tirer des héros.
- **VIP** : niveau via XP VIP, packs spéciaux (shards de Helga pour VIP 1-6, Amadeus 7-12, XP, accélérateurs 1 h).
- **King's Pass / battle pass**, packs limités dans le temps, offres de bienvenue, abonnement.
- **Gacha** : tirage de héros/shards.
- **Leviers psychologiques** : FOMO (événements et offres limités, classements), timers (attente -> paiement pour éviter l'ennui), gating par TC, aversion à la perte (boucliers, pertes de troupes), pression sociale d'alliance (rallyes à heure fixe), progression de collection, ancrage de prix (packs 99,99 $), engagement quotidien (streaks).
- Risque réglementaire cité : frais Google de 20 % potentiels sur achats donnant un avantage.

## 5. Garder vs retirer (version solo hors-ligne sans monétisation)
**Garder** : progression par Town Center et dépendances de bâtiments ; files de construction/recherche/entraînement (timers courts ou temps de jeu réel) ; triangle infanterie/cavalerie/archers ; héros avec compétences et fragments (loot déterministe) ; arbre de recherche ; mini-jeu tower defense comme combat principal ; boss type Bear Hunt en PvE solo ; événements scénarisés ; carte avec monstres/ressources contre IA.

**Adapter** : timers -> durées courtes ou accélérées par actions du joueur ; alliance -> PNJ alliés/compagnons ; rallyes -> escouades IA ; gacha -> récompenses de quêtes/ pitié fixe ; événements -> campagnes scriptées.

**Retirer** : gemmes premium, VIP, battle pass, packs, offres limitées, publicités, FOMO calendaire, PvP serveur réel, abonnements, boucliers/gating payant, notifications de rétention.

## 6. Sources
- https://kingshot.net/wiki/guides/beginner-guide (extrait de recherche)
- https://kingshot.net/wiki/troops/troop-formation-guide
- https://kingshot.net/wiki/troops/infantry-overview
- https://kingshotguide.com/
- https://www.kingshotguide.org/guide/2026-kingshot-bear-hunt-guide
- https://kingshotoptimizer.com/guides/kingshot-bear-hunt-guide/
- https://kingshotmastery.com/guides/bear-hunt
- https://kingshotmastery.com/guides/kingshot-troop-guide
- https://kingshotmastery.com/guides/hero-skills-and-builds
- https://kingshotmastery.com/blog/kingshot-vip-special-packs-guide
- https://www.kingshotguide.com/database/hero-shards
- https://www.pocketgamer.biz/kingshots-first-year-800m-11-months-of-growth-but-backlash-from-whales
- https://www.pocketgamer.biz/kingshot-surpasses-100m-in-just-117-days
- https://appfigures.com/resources/insights/kingshot-500m-revenue-century-games/amp
- https://respawn.outlookindia.com/gaming/gaming-news/century-games-kingshot-crosses-100-million-in-just-117-days
- https://foxdata.com/fr/blogs/kingshot-a-remastered-survival-strategy-game-poised-to-dominate-mobile-in-2025/
