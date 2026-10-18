# Bastion Gelé

Petit jeu original pour navigateur, en un seul fichier (`index.html`). Il mêle un village de survie en terre gelée et une défense de couloir où un héros tire tout seul. Il fonctionne hors ligne, sans publicité ni achat, et ne fait aucune requête réseau. Tous les graphismes sont dessinés par le code.

## Lancer le jeu
Ouvrez `index.html` dans un navigateur, sur mobile en portrait ou sur ordinateur. La partie est sauvegardée dans le `localStorage`. Si le stockage est bloqué, le jeu fonctionne quand même, mais la partie n'est pas conservée.

## Commandes
- **Mobile** : glissez le doigt horizontalement sur le couloir pour déplacer le héros. Le bouton rond déclenche sa compétence.
- **Ordinateur** : la souris, ou les touches ← → / A·Q / D, déplacent le héros. `Espace` ou `E` lance la compétence, `P` ou `Échap` met en pause.

## Village
- **Ressources** : bois, pierre, fer et pain. La Scierie, la Carrière, la Mine et la Ferme les produisent chaque seconde. La production continue hors ligne pendant 8 h au plus, dans la limite de l'entrepôt.
- **Hôtel de ville** : il fixe le niveau maximal des autres bâtiments et la capacité de l'entrepôt.
- **Améliorations** : le coût est multiplié par environ 1,5 à chaque niveau. Les délais vont de 5 à 60 s en temps réel. Il n'y a qu'un chantier à la fois et aucune monnaie d'accélération.
- **Caserne** : elle forme des Fantassins, des Cavaliers et des Archers par lots de 5.
- **Académie** : elle débloque 4 recherches (production, dégâts, PV du héros, vitesse des flèches).
- **Muraille** : elle détermine les PV du mur en défense.

## Défense
- **Ennemis** : les vagues descendent vers le mur. On y trouve des pillards, des brutes, des loups rapides et des frondeurs qui visent le héros. Un seigneur arrive toutes les 5 vagues.
- **Améliorations de partie** : à chaque niveau gagné par l'XP, et après chaque seigneur vaincu, vous choisissez 1 amélioration parmi 3 (tir multiple, perforation, cadence, flèches de givre, archer allié, réparation, critique, puissance).
- **Bannières** : elles descendent par paires (« +1 flèche », « ×2 dégâts »…). Placez le héros du côté voulu quand elles le croisent.
- **Troupes** : celles de la Caserne apportent des bonus passifs. Les archers fournissent des tourelles de flanc. Les fantassins ajoutent des PV au mur et une garnison qui frappe les ennemis au contact. Les cavaliers lancent une charge périodique qui balaie une colonne.
- **Fin de partie** : la partie s'arrête quand le mur tombe, ou quand vous abandonnez. Le butin (ressources et **Insignes**) dépend des vagues tenues. Vous perdez 10 % de vos troupes.

## Triangle des armes
Fantassin › Cavalier › Archer › Fantassin. Une attaque contre le type qu'elle domine fait ×1,5 de dégâts, contre celui qui la domine ×0,67. Chaque ennemi porte un anneau de la couleur de son type. Cela vaut pour le héros (chacun a un type), les tourelles (archer), la garnison (fantassin) et la charge (cavalier).

## Héros
Les Insignes servent à débloquer les héros et à payer l'entraînement permanent (Force, Vigueur, Célérité).
- **Aube** (archère) : Pluie de flèches.
- **Brann** (fantassin, 12 Insignes) : Rempart de fer, qui rend le mur invulnérable un moment, le soigne et repousse les ennemis.
- **Sélène** (cavalière, 25 Insignes) : Blizzard, qui gèle tous les ennemis.

## Réglages
Son activé ou coupé (bips WebAudio), statistiques et réinitialisation de la sauvegarde (en deux appuis).
