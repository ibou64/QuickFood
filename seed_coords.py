"""
seed_coords.py — Initialisation des coordonnées GPS des restaurants
Couvre toutes les localités de la région de Dakar.
Matching automatique via l'adresse du restaurant.
"""
from app import create_app

app = create_app()

DAKAR_COORDS = {
    # ── DAKAR CENTRE ──────────────────────────────────────
    "Plateau":          (14.6928, -17.4467),
    "Médina":           (14.6950, -17.4500),
    "Fann":             (14.7080, -17.4660),
    "Point E":          (14.7100, -17.4700),
    "Colobane":         (14.7010, -17.4540),
    # ── ALMADIES / NGOR / OUAKAM ──────────────────────────
    "Almadies":         (14.7456, -17.5150),
    "Ngor":             (14.7400, -17.5100),
    "Ouakam":           (14.7289, -17.4978),
    "Mamelles":         (14.7350, -17.5000),
    # ── MERMOZ / SACRÉ-COEUR / LIBERTÉ ───────────────────
    "Mermoz":           (14.7167, -17.4833),
    "Sacré-Coeur":      (14.7190, -17.4700),
    "Liberté 6":        (14.7230, -17.4570),
    "Liberté 5":        (14.7210, -17.4590),
    "Liberté 4":        (14.7190, -17.4610),
    "Liberté 3":        (14.7170, -17.4630),
    "Liberté 2":        (14.7150, -17.4650),
    "Liberté 1":        (14.7130, -17.4680),
    "Liberté":          (14.7130, -17.4680),
    # ── GRAND DAKAR / HLM ────────────────────────────────
    "Grand Dakar":      (14.7135, -17.4505),
    "HLM 6":            (14.7150, -17.4450),
    "HLM 5":            (14.7130, -17.4470),
    "HLM 4":            (14.7110, -17.4490),
    "HLM 3":            (14.7090, -17.4510),
    "HLM 2":            (14.7070, -17.4530),
    "HLM 1":            (14.7050, -17.4550),
    "HLM":              (14.7050, -17.4550),
    # ── YOFF / AÉROPORT ──────────────────────────────────
    "Yoff":             (14.7667, -17.4667),
    "Ouest Foire":      (14.7600, -17.4500),
    "Virage":           (14.7500, -17.4900),
    "Aéroport":         (14.7397, -17.4902),
    # ── PIKINE ────────────────────────────────────────────
    "Pikine Technopole":(14.7600, -17.3800),
    "Pikine Icotaf":    (14.7500, -17.3900),
    "Pikine":           (14.7547, -17.3967),
    "Thiaroye":         (14.7700, -17.3500),
    # ── GUÉDIAWAYE ───────────────────────────────────────
    "Wakhinane Nimzatt":(14.7800, -17.3900),
    "Médina Gounass":   (14.7850, -17.3800),
    "Guédiawaye":       (14.7760, -17.3950),
    # ── RUFISQUE / BANLIEUE SUD ───────────────────────────
    "Sébikotane":       (14.7500, -17.1500),
    "Diamniadio":       (14.7300, -17.2000),
    "Rufisque":         (14.7167, -17.2667),
    # ── BANLIEUE EST ──────────────────────────────────────
    "Keur Massar":      (14.7900, -17.3200),
    "Malika":           (14.8000, -17.3300),
    "Keur Mbaye Fall":  (14.7800, -17.3500),
    "Yeumbeul":         (14.7700, -17.3700),
}

# Ordre important : les plus spécifiques d'abord
# (ex: "Liberté 6" avant "Liberté", "HLM 2" avant "HLM")
SORTED_COORDS = dict(
    sorted(DAKAR_COORDS.items(), key=lambda x: len(x[0]), reverse=True)
)

# Fallback centre Dakar si aucun quartier reconnu
DEFAULT_LAT, DEFAULT_LNG = 14.6928, -17.4467


def find_coords(address: str):
    """Retourne (lat, lng, quartier) depuis une adresse textuelle."""
    addr_lower = address.lower()
    for quartier, (lat, lng) in SORTED_COORDS.items():
        if quartier.lower() in addr_lower:
            return lat, lng, quartier
    return None, None, None


with app.app_context():
    from extensions import db
    from models.restaurant import Restaurant

    restaurants = Restaurant.query.all()
    total = len(restaurants)
    updated = 0
    fallback = 0
    skipped = 0

    print(f"\n{'─'*55}")
    print(f"  🗺️  Seed coordonnées GPS — Région de Dakar")
    print(f"  {total} restaurant(s) à traiter")
    print(f"{'─'*55}")

    for r in restaurants:
        if r.address and r.address.strip():
            lat, lng, quartier = find_coords(r.address)
            if lat:
                r.latitude  = lat
                r.longitude = lng
                print(f"  ✅ {r.name:<30} → {quartier} ({lat}, {lng})")
                updated += 1
            else:
                # Fallback : coordonnées centre Dakar
                r.latitude  = DEFAULT_LAT
                r.longitude = DEFAULT_LNG
                print(f"  ⚠️  {r.name:<30} → quartier non reconnu dans \"{r.address}\"")
                print(f"      → fallback centre Dakar ({DEFAULT_LAT}, {DEFAULT_LNG})")
                fallback += 1
        else:
            # Pas d'adresse → fallback centre Dakar
            r.latitude  = DEFAULT_LAT
            r.longitude = DEFAULT_LNG
            print(f"  ❌ {r.name:<30} → pas d'adresse → fallback centre Dakar")
            fallback += 1

    db.session.commit()

    print(f"\n{'─'*55}")
    print(f"  ✅ Mis à jour avec quartier reconnu : {updated}")
    print(f"  ⚠️  Fallback centre Dakar            : {fallback}")
    print(f"  Total traités                        : {updated + fallback}/{total}")
    print(f"{'─'*55}")
    print(f"\n  ℹ️  Pour corriger un restaurant manuellement :")
    print(f"     → /admin/restaurants → Modifier → Latitude / Longitude")
    print(f"     → ou relancer ce script après avoir mis à jour l'adresse\n")
