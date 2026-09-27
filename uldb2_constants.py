"""Buchungsannahme mit Gewichtslimit - feste Annahmen, Reglerstufen, Presets, Farben.

Drei Regler bilden genau die drei Sweep-Dimensionen der Messreihe ab (Restzeit T, Gewichtslimit,
Preis-Gewicht-Korrelation - siehe AP 0 / tests/test_results.py). Die Preisschwelle ist ein reiner
Live-Regler OHNE Messreihen-Abdeckung: sie wirkt direkt auf jede live gerechnete Instanz
(uldb2_model.policy_threshold), unabhängig von der vorgerechneten Messreihe (data/uldb2_results.json), die
nur die zwei fest gemessenen Schwellen (Mitte des Preisbereichs, Preisuntergrenze) enthält."""

WEIGHT_RANGE = (200.0, 2000.0)
PRICE_RANGE = (2.0, 12.0)
MID_PRICE_PER_KG = 7.0  # Schwelle "th_mid" der Messreihe (Mitte des Preisbereichs)
LOW_PRICE_PER_KG = 2.0  # Schwelle "th_low" der Messreihe (Preisuntergrenze, praktisch FCFS)

# --- Reglerstufen (genau die drei Sweep-Dimensionen) ----------------------------------------------------
T_OPTIONS = (15, 25, 40)
T_DEFAULT = 25

CAP_OPTIONS = (1500.0, 2500.0)
CAP_DEFAULT = 2500.0

CORR_OPTIONS = (0.0, 0.3, 0.6)
CORR_DEFAULT = 0.3

# --- Preisschwelle: reiner Live-Regler, kein Sweep-Raster ------------------------------------------------
THRESHOLD_RANGE = (2.0, 12.0)
THRESHOLD_DEFAULT = 7.0
THRESHOLD_STEP = 0.5

SEED_RANGE = (0, 149)  # n_instances der Vorab-Messreihe (150 Instanzen je Zelle)
SEED_DEFAULT = 0

COLOR_FCFS = "#2a6fb0"
COLOR_THRESHOLD = "#9fc2e6"
COLOR_DP = "#3d8b5f"

PRESETS = {
    "Standard": dict(t=25, cap=2500.0, corr=0.3, threshold=7.0, seed=0),
    "Viel Restzeit": dict(t=40, cap=2500.0, corr=0.3, threshold=7.0, seed=0),
    "Wenig Restzeit": dict(t=15, cap=2500.0, corr=0.3, threshold=7.0, seed=0),
    "Zu niedrige Schwelle": dict(t=25, cap=2500.0, corr=0.3, threshold=2.0, seed=0),
    "Weniger Auslastung, mehr Umsatz": dict(t=25, cap=2500.0, corr=0.3, threshold=7.0, seed=0),
}

PRESET_HELP = {
    "Standard": "25 Buchungsgelegenheiten, 2.500 kg Limit, mittlere Preis-Gewicht-Korrelation: FCFS verliert deutlich, eine einfache Preisschwelle holt das meiste zurück.",
    "Viel Restzeit": "T = 40: hier verliert die feste Preisschwelle am meisten gegenüber der optimalen Regel.",
    "Wenig Restzeit": "T = 15: hier ist die feste Preisschwelle fast so gut wie die optimale Regel.",
    "Zu niedrige Schwelle": "Schwelle = 2 EUR/kg (Preisuntergrenze): eine Schwelle, die kaum filtert, verhält sich wie FCFS.",
    "Weniger Auslastung, mehr Umsatz": "Der Kern-Befund direkt erlebbar: die optimale Regel erreicht mehr Umsatz bei NIEDRIGERER Auslastung.",
}
