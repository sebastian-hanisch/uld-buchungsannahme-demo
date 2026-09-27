"""Buchungsannahme mit Gewichtslimit - Plotly-Figuren.

Zeitleiste der Buchungsanfragen (Annahme/Ablehnung je Regel), Kapazitätsverlauf als Flächendiagramm, und
die vorgerechnete Rückstand-über-Restzeit-Grafik. Alle Achsen `fixedrange` (Touch-Scrollen soll nicht am
Chart hängen bleiben, siehe DEMO-PLAYBOOK Abschnitt 3)."""
from __future__ import annotations

from uldb2_constants import COLOR_DP, COLOR_FCFS, COLOR_THRESHOLD

POLICY_LABEL = {"fcfs": "FCFS", "threshold": "Feste Preisschwelle", "dp": "DP-Regel (Bid-Price)"}
POLICY_COLOR = {"fcfs": COLOR_FCFS, "threshold": COLOR_THRESHOLD, "dp": COLOR_DP}
POLICIES = ("fcfs", "threshold", "dp")


def timeline_figure(requests: list, accepted_by_policy: dict[str, list[bool]]):
    """Eine Zeile je Regel, x = Buchungsindex. Gefülltes Quadrat = angenommen, hohles Quadrat = abgelehnt;
    Marker-Größe skaliert leicht mit dem Gewicht der Anfrage."""
    import plotly.graph_objects as go

    fig = go.Figure()
    n = len(requests)
    xs = list(range(1, n + 1))
    w_lo = min(r.weight_kg for r in requests) if requests else 0.0
    w_hi = max(r.weight_kg for r in requests) if requests else 1.0
    w_span = max(w_hi - w_lo, 1e-9)

    def marker_size(w):
        return 9.0 + 9.0 * (w - w_lo) / w_span

    for row, policy in enumerate(POLICIES):
        y = len(POLICIES) - 1 - row
        accepted = accepted_by_policy[policy]
        for accept_state in (True, False):
            idx = [i for i in range(n) if accepted[i] == accept_state]
            if not idx:
                continue
            fig.add_trace(go.Scatter(
                x=[xs[i] for i in idx], y=[y] * len(idx), mode="markers",
                marker=dict(symbol="square" if accept_state else "square-open",
                            size=[marker_size(requests[i].weight_kg) for i in idx],
                            color=POLICY_COLOR[policy], line=dict(width=2, color=POLICY_COLOR[policy])),
                name=f"{POLICY_LABEL[policy]}, {'angenommen' if accept_state else 'abgelehnt'}",
                legendgroup=f"{policy}_{accept_state}", showlegend=row == 0,
                hovertext=[f"Anfrage {xs[i]}: {requests[i].weight_kg:.0f} kg, "
                           f"{requests[i].price / requests[i].weight_kg:.2f} EUR/kg, "
                           f"{'angenommen' if accept_state else 'abgelehnt'}" for i in idx],
                hoverinfo="text",
            ))
    fig.update_layout(
        height=110 + 55 * len(POLICIES), margin=dict(l=10, r=10, t=20, b=40),
        xaxis=dict(title="Buchungsanfrage (Ankunftsreihenfolge)", range=[0.3, n + 0.7], fixedrange=True),
        yaxis=dict(tickmode="array", tickvals=list(range(len(POLICIES))),
                    ticktext=[POLICY_LABEL[p] for p in POLICIES][::-1],
                    range=[-0.6, len(POLICIES) - 0.4], fixedrange=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig


def capacity_figure(requests: list, accepted_by_policy: dict[str, list[bool]], capacity_kg: float):
    """Restkapazität über die Buchungsreihenfolge je Regel, als Flächendiagramm."""
    import plotly.graph_objects as go

    fig = go.Figure()
    n = len(requests)
    xs = [0] + list(range(1, n + 1))
    for policy in POLICIES:
        accepted = accepted_by_policy[policy]
        remaining = capacity_kg
        ys = [remaining]
        for r, a in zip(requests, accepted):
            if a:
                remaining -= r.weight_kg
            ys.append(remaining)
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", name=POLICY_LABEL[policy],
            line=dict(color=POLICY_COLOR[policy], width=2, shape="hv"),
            fill="tozeroy" if policy == "dp" else None,
            fillcolor="rgba(61,139,95,0.08)" if policy == "dp" else None,
            hovertemplate=f"{POLICY_LABEL[policy]}<br>nach Anfrage %{{x}}: %{{y:.0f}} kg Restkapazität<extra></extra>",
        ))
    fig.update_layout(
        height=320, margin=dict(l=10, r=10, t=20, b=40),
        xaxis=dict(title="Buchungsanfrage (Ankunftsreihenfolge)", range=[0, n], fixedrange=True),
        yaxis=dict(title="Restkapazität (kg)", range=[0, capacity_kg * 1.05], fixedrange=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig


def gap_over_time_figure(rows: list[dict]):
    """Rückstand von FCFS und fester Preisschwelle (Mitte des Preisbereichs) über die Restzeit T."""
    import plotly.graph_objects as go

    xs = [f"T = {r['T']}" for r in rows]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=xs, y=[r["gap_fcfs_pct"] for r in rows], name="Rückstand FCFS",
                          marker_color=COLOR_FCFS, text=[f"{r['gap_fcfs_pct']:.1f} %" for r in rows], textposition="outside"))
    fig.add_trace(go.Bar(x=xs, y=[r["gap_th_mid_pct"] for r in rows], name="Rückstand feste Preisschwelle (7 EUR/kg)",
                          marker_color=COLOR_THRESHOLD, text=[f"{r['gap_th_mid_pct']:.1f} %" for r in rows], textposition="outside"))
    fig.update_layout(
        barmode="group", height=340, margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(title="Restzeit (Buchungsgelegenheiten)", fixedrange=True),
        yaxis=dict(title="Rückstand zur DP-Regel (%)", range=[0, 42], fixedrange=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig
