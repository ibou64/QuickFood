# QuickFood V4 🍽️

Plateforme de livraison de repas pour le marché sénégalais — application web moderne
avec API mobile prête pour une future app native.

## 🚀 Lancement rapide

```bash
cd QUICKFOODS_V3
python -m venv venv
source venv/bin/activate          # Windows : .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env              # puis éditez SECRET_KEY, JWT_SECRET_KEY, ADMIN_PASSWORD
python app.py
```

⚠️ **Important** : générez de vraies valeurs pour `.env` avant tout déploiement :
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## 🔐 Compte admin
- Email : `admin@quickfood.sn`
- Mot de passe : défini par `ADMIN_PASSWORD` dans `.env` (⚠️ ne jamais laisser la valeur par défaut en production)

## 💳 Configuration PayTech (paiement)
1. Créer un compte sur [paytech.sn](https://paytech.sn)
2. Récupérer votre `API_KEY` et `API_SECRET` depuis le tableau de bord
3. Remplir `.env` :
```
PAYTECH_API_KEY=votre_api_key
PAYTECH_API_SECRET=votre_api_secret
PAYTECH_ENV=test
PAYTECH_IPN_URL=https://votredomaine.com/payment/ipn
PAYTECH_SUCCESS_URL=https://votredomaine.com/payment/success
PAYTECH_CANCEL_URL=https://votredomaine.com/payment/cancel
```

## 🗺️ Frais de livraison par distance (Haversine)
| Distance    | Frais       |
|-------------|-------------|
| 0 – 2 km    | 500 FCFA    |
| 2 – 5 km    | 1 000 FCFA  |
| 5 – 10 km   | 1 500 FCFA  |
| 10 – 20 km  | 2 500 FCFA  |
| > 20 km     | 3 500 FCFA  |

## 📁 Structure
```
├── app.py                  # Point d'entrée
├── config.py                # Configuration (sécurité, JWT)
├── extensions.py            # SQLAlchemy, LoginManager, SocketIO, JWT, CORS
├── models/                  # User, Order, Restaurant, Product, Driver, Review, PromoCode, Notification...
├── routes/
│   ├── main.py, auth.py, cart.py, client.py, partner.py, admin.py
│   ├── driver.py            # Espace livreur (dispo, position GPS, livraisons)
│   ├── reviews.py           # Avis restaurants + livreurs
│   ├── notifications.py     # Cloche de notifications in-app
│   ├── payment.py, support.py
│   └── api_v1.py            # 📱 API JSON + JWT pour app mobile (voir plus bas)
├── services/                 # CartService, OrderService, DriverService, PromoService, NotificationService...
├── sockets/                  # Événements Socket.IO (notifications live, position livreur)
├── utils/                    # helpers, delivery (Haversine), security
└── templates/                 # Templates Jinja2 (+ static/css/modern.css : design system V4)
```

## 📱 API mobile (`/api/v1/...`)
Base JSON + JWT indépendante des routes web, pensée pour une future app native
(React Native/Flutter) tout en servant déjà la PWA :

| Endpoint | Description |
|---|---|
| `POST /api/v1/auth/register` / `login` / `refresh` | Authentification JWT |
| `GET /api/v1/restaurants` | Liste (tri par distance si `lat`/`lng` fournis) |
| `GET /api/v1/restaurants/<id>` | Détail + produits |
| `GET/POST /api/v1/cart` | Panier (session) |
| `POST /api/v1/promo/validate` | Valider un code promo |
| `GET /api/v1/orders`, `/orders/<id>` | Commandes du client + position du livreur en direct |

Toutes les routes (sauf auth et lecture publique) nécessitent `Authorization: Bearer <token>`.

## ✅ Nouveautés V4
- 🛵 **Module Livreurs complet** : attribution automatique du livreur le plus proche (Haversine),
  espace livreur avec position GPS live, historique de livraisons
- 📍 **Suivi de commande en temps réel** : carte Leaflet + Socket.IO pour le client
- ⭐ **Avis clients** : notes restaurant + livreur, réponses du commerçant côté admin
- 🏷️ **Codes promo** : % ou montant fixe, plafonds, restrictions par commerce/utilisateur
- 🔔 **Notifications in-app** en temps réel (cloche, Socket.IO), prêtes pour un relais SMS/push futur
- 📱 **API JSON + JWT** (`/api/v1`) — base propre pour app mobile native
- 🎨 **Refonte visuelle** : nouveau design system (`static/css/modern.css`), pages client
  (accueil, commerces, menu, panier, commandes) repensées avec animations et composants modernes
- 🔐 **Corrections sécurité** : plus de clé secrète codée en dur, avertissement mot de passe admin
- 🐛 **Bug corrigé** : statuts de commande incohérents (`"livré"` minuscule vs `"En attente"` capitalisé)
  unifiés dans tout le code — cycle complet : *En attente → Confirmée → En préparation → Prête
  → Livreur assigné → En livraison → Livrée / Annulée*
- 🐛 **Bug corrigé** : les livreurs étaient redirigés vers l'accueil après connexion au lieu de
  leur tableau de bord

## 🗺️ Roadmap suggérée (V5)
- App mobile native (React Native/Flutter) branchée sur `/api/v1`
- Vrai provider SMS/push (ex: Firebase Cloud Messaging, Twilio) derrière `NotificationService`
- Refonte visuelle des back-offices admin/partenaire (actuellement fonctionnels mais non redesignés)
- Programme de fidélité (points cumulés par commande)
- Filtres avancés (prix, temps de livraison estimé) sur la liste des commerces
