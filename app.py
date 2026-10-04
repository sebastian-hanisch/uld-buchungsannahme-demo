"""
Buchungsannahme mit Gewichtslimit - interaktive Fall-Demo (Luftfracht, Bid-Price-Kontrolle)
Sebastian Hanisch - Operations Research und Machine Learning

Eigenständiges Luftfracht-Stück, geschärft gegenüber revenue-management-demo (dort: zwei Frachtklassen,
JEDE Buchung verbraucht genau EINE diskrete Kapazitätseinheit, geschlossene Littlewood-Formel). Hier
verbraucht jede Buchungsanfrage ein ZUFÄLLIGES Gewicht aus einem gemeinsamen Gewichtslimit - ein Online-
Rucksackproblem, für das die Littlewood-Formel nicht funktioniert; eine dynamische Programmierung (DP,
Bid-Price-Kontrolle) ersetzt sie. Live: eine Instanz mit drei Regeln (FCFS, feste Preisschwelle, DP-Regel).
Vorgerechnet: die Messreihe über 150 Instanzen je Zelle (data/uldb2_results.json), die die Aussage trägt.

Lauffähig mit: streamlit run app.py
"""
import numpy as np
import streamlit as st

import uldb2_constants as C
import uldb2_results as R
import uldb2_visualization as V
from uldb2_dp import CAP_STEP, dp_value_function, policy_dp
from uldb2_format import fmt_num, fmt_pct
from uldb2_model import make_requests, policy_fcfs, policy_threshold, revenue_of
from uldb2_pdf_export import generate_uldb2_pdf
from uldb2_presets import (SETTING_SPECS, apply_preset, bounds, init_session_state_defaults, load_permalink_settings,
                            randomize_seed, sync_query_params)

st.set_page_config(page_title="Buchungsannahme mit Gewichtslimit – Sebastian Hanisch", layout="wide")

DATA = R.load_results()


@st.cache_data(show_spinner=False, max_entries=64)
def _value_function(t, cap, corr):
    """Hängt nur von (T, Kapazität, Korrelation) ab, nicht von Schwelle oder Seed - wird bei Reglerwechsel
    neu berechnet (Millisekunden, siehe ERGEBNIS.md Rechenzeit), nicht bei jedem Frame."""
    return dp_value_function(T=t, capacity_kg=cap, weight_range=C.WEIGHT_RANGE, price_range=C.PRICE_RANGE,
                              price_weight_corr=corr)


@st.cache_data(show_spinner=False, max_entries=256)
def _requests(t, corr, seed):
    rng = np.random.default_rng(seed)
    return make_requests(rng, t, corr, C.WEIGHT_RANGE, C.PRICE_RANGE)


def _live(t, cap, corr, threshold, seed):
    V_tab = _value_function(t, cap, corr)
    requests = _requests(t, corr, seed)
    acc = {
        "fcfs": policy_fcfs(requests, cap),
        "threshold": policy_threshold(requests, cap, threshold),
        "dp": policy_dp(requests, cap, V_tab),
    }
    revenue = {k: revenue_of(a, requests) for k, a in acc.items()}
    n_accepted = {k: sum(a) for k, a in acc.items()}
    utilization = {k: sum(r.weight_kg for r, ok in zip(requests, a) if ok) / cap for k, a in acc.items()}
    return dict(requests=requests, accepted=acc, revenue=revenue, n_accepted=n_accepted, utilization=utilization)


st.title("✈️ Buchungsannahme mit Gewichtslimit")
st.markdown(
    """
Luftfracht-Buchungsanfragen treffen **nacheinander** ein, jede mit ihrem **eigenen Gewicht** aus einem
gemeinsamen Gewichtslimit - anders als bei `revenue-management-demo` (zwei Frachtklassen, jede Buchung
verbraucht genau **eine** diskrete Kapazitätseinheit, geschlossene Littlewood-Formel) gibt es hier **keine
feste Einheitengröße**, die Littlewood-Formel funktioniert dafür nicht. Wie viel Umsatz kostet es, Anfragen
einfach anzunehmen, solange Platz ist (**FCFS**) oder mit einer **festen Preisschwelle** je kg zu arbeiten -
gegenüber einer Regel, die den **Restwert der Kapazität** kennt (**DP-Regel**, Bid-Price-Kontrolle)? Die
Demo zeigt live **eine Instanz** mit allen drei Regeln (immer alle drei gerechnet) und vorgerechnet die
Messreihe über **150 Instanzen je Zelle**, die die Aussage trägt. Wie das Modell funktioniert, steht im
Expander „Wie funktioniert diese Demo?" weiter unten, die formale Beschreibung im Expander
„📐 Mathematische Formulierung".
"""
)

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
preset_names = list(C.PRESETS)
for row in (preset_names[:3], preset_names[3:]):
    cols = st.columns(len(row))
    for col, name in zip(cols, row):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name])

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    st.markdown("**Buchungssituation**")
    t = st.select_slider("Buchungsgelegenheiten (Restzeit T)", options=list(C.T_OPTIONS), key="t_slider",
                          help="Gemessene Stufen der Messreihe (15 / 25 / 40).")
    cap = st.select_slider("Gewichtslimit (kg)", options=list(C.CAP_OPTIONS), key="cap_slider",
                            help="Gemessene Stufen der Messreihe (1.500 / 2.500 kg) - die einzige Ressource.")
    corr = st.select_slider("Preis-Gewicht-Korrelation", options=list(C.CORR_OPTIONS), key="corr_slider",
                             help="0 = Preis je kg unabhängig vom Gewicht; höhere Werte lassen den Preis je kg "
                                  "mit wachsendem Gewicht sinken (Massengut typischerweise günstiger je kg).")
    st.markdown("**Vergleichsregel**")
    threshold = st.slider("Preisschwelle (feste Schwellenregel)", *bounds("threshold_slider"),
                           step=C.THRESHOLD_STEP, key="threshold_slider", format="%.1f EUR/kg",
                           help="Reiner Live-Regler ohne eigene Messreihen-Abdeckung (wirkt auf jede Instanz "
                                "direkt). Am unteren Rand (nahe der Preisuntergrenze) verhält sich die Regel "
                                "praktisch wie FCFS.")
    st.markdown("**Gezeigte Instanz**")
    seed = st.number_input("Seed", *bounds("seed_input"), key="seed_input", step=1,
                            help="Nummer der gezeigten Buchungsfolge.")
    st.button("🎲 Neue Instanz", width="stretch", on_click=randomize_seed, help="Würfelt einen neuen Seed.")

sync_query_params({key: st.session_state[key] for key in SETTING_SPECS})
t, cap, corr, threshold, seed = int(t), float(cap), float(corr), float(threshold), int(seed)

cell = R.find_cell(DATA, t, cap, corr)
live = _live(t, cap, corr, threshold, seed)

# ---------------------------------------------------------------------------------------------------
# Hauptansicht (Kernabschnitt ①, live: eine Instanz)
# ---------------------------------------------------------------------------------------------------
st.markdown("## ✈️ Welche Buchungen werden angenommen?")
st.caption(f"Live-Instanz (eine Buchungsfolge): Seed {seed}, T = {t}, Gewichtslimit {cap:.0f} kg, "
           f"Korrelation {corr:g}, Preisschwelle {fmt_num(threshold, 1)} EUR/kg. Alle drei Regeln laufen bei "
           "jeder Einstellung neu; die DP-Wertfunktion hängt nur von T/Gewichtslimit/Korrelation ab und wird "
           "nur bei deren Änderung neu berechnet (Millisekunden). Eine einzelne Instanz – die vorgerechnete "
           "Messreihe unten trägt die Aussage.")

st.plotly_chart(V.timeline_figure(live["requests"], live["accepted"]), width="stretch", key="main_timeline")
st.plotly_chart(V.capacity_figure(live["requests"], live["accepted"], cap), width="stretch", key="main_capacity")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Umsatz FCFS", f"{live['revenue']['fcfs']:.0f} EUR")
k2.metric("Umsatz feste Schwelle", f"{live['revenue']['threshold']:.0f} EUR")
k3.metric("Umsatz DP-Regel", f"{live['revenue']['dp']:.0f} EUR")
k4.metric("Auslastung DP-Regel (Ende)", fmt_pct(live["utilization"]["dp"]))
st.caption(f"Auslastung am Ende – FCFS {fmt_pct(live['utilization']['fcfs'])}, feste Schwelle "
           f"{fmt_pct(live['utilization']['threshold'])}, DP-Regel {fmt_pct(live['utilization']['dp'])}. "
           f"Angenommene Buchungen – FCFS {live['n_accepted']['fcfs']}, feste Schwelle "
           f"{live['n_accepted']['threshold']}, DP-Regel {live['n_accepted']['dp']} (von {t}).")

st.info(R.judgment_text(cell))
st.caption("Ehrliche Grenze: eine Buchungsfolge zeigt nur einen von 150 möglichen Zufallsfällen; die "
           "Meldung oben stützt sich auf die Messreihe (150 Instanzen dieser Zelle), nicht auf diese eine Instanz.")

pdf_slot = st.container()

st.markdown("---")

# ---------------------------------------------------------------------------------------------------
# Kernabschnitt ② (vorgerechnet): was die Messreihe zeigt
# ---------------------------------------------------------------------------------------------------
st.markdown("### 📐 Was die Messreihe über 150 Instanzen je Zelle zeigt")
st.markdown(
    """
Kernfrage: wie viel Umsatz kostet FCFS gegenüber der DP-Regel, wie viel holt eine feste Preisschwelle davon
zurück, und wie verändert sich das mit der Restzeit? Die Antwort steht auf **150 Instanzen je Zelle**
(18 Zellen: Restzeit × Gewichtslimit × Korrelation), vorgerechnet und **nie live** gerechnet. Gezeigt wird die
exakt gemessene Zelle Ihrer Einstellung (die drei Sweep-Regler bilden genau die drei Sweep-Dimensionen ab,
keine Näherung nötig); die Preisschwelle ist dabei immer die gemessene Mitte des Preisbereichs (7 EUR/kg).
"""
)

st.markdown("**1 · Rückstand über die Restzeit** (festes Gewichtslimit/Korrelation Ihrer Einstellung)")
t_rows = R.time_rows(DATA, cap, corr)
st.plotly_chart(V.gap_over_time_figure(t_rows), width="stretch", key="core_gap")
st.caption("FCFS liegt bei jeder Restzeit weit zurück (mit mehr Buchungsgelegenheiten eher noch weiter); die feste "
           "Schwellenregel holt das meiste zurück, wird aber in den meisten Zellen mit mehr Buchungsgelegenheiten "
           "schwächer, weil eine starre Schwelle nicht auf die mit der Zeit wachsende Restwert-Information reagiert.")

st.markdown("**2 · Weniger Auslastung, mehr Umsatz** – der Kern-Befund dieser Zelle")
ug = R.utilization_gap_cell(DATA, t, cap, corr)
c1, c2 = st.columns([2, 3])
with c1:
    st.metric("Auslastung FCFS (Mittel)", fmt_pct(ug["util_fcfs"]))
    st.metric("Auslastung DP-Regel (Mittel)", fmt_pct(ug["util_dp"]), delta=fmt_pct(ug["util_dp"] - ug["util_fcfs"]),
              delta_color="inverse")
with c2:
    st.markdown(f"Bei T = {t}, {cap:.0f} kg, Korrelation {corr:g} erreicht die DP-Regel im Mittel "
                f"**{ug['rev_dp']:.0f} EUR** Umsatz gegenüber **{ug['rev_fcfs']:.0f} EUR** bei FCFS – bei "
                f"**niedrigerer** Auslastung ({fmt_pct(ug['util_dp'])} gegen {fmt_pct(ug['util_fcfs'])}). Die "
                "DP-Regel hält bewusst Kapazität für später erwartete, besser bezahlte Anfragen zurück, statt "
                "sie sofort zu füllen – der klassische Yield-Management-Effekt, hier mit Gewicht statt Sitzplätzen.")

st.markdown("**3 · Regime** – Rückstand beider einfachen Regeln über alle 18 gemessenen Zellen")
regime = R.regime_rows(DATA)
st.dataframe(
    {
        "T": [r["T"] for r in regime], "Gewichtslimit (kg)": [f"{r['cap']:.0f}" for r in regime],
        "Korrelation": [r["corr"] for r in regime],
        "Rückstand FCFS": [fmt_num(r["gap_fcfs_pct"], 1) + " %" for r in regime],
        "Rückstand feste Schwelle": [fmt_num(r["gap_th_mid_pct"], 1) + " %" for r in regime],
        "Auslastung FCFS": [fmt_pct(r["util_fcfs_mean"]) for r in regime],
        "Auslastung DP-Regel": [fmt_pct(r["util_dp_mean"]) for r in regime],
    },
    width="stretch", hide_index=True, height=360,
)
fcfs_sum, th_sum = R.fcfs_gap_summary(DATA), R.threshold_mid_gap_summary(DATA)
st.caption(f"Über alle 18 Zellen: FCFS-Rückstand im Mittel {fmt_num(fcfs_sum['mean'], 1)} % (Minimum "
           f"{fmt_num(fcfs_sum['min'], 1)} %, Maximum {fmt_num(fcfs_sum['max'], 1)} %); Rückstand der festen "
           f"Preisschwelle im Mittel {fmt_num(th_sum['mean'], 1)} % (Minimum {fmt_num(th_sum['min'], 1)} %, "
           f"Maximum {fmt_num(th_sum['max'], 1)} %).")

with pdf_slot:
    st.download_button(
        "📄 Buchungsannahme als PDF herunterladen",
        data=generate_uldb2_pdf(dict(t=t, cap=cap, corr=corr, threshold=threshold, seed=seed), live, cell),
        file_name="uld_buchungsannahme.pdf", mime="application/pdf", key="primary_pdf_download",
        help="Einstellungen, Kennzahlen aller drei Regeln und die Anfrageliste der gezeigten Instanz.")

st.markdown("---")

# ---------------------------------------------------------------------------------------------------
# Ansichten
# ---------------------------------------------------------------------------------------------------
with st.expander("🔧 Wie wir das erreichen – vollständiger Methodenvergleich"):
    tabs = st.tabs(["📅 Zeitleiste", "📊 Regeln", "📈 Messreihe"])
    with tabs[0]:
        st.markdown("Alle drei Regeln auf **dieser** Instanz: gefülltes Quadrat = angenommen, hohles Quadrat "
                     "= abgelehnt, Kapazitätsverlauf darunter.")
        st.plotly_chart(V.timeline_figure(live["requests"], live["accepted"]), width="stretch", key="tab_timeline")
        st.plotly_chart(V.capacity_figure(live["requests"], live["accepted"], cap), width="stretch", key="tab_capacity")
    with tabs[1]:
        st.markdown("Alle drei Regeln auf **dieser** Instanz, Kennzahlen nebeneinander:")
        st.dataframe(
            {
                "Kennzahl": ["Umsatz (EUR)", "Angenommene Buchungen", "Auslastung"],
                "FCFS": [f"{live['revenue']['fcfs']:.0f}", str(live['n_accepted']['fcfs']), fmt_pct(live['utilization']['fcfs'])],
                "Feste Schwelle": [f"{live['revenue']['threshold']:.0f}", str(live['n_accepted']['threshold']), fmt_pct(live['utilization']['threshold'])],
                "DP-Regel": [f"{live['revenue']['dp']:.0f}", str(live['n_accepted']['dp']), fmt_pct(live['utilization']['dp'])],
            },
            width="stretch", hide_index=True,
        )
        st.caption(f"Zum Vergleich die Messreihe dieser Zelle (150 Instanzen): {R.judgment_text(cell)}")
    with tabs[2]:
        st.markdown("Alle 18 gemessenen Zellen als Tabelle (Restzeit, Gewichtslimit, Korrelation, Rückstand "
                     "beider einfachen Regeln, Auslastung):")
        st.dataframe(
            {
                "T": [r["T"] for r in regime], "Gewichtslimit (kg)": [f"{r['cap']:.0f}" for r in regime],
                "Korrelation": [r["corr"] for r in regime],
                "Rückstand FCFS": [fmt_num(r["gap_fcfs_pct"], 1) + " %" for r in regime],
                "Rückstand feste Schwelle": [fmt_num(r["gap_th_mid_pct"], 1) + " %" for r in regime],
                "Rückstand Schwelle nahe Preisuntergrenze": [fmt_num(r["gap_th_low_pct"], 1) + " %" for r in regime],
                "Auslastung FCFS": [fmt_pct(r["util_fcfs_mean"]) for r in regime],
                "Auslastung DP-Regel": [fmt_pct(r["util_dp_mean"]) for r in regime],
            },
            width="stretch", hide_index=True, height=360,
        )
        st.plotly_chart(V.gap_over_time_figure(R.time_rows(DATA, cap, corr)), width="stretch", key="tab_gap")

