"""Erzeugt einen downloadbaren Buchungsannahme-Bericht als PDF (in-memory, kein Zwischenspeichern auf Disk):
Einstellungen, Kennzahlen aller drei Regeln, die Meldung der gezeigten Zelle und die Anfrageliste mit
Annahme-Entscheidung je Regel.

fpdf2-Fallstricke (siehe DEMO-PLAYBOOK Abschnitt 7): echte Umlaute sind in den Kernschriften unproblematisch,
Gedankenstrich (-) und Euro-Zeichen (EUR statt Symbol) vermeiden."""
import time

from uldb2_format import fmt_num, fmt_pct


def generate_uldb2_pdf(settings: dict, live: dict, cell: dict) -> bytes:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Buchungsannahme mit Gewichtslimit", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Erstellt: {time.strftime('%d.%m.%Y %H:%M')} Uhr", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Einstellungen", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Restzeit T = {settings['t']}, Gewichtslimit {settings['cap']:.0f} kg, "
                    f"Preis-Gewicht-Korrelation {settings['corr']:g}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Preisschwelle {settings['threshold']:.1f} EUR/kg, Seed {settings['seed']}",
              new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Kennzahlen aller drei Regeln (diese Instanz)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(235, 235, 235)
    headers = ["Kennzahl", "FCFS", "Feste Schwelle", "DP-Regel"]
    widths = [55, 45, 45, 45]
    for h, w in zip(headers, widths):
        pdf.cell(w, 7, h, border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.ln(7)
    pdf.set_font("Helvetica", "", 9)
    rows = [
        ("Umsatz (EUR)", f"{live['revenue']['fcfs']:.0f}", f"{live['revenue']['threshold']:.0f}", f"{live['revenue']['dp']:.0f}"),
        ("Angenommene Buchungen", str(live['n_accepted']['fcfs']), str(live['n_accepted']['threshold']), str(live['n_accepted']['dp'])),
        ("Auslastung", fmt_pct(live['utilization']['fcfs']), fmt_pct(live['utilization']['threshold']), fmt_pct(live['utilization']['dp'])),
    ]
    for row in rows:
        for val, w in zip(row, widths):
            pdf.cell(w, 6, val, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.ln(6)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Messreihe (150 Instanzen dieser Zelle)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, f"FCFS verliert im Mittel {fmt_num(cell['gap_fcfs_pct'], 1)} % Umsatz gegenüber der "
                         f"DP-Regel, eine feste Preisschwelle von 7 EUR/kg nur {fmt_num(cell['gap_th_mid_pct'], 1)} %.")
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Anfrageliste mit Annahme-Entscheidung je Regel", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(235, 235, 235)
    headers2 = ["#", "Gewicht (kg)", "Preis/kg (EUR)", "FCFS", "Schwelle", "DP-Regel"]
    widths2 = [15, 35, 35, 30, 30, 30]
    for h, w in zip(headers2, widths2):
        pdf.cell(w, 7, h, border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.ln(7)
    pdf.set_font("Helvetica", "", 9)
    requests = live["requests"]
    acc = live["accepted"]
    for i, r in enumerate(requests):
        row2 = [str(i + 1), f"{r.weight_kg:.0f}", f"{r.price / r.weight_kg:.2f}",
                "ja" if acc["fcfs"][i] else "nein", "ja" if acc["threshold"][i] else "nein",
                "ja" if acc["dp"][i] else "nein"]
        for val, w in zip(row2, widths2):
            pdf.cell(w, 6, val, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.ln(6)

    return bytes(pdf.output())
