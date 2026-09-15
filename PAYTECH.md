# Configuration PayTech — Guide rapide

## 1. Créer un compte
→ https://paytech.sn → S'inscrire

## 2. Récupérer les clés API
→ Tableau de bord → Paramètres → Clés API

Vous aurez 2 clés :
- **API_KEY**
- **API_SECRET**

## 3. Configurer le projet
Copier `.env.example` → `.env` à la racine de QUICKFOODS_V3 et remplir :

```
PAYTECH_API_KEY=votre_api_key_ici
PAYTECH_API_SECRET=votre_api_secret_ici
PAYTECH_ENV=test

# URLs callback (remplacer par votre domaine en production)
PAYTECH_IPN_URL=http://127.0.0.1:5000/payment/ipn
PAYTECH_SUCCESS_URL=http://127.0.0.1:5000/payment/success
PAYTECH_CANCEL_URL=http://127.0.0.1:5000/payment/cancel
```

## 4. Installer les dépendances
```
pip install -r requirements.txt
```

## 5. Flux de paiement

```
Client clique "Payer en ligne"
        ↓
POST https://paytech.sn/api/payment/request-payment
        ↓
Redirection vers la page de paiement PayTech
        ↓
Client paie (Wave / Orange Money / Carte)
        ↓
PayTech envoie IPN → /payment/ipn  (type_event=sale_complete)
        ↓
Commande marquée "En préparation"
        ↓
Redirection → /payment/success
```

## 6. Tester en mode test
En mode `PAYTECH_ENV=test`, PayTech fournit des numéros Wave / Orange Money
fictifs pour simuler des paiements sans argent réel.

## 7. Passer en production
1. Changer `PAYTECH_ENV=prod` dans `.env`
2. Remplacer les URLs `PAYTECH_*_URL` par votre domaine HTTPS
3. S'assurer que `/payment/ipn` est accessible publiquement (pas derrière un VPN ou localhost)

## Sans clés PayTech
L'application fonctionne normalement — le bouton "Payer en ligne"
redirige automatiquement vers paiement à la livraison avec un message explicatif.