with st.expander("Wie funktioniert diese Demo?"):
    st.markdown(
        f"""
**Instanz.** T Buchungsanfragen ({', '.join(str(v) for v in C.T_OPTIONS)}) treffen nacheinander ein, jede mit
Gewicht ~ U({C.WEIGHT_RANGE[0]:.0f}; {C.WEIGHT_RANGE[1]:.0f} kg) und Preis je kg ~ U({C.PRICE_RANGE[0]:.0f};
{C.PRICE_RANGE[1]:.0f} EUR/kg), das bei wachsender Korrelation mit steigendem Gewicht sinkt (Massengut ist
typischerweise günstiger je kg). Das Gewichtslimit ({', '.join(f'{v:.0f}' for v in C.CAP_OPTIONS)} kg) ist die
einzige Ressource, jede Annahme verbraucht ihr Gewicht unwiderruflich, sofortige Entscheidung ohne Kenntnis
künftiger Anfragen (online).

**Die Regeln.** **FCFS:** annehmen, solange es gewichtsmäßig passt, unabhängig vom Preis. **Feste
Preisschwelle:** annehmen, wenn es passt UND der Preis je kg über der eingestellten Schwelle liegt – kennt
weder Restzeit noch künftige Nachfrage. **DP-Regel (Bid-Price):** exakte Rückwärtsrechnung über ein
diskretisiertes Kapazitätsgitter ({int(CAP_STEP)}-kg-Schritte) und ein Gewichts-/
Preisgitter für die bekannte, stationäre Anfrageverteilung; nimmt an, wenn der Preis den Bid-Price (Grenzwert
der Restkapazität) übersteigt. Die Zulässigkeit selbst wird immer gegen die **echte** Restkapazität geprüft,
nicht gegen das Gitter.

**Warum FCFS so viel Umsatz verliert.** FCFS nimmt frühe, oft niedrigpreisige Anfragen an und hat dann keinen
Platz mehr für spätere, besser bezahlte – ohne jede Rücksicht auf den Preis.

**Warum eine feste Preisschwelle mit mehr Restzeit schwächer wird.** Je mehr Buchungsgelegenheiten kommen,
desto mehr lohnt es sich, den Bid-Price mit der Zeit anzupassen statt fest zu halten – eine starre Schwelle
reagiert nicht auf die wachsende Restwert-Information.

**Warum die DP-Regel mehr Umsatz bei WENIGER Auslastung erreicht.** Sie hält bewusst Kapazität für später
erwartete, besser bezahlte Anfragen zurück, statt sie sofort zu füllen – der klassische Yield-Management-
Effekt, hier mit Gewicht statt Sitzplätzen.

**Verhältnis zu `revenue-management-demo`.** Dort verbraucht jede Buchung genau **eine** diskrete
Kapazitätseinheit (zwei Frachtklassen), die geschlossene Littlewood-Formel liefert die optimale Regel. Hier
hat jede Buchung ihr **eigenes, zufälliges Gewicht** – ein Online-Rucksackproblem statt einer
Klassenschutz-Frage mit Einheitsnachfrage; die Littlewood-Formel funktioniert dafür nicht, die DP-Regel über
ein Kapazitätsgitter ersetzt sie.

**Grenzen dieses Modells** (bewusst so gewählt, damit die Aussage ehrlich bleibt):

- Anfrageverteilung ist bekannt und stationär (kein Prognosefehler) – wie bei `revenue-management-demo`.
- Nur ein Gewichtslimit, keine parallele Volumengrenze (reale Luftfracht ist oft volumen- UND
  gewichtslimitiert, je nachdem was zuerst bindet).
- Kein Overbooking/No-Show.
- Preis- und Gewichtsverteilung erfunden, nicht kalibriert.
- Das Kapazitätsgitter ist eine Diskretisierungs-Näherung; die Brute-Force-Referenz bestätigt sie nur auf
  einem winzigen Beispiel, nicht in voller Auflösung.
- **Nicht Teil dieser Demo:** Overbooking/No-Show, parallele Volumengrenze, Prognoseunschärfe der Nachfrage,
  Kalibrierung an echten Buchungsdaten, dynamische Preisanpassung.
        """
    )

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Bellman-Gleichung.** $V(t, c) = \mathbb{E}\big[\max\big(V(t+1, c),\; \text{Preis} + V(t+1, c - \text{Gewicht})\big)\big]$ - der Erwartungswert läuft über alle Anfragen (Gewichts-/Preisstufen); eine Anfrage mit Gewicht $> c$ kann nicht angenommen werden und trägt $V(t+1, c)$ bei.

**Bid-Price** zum Zeitpunkt $t$ bei Restkapazität $c$: $\beta(t, c) = V(t+1, c) - V(t+1, c - \text{Gewichtsstufe})$

**Annahmeregel:** annehmen $\iff$ Preis $\ge \beta(t, c)$ und Gewicht $\le c$ (echte, nicht diskretisierte
Restkapazität).

Implementiert in `uldb2_model.py` (Anfragemodell, FCFS, feste Preisschwelle) und `uldb2_dp.py`
(DP-Rückwärtsrechnung, Bid-Price-Regel).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zum Thema: [Luftfracht optimieren](https://sebastianhanisch.net/luftfracht-optimierung.html)."
)
