# Politique de sécurité

<p align="center">
  <a href="SECURITY.md">English</a> · <b>Français</b>
</p>

## Signaler une vulnérabilité

**Merci de ne pas ouvrir d'issue publique pour les problèmes de sécurité.**

Le canal préféré est le **Private vulnerability reporting de GitHub** (onglet Security → « Report a vulnerability »). Les signalements restent privés jusqu'à divulgation coordonnée.

Si pour une raison ou une autre vous ne pouvez pas accéder au formulaire de Private vulnerability reporting, ouvrez une issue publique brève et non révélatrice demandant un canal privé ; un mainteneur vous répondra avec un canal. **N'incluez aucun détail d'exploitation dans cette issue initiale.**

Lors du signalement, merci d'inclure :

- Une description claire du problème
- La version affectée (commit hash si possible)
- Les étapes de reproduction
- L'impact attendu et toute preuve de concept
- Si vous souhaitez être crédité dans l'éventuel advisory

---

## Versions supportées

| Canal                    | Tag d'image                                             | Supporté                                         |
| ------------------------ | ------------------------------------------------------- | ------------------------------------------------ |
| Dernière stable          | `:latest` (= le `vX.Y.Z` le plus récent sans tiret)     | ✅ Les correctifs sécurité arrivent ici          |
| Pré-release              | `:beta` (= le `vX.Y.Z-rc.N` / `-beta.N` le plus récent) | 🟡 Best-effort, sans garanties                   |
| Anciennes lignes stables | tout `:vA.B.Z` une fois qu'un `vC.D.0` plus récent sort | ❌ Merci de mettre à jour avant tout signalement |

**Politique : dernière stable uniquement.** En tant que projet à mainteneur unique, MediaKeeper ne back-porte pas les correctifs de sécurité sur les anciennes lignes mineures. Quand une nouvelle release stable sort, seule celle-ci (et le tag flottant `:latest`) reçoit les correctifs suivants.

Tant que le projet est encore sur la ligne `v1.0.0-rc.x` avant la première stable `v1.0.0`, le canal pré-release (`:beta`) est le chemin de code le plus à jour et reçoit les correctifs en premier.

Voir [`docs/operations/updating.md`](docs/operations/updating.md) pour savoir comment mettre à jour ou changer de canal.

---

## À quoi s'attendre

| Étape                                               | Délai cible                                              |
| --------------------------------------------------- | -------------------------------------------------------- |
| Accusé de réception                                 | sous 72 heures                                           |
| Triage initial / évaluation de sévérité             | sous 7 jours                                             |
| Communication d'un plan de correction ou mitigation | sous 30 jours pour les problèmes confirmés               |
| Divulgation publique coordonnée                     | après la sortie d'un correctif, idéalement sous 90 jours |

Ces délais sont au mieux : ce projet est porté par un mainteneur sur son temps libre.

---

## Périmètre

**Dans le périmètre :**

- Authentification et gestion de session (login admin, login Portail, gestion JWT)
- Autorisation et permissions (isolation des scopes, permissions granulaires)
- Validation des entrées côté serveur et sûreté SQL/ORM
- Cryptographie (secrets chiffrés Fernet en base, hash des mots de passe, signature JWT)
- CSRF, XSS et autres vulnérabilités web classiques sur le frontend ou le backend
- Manipulation de fichiers (uploads, validation des chemins média, opérations du Gestionnaire de médias sur le système de fichiers)
- Vulnérabilités de dépendances avec un chemin d'exploitation crédible sur un déploiement par défaut

**Hors périmètre (sauf à démontrer un impact concret) :**

- Self-XSS qui demande à la victime de coller du contenu dans sa propre console
- Déni de service contre une instance auto-hébergée unique
- Constats de bonne pratique sans exploit reproductible
- Problèmes dans des services tiers en amont — merci de les remonter aux éditeurs concernés
- Vulnérabilités nécessitant un accès physique au serveur

---

## Safe harbour (recherche sécurité de bonne foi)

La recherche sécurité menée de bonne foi est la bienvenue :

- Testez uniquement contre votre propre déploiement, jamais contre l'instance d'un tiers sans son consentement écrit
- N'accédez pas, ne modifiez pas, ne détruisez pas de données qui ne vous appartiennent pas
- Ne lancez pas de scans automatisés qui génèrent une charge de déni de service
- Arrêtez-vous et faites un rapport dès que vous avez assez d'éléments pour décrire le problème

Aucune action en justice ne sera engagée contre les chercheurs qui respectent cette politique.

---

## Politique de divulgation

Nous appliquons la **divulgation coordonnée** : nous collaborons avec le rapporteur pour comprendre et reproduire le problème, gardons le rapport confidentiel jusqu'à la sortie d'un correctif, et créditons le rapporteur dans l'advisory sauf s'il préfère rester anonyme.

---

## Notes de durcissement

Quelques choix défensifs déjà documentés dans le code :

- Les mots de passe sont hachés avec bcrypt (facteur de coût 12 par défaut).
- Les secrets JWT doivent faire ≥ 32 octets ; l'application refuse de démarrer sinon.
- Les paramètres sensibles stockés en base (clés API, webhooks, tokens OAuth) sont chiffrés au repos avec Fernet.
- La protection CSRF utilise un pattern double-submit cookie sur toute route mutante.
- Les tentatives de connexion sont rate-limitées et suivies dans une table dédiée.
- Un workflow `Security` dédié lance `pip-audit`, `npm audit`, `bandit`, `ruff S` et `semgrep` à chaque push et chaque semaine.
