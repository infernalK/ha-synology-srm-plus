# Historique des versions

[English](CHANGELOG.md) · **Français**

## 0.5.25

- Le capteur des sessions d'administration s'appelle maintenant « Historique des connexions d'administration » : SRM ne renvoie qu'un historique de connexions (sans état ouvert ou fermé), jamais les sessions réellement ouvertes. Les enregistrements datés de 1970 (non renseignés) sont ignorés, ce qui évite aussi l'alerte « session d'administration depuis Internet » à cause d'eux. L'identifiant de l'entité ne change pas.
- La carte Protection contre les menaces a une option `show_admin_sessions` (aussi dans l'éditeur visuel) pour masquer la liste des connexions d'administration ; la tuile du nombre reste.
- L'utilisation du CPU et de la mémoire (%) est aussi affichée pour chaque satellite d'un mesh (« Utilisation CPU (nœud N) », « Utilisation mémoire (nœud N) ») ; le routeur principal garde ses capteurs. Le swap n'est fourni que pour le routeur principal.
- La carte Routeur a une option `show_unlinked_ports` (aussi dans l'éditeur visuel) : `false` masque les ports Ethernet sans lien, pratique pour les satellites peu câblés.
- Les capteurs des réseaux Wi-Fi ont un attribut `by_band` (clients et débits par bande), et la carte Routeur a une option `networks_by_band` (aussi dans l'éditeur visuel) pour afficher une tuile par réseau Wi-Fi et par bande, par exemple « IOT · 2.4G » et « IOT · 5G ».
- Corrigé : la carte Routeur n'affiche plus une carte vide par suivi de client depuis que les suivis ont leur propre appareil en 0.5.24.
- Nouvelle carte `synology-srm-trackers-card` : liste les clients suivis comme device trackers (nom, IP, MAC, en ligne ou non), en ligne d'abord. `show_offline: false` masque les clients hors ligne.

## 0.5.24

- Home Assistant 2026.11 et suivants : chaque suivi de client a maintenant son propre appareil (identifié par l'adresse MAC du client et nommé d'après lui), ce qui supprime l'avertissement indiquant que les suivis d'appareils sans informations d'appareil cesseront de fonctionner en 2028.11. Les versions plus anciennes de Home Assistant restent comme avant.
- Un suivi que vous arrêtez est supprimé avec son appareil quand plus rien d'autre ne l'utilise, et l'identifiant unique ne gêne plus le nettoyage des suivis sur la 2026.11.
- L'appareil d'un client peut être supprimé depuis l'interface ; celui du routeur ne le peut pas.

## 0.5.23

- Nouvelle action `synology_srm_plus.check_parallel` (Outils de développement > Actions) : un test en lecture seule, d'une dizaine de secondes, qui pose trois questions différentes au routeur en même temps, avec et sans le correctif de la 0.5.21, et compte les réponses qui appartiennent à une autre question. Sur un RT2600ac, la bibliothèque seule renvoyait environ une réponse sur dix qui était celle d'un autre appel ; avec le correctif, aucune. Collez son résultat quand vous demandez de l'aide.

## 0.5.22

- Réseaux Wi-Fi : de nouveaux capteurs par réseau Wi-Fi (le profil SRM, par exemple *IOT*) : nombre de clients (avec les bandes et SSID utilisés) et trafic de téléchargement / d'envoi.
- Carte routeur : le trafic des clients est affiché en deux sections, par connexion (Total, Filaire, bandes Wi-Fi) et par réseau Wi-Fi. Nouvelle option `traffic_by` (`both` par défaut, `bands` ou `networks`).
- Carte clients : deux rangées de filtres qui se combinent, par connexion (bande, filaire, hors ligne) et par réseau Wi-Fi, avec des compteurs qui suivent l'autre filtre. Nouvelle option `filter_by` (`both` par défaut, `connection` ou `network`). La recherche trouve aussi le nom du réseau.
- Éditeurs visuels pour les cinq cartes (titre, routeur, et les options de chaque carte).
- Adresse externe : seule une adresse valide de la bonne famille est affichée. `0:0:0:0:0:0:0:0`, une adresse MAC, une adresse locale de lien ou une IPv6 non globale donnent désormais *inconnu* au lieu d'une valeur fausse.
- Corrigé dans la carte clients : clients listés deux fois et pastille « Wi-Fi undefined » quand les capteurs par réseau étaient présents.

## 0.5.21

- Correction des réponses mélangées du routeur : la bibliothèque `synology-srm` partage un seul dictionnaire de paramètres entre tous les appels, donc des appels faits en même temps s'envoyaient mutuellement leur API, leur méthode et leur version et recevaient la mauvaise réponse (par exemple l'IP externe qui recevait l'enregistrement DDNS, ou les statistiques de menaces qui recevaient les réglages du capteur). Chaque appel a maintenant ses propres paramètres. C'était surtout visible sur les routeurs à plusieurs nœuds.
- Statistiques de menaces : si une réponse n'a pas ses données, l'appel est refait seul, puis avec les autres versions d'API que le routeur liste ; ce qui a été essayé est signalé une fois dans le journal et dans les diagnostics.
- IP externe : la réponse est aussi lue quand le routeur enveloppe la liste dans `{records: [...]}`, et l'adresse de la connexion WAN est utilisée quand le service d'IP externe n'en donne pas.
- Carte routeur : les ports sont regroupés par routeur, avec le nom du routeur en sous-titre quand il y en a plusieurs. Une petite ligne en bas indique la version des cartes et le nombre de nœuds et de ports reçus.
- Nouvelle action `synology_srm_plus.debug_report` : un court rapport texte (versions, routeurs, ports, adresse externe, statistiques de menaces, stockage, entités sans valeur), sans noms, adresses ni adresses MAC, à coller quand vous demandez de l'aide. Le même rapport, les versions d'API et l'état des entités principales figurent dans le fichier de diagnostics ; les adresses et les identifiants d'entité n'y sont pas indiqués.

## 0.5.20

- Carte routeur : correction d'une carte *Routeur* vide en trop affichée au-dessus de la vraie (introduite en 0.5.17). Elle venait des suivis de présence, qui n'appartiennent à aucun appareil routeur et sont maintenant ignorés.

## 0.5.20

- Cartes : elles sont maintenant chargées par un petit chargeur auto-réparateur (comme dans l'intégration Skolengo). Sous Firefox, les cartes pouvaient rester sur « Erreur de configuration » jusqu'à un rafraîchissement manuel ; le chargeur réimporte les cartes, recommence si les éléments manquent encore et demande à Lovelace de reconstruire les cartes restées en erreur. La ressource Lovelace existante est migrée automatiquement.

## 0.5.19

- Carte routeur : avec plusieurs nœuds de routeur (mesh), les ports du routeur principal ne sont plus mélangés à ceux des autres ; chaque autre nœud affiche ses propres ports dans sa tuile. Les tuiles sans valeur (par exemple l'IP externe d'un routeur secondaire) sont masquées.

## 0.5.18

- Carte clients : l'icône de câble des clients filaires est maintenant colorée comme les barres de signal Wi-Fi (vert à partir de 1 Gbit/s, jaune à 100 Mbit/s, rouge en dessous).

## 0.5.17

- Safe Access : le profil d'un réseau, que SRM nomme `$lbr0$`, `$lbr2$`…, prend maintenant le nom de ce réseau (par exemple *Primary Network*), lu dans les réseaux locaux du routeur. Les identifiants d'entité ne changent pas.
- Carte routeur : avec plusieurs routeurs, elle affiche maintenant une carte par routeur (elle mélangeait leurs ports, leur stockage et leurs adresses, et pouvait choisir un routeur secondaire sans IP externe). Un routeur sans stockage n'affiche plus 0 %.
- IP externe : si aucune entrée `WAN` ne porte d'adresse, n'importe quelle entrée qui en a une est utilisée.

## 0.5.16

- Clients filaires : la liste du trafic en direct du routeur est vide au premier appel après une pause (elle ne se remplit que pendant qu'on la demande), donc une réponse vide est maintenant redemandée au bout de deux secondes.

## 0.5.15

- Les clients filaires ont maintenant un débit de téléchargement / d'envoi (il valait toujours 0) : SRM n'en donne aucun dans la liste des appareils, il est donc lu dans le trafic en direct du routeur, qui ne liste que les appareils ayant échangé des données pendant la dernière seconde.

## 0.5.14

- Service *Explorer les API* (filtre `Traffic`) : écrit aussi dans le journal le trafic en direct de chaque client, par nom.

## 0.5.13

- Service *Explorer les API* : avec le filtre `Traffic`, il essaie aussi des appels de trafic par appareil avec des paramètres, pour trouver où lire le débit des clients filaires (toujours à 0 jusque-là).

## 0.5.12

- Après la première installation, une notification vous invite à recharger la page sans cache pour que les cartes du tableau de bord apparaissent (aussi documenté dans le README).

## 0.5.11

- Documentation : la section d'installation commence maintenant par la recherche de *Synology SRM Plus* dans HACS, l'intégration étant désormais dans le catalogue par défaut.

## 0.5.10

- Les réglages de connexion (hôte, compte, mot de passe, port, HTTPS) peuvent maintenant être modifiés avec *Reconfigurer* sur l'intégration, sans la supprimer et la rajouter. Les entités et l'historique sont conservés. Laissez le mot de passe vide pour garder l'actuel.

## 0.5.9

- Carte *Routeur* : nouvelle section *Points d'accès Wi-Fi* pour les autres nœuds du routeur (un répéteur comme le MR2200ac) : état, modèle, firmware, durée de fonctionnement, appareils connectés et débit. Les tuiles du routeur principal utilisent maintenant toujours le nœud 0, quel que soit l'ordre des entités.

## 0.5.8

- Carte *Contrôle d'accès* : nouvelle option `show_blocked_ips: false` qui masque la liste des adresses IP bloquées et ne garde que leur nombre (utile quand le routeur en bloque des dizaines de milliers). La liste reste affichée par défaut.

## 0.5.7

- Nouvelle option **Utiliser Safe Access** (*Configurer* sur l'intégration, activée par défaut). Désactivée, les appels Safe Access ne sont plus faits et les entités Safe Access sont supprimées, pour les routeurs qui n'utilisent pas le contrôle parental.

## 0.5.6

- Confidentialité : le compte, le mot de passe et l'identifiant de session (envoyés par SRM en paramètres d'URL) sont effacés des messages d'erreur et des journaux de débogage de `urllib3` ; une connexion échouée n'écrit plus de trace dans le journal.
- Le fichier de diagnostics masque maintenant les adresses IP, les adresses MAC (aussi comme clés de dictionnaire), les noms, les SSID et les secrets partout, et plus seulement sous quelques clés ; le journal de l'exploration masque aussi les noms de compte, d'utilisateur, d'hôte et de SSID.

## 0.5.5

- Un appel qui échoue pendant que d'autres tournent est refait une fois, seul, avant d'être signalé (le routeur peut répondre à une requête chargée par une réponse incomplète).
- Le routeur est interrogé sur quelques fils d'exécution : l'installation et les mises à jour sont bien plus rapides (le premier relevé prenait environ une minute, ce qui retardait le démarrage de Home Assistant).
- Nouvelle carte *Contrôle d'accès* (IP bloquées avec les réglages du blocage automatique, liste de blocage Wi-Fi, filtres MAC personnalisés, appareils bloqués), séparée de la carte *Protection contre les menaces*.
- Les capteurs de filtrage MAC Wi-Fi portent maintenant les noms que SRM leur donne : *Liste de blocage système Wi-Fi* (valable pour tous les SSID et prioritaire sur les filtres personnalisés ; elle contient aussi les appareils bloqués par la prévention des tempêtes de diffusion, dont les réglages sont des attributs) et *Filtres MAC personnalisés*.
- *Adresses IP bloquées* : les réglages du blocage automatique (activé, tentatives échouées, fenêtre, expiration) et les adresses bloquées sont maintenant des attributs du capteur.

## 0.5.4

- Filtrage MAC (lecture seule) : nombre de profils de filtre, appareils de la liste de filtrage, utilisation d'un filtre par chaque réseau Wi-Fi, et appareils que le routeur bloque. Affiché dans la carte de protection contre les menaces.
- Les réglages des réseaux Wi-Fi sont réduits à des champs sans risque avant d'être stockés (les données brutes contiennent les mots de passe Wi-Fi).

## 0.5.3

- Cartes : les débits et les durées Safe Access sont maintenant lus dans l'unité où Home Assistant les affiche (Mbit/s, heures). Avant, le débit du routeur, les tuiles de trafic des clients et le total Safe Access pouvaient être beaucoup trop petits.
- Safe Access : un appareil appartient à un seul profil.

## 0.5.2

- Safe Access : les appareils de chaque profil (état en ligne, IP, temps sur internet) en attribut et dans la carte (cliquez sur un profil pour le déplier) ; chaque client indique son profil Safe Access.

## 0.5.1

- L'utilisation du disque USB et les IP bloquées fonctionnent maintenant : certaines API de DSM se trouvent derrière un autre point d'accès que `entry.cgi`, lu dans la liste des API du routeur.
- Un appel d'API qui échoue est écrit une fois comme avertissement, puis au niveau débogage.

## 0.5.0

- Vrai débit du routeur, débit par bande, appareils connectés et état du routeur (depuis les API des nœuds mesh).
- Ports Ethernet : état du lien et vitesse (WAN et chaque port LAN).
- Utilisation du disque USB (%, utilisé, total).
- Sécurité : menaces détectées (24 h / 7 jours), nouveaux appareils, sessions d'administration, IP bloquées, redirections de ports, protection contre les menaces, et alertes quand l'interface d'administration est joignable depuis Internet ou qu'une session d'administration vient de l'extérieur.
- Safe Access (contrôle parental) : par profil, temps sur internet, état, « bloqué en ce moment » et filtres actifs.
- Les capteurs de canal Wi-Fi portent maintenant la largeur de canal, la puissance d'émission et le mode.
- Clients hors ligne avec leur dernière connexion (conservée entre les redémarrages).
- Nouvelles cartes de tableau de bord *Protection contre les menaces* et *Safe Access* (deux cartes séparées) ; les cartes routeur et clients affichent les nouvelles données ; les clients peuvent être triés par IP et par dernière connexion.
- `explore_api` masque maintenant les secrets, les adresses MAC et les IP publiques dans le journal.
- Suivi de présence : choisissez quels clients reçoivent une entité de présence ; les autres sont supprimés (pas d'entités fantômes).
- Icône de marque, README en anglais et en français, workflow de validation (hassfest + HACS), licence MIT.

## 0.4.x

- Détails des clients en attributs des capteurs de connexion, entités de présence facultatives par client, cartes de tableau de bord routeur et clients chargées comme ressource Lovelace.
- Service `explore_api`, téléchargement des diagnostics.

## 0.1 – 0.3

- Premières versions : capteurs CPU, mémoire, réseau, Wi-Fi, stockage et clients.
