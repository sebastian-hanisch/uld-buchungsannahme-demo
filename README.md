# ✈️ Buchungsannahme mit Gewichtslimit

*(noch nicht deployed)*

Eigenständiges Luftfracht-Stück, geschärft gegenüber [`revenue-management-demo`](https://github.com/sebastian-hanisch/revenue-management-demo)
(dort: zwei Frachtklassen, **jede** Buchung verbraucht genau **eine** diskrete Kapazitätseinheit, geschlossene
Littlewood-Formel). Hier verbraucht jede Buchungsanfrage ein **zufälliges Gewicht** aus einem gemeinsamen
Gewichtslimit - ein Online-Rucksackproblem (Bid-Price-Kontrolle), für das die Littlewood-Formel nicht
funktioniert, weil es keine feste Einheitengröße gibt; eine dynamische Programmierung (DP) über ein
Kapazitätsgitter ersetzt sie. Die Demo zeigt live **eine Instanz** mit drei Regeln (FCFS, feste
Preisschwelle, DP-Regel - hier immer alle drei gerechnet) und vorgerechnet die Messreihe über
**150 Instanzen je Zelle** (18 Zellen), die die Aussage trägt.

## Warum dieses Problem

Luftfracht-Buchungen unterscheiden sich in einem wichtigen Punkt von Sitzplatz- oder Kabinen-Buchungen:
jede Sendung hat ihr **eigenes Gewicht**, nicht eine feste Einheitengröße. `revenue-management-demo` löst
die klassische Zwei-Klassen-Buchungsannahme (Spot/Premium), bei der jede Buchung genau eine diskrete
Kapazitätseinheit verbraucht - dafür liefert die geschlossene Littlewood-Formel die optimale Schwelle direkt.
Bei Luftfracht verbraucht jede Buchung ein zufälliges Gewicht aus einem gemeinsamen Gewichtslimit: ein
Online-Rucksackproblem statt einer Klassenschutz-Frage mit Einheitsnachfrage. Die Littlewood-Formel
funktioniert dafür strukturell nicht - dieses Stück ersetzt sie durch eine dynamische Programmierung
(Bid-Price-Kontrolle) über ein diskretisiertes Kapazitätsgitter.

## Modell

- **T Buchungsanfragen** (15/25/40) treffen nacheinander ein, jede mit Gewicht ~ U(200; 2.000 kg) und einem
  Preis je kg ~ U(2; 12) EUR/kg, der bei wachsender Preis-Gewicht-Korrelation (Regler, 0/0,3/0,6) mit
  steigendem Gewicht sinkt (Massengut ist typischerweise günstiger je kg als kleine, eilige Sendungen).
- **Gewichtslimit** (1.500 / 2.500 kg) ist die einzige Ressource; jede Annahme verbraucht ihr Gewicht
  unwiderruflich, **sofortige** Entscheidung ohne Kenntnis künftiger Anfragen (online).
- **FCFS:** annehmen, solange es gewichtsmäßig passt, unabhängig vom Preis.
- **Feste Preisschwelle:** annehmen, wenn es passt UND der Preis je kg über einer festen Schwelle liegt - ein
  reiner Live-Regler (2-12 EUR/kg), unabhängig von der Messreihe, die zwei feste Schwellen misst (Mitte des
  Preisbereichs, 7 EUR/kg, und die Preisuntergrenze, 2 EUR/kg, praktisch FCFS).
- **DP-Regel (Bid-Price):** exakte Rückwärtsrechnung über ein diskretisiertes Kapazitätsgitter
  (50-kg-Schritte) und ein Gewichts-/Preisgitter für die bekannte, stationäre Anfrageverteilung; nimmt an,
  wenn der Preis den Bid-Price (Grenzwert der Restkapazität) übersteigt. Die Zulässigkeit selbst wird immer
  gegen die **echte** Restkapazität geprüft, nicht gegen das Gitter (siehe "Beim Bauen der Vorab-Messreihe
  gefunden" unten).

Anfrageverteilung ist bekannt und stationär (kein Prognosefehler, wie bei `revenue-management-demo`); Preis-
und Gewichtsverteilung erfunden, nicht kalibriert; nur ein Gewichtslimit, keine parallele Volumengrenze; kein
Overbooking/No-Show.

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen aus `data/uldb2_results.json` (18 Zellen × 150 Instanzen, aus
`packen-planung/messreihe_uld_buchung/sweep_data.json`, bitgleich übernommen, siehe `tools/sweep.py` und
`tools/check_full.py`), nachgerechnet in `tests/test_claims.py`.

| Frage | Befund |
|---|---|
| Wie viel Umsatz verliert FCFS? | Viel, und konsistent über alle 18 Zellen: im Mittel **30,4 %** weniger Umsatz als die DP-Regel (Minimum 20,1 %, Maximum 37,0 %). |
| Holt eine feste Preisschwelle (7 EUR/kg) das meiste zurück? | Ja, aber nicht alles: im Mittel nur noch **6,4 %** Rückstand (Minimum 2,7 %, Maximum 14,6 %). |
| Wird die feste Schwelle mit mehr Restzeit schwächer? | Ja: bei 2.500 kg/Korrelation 0,3 wächst ihr Rückstand von **3,5 %** (T = 15) über **6,7 %** (T = 25) auf **9,3 %** (T = 40) - eine starre Schwelle reagiert nicht auf die mit der Zeit wachsende Restwert-Information. |
| Verhält sich eine zu niedrige Schwelle wie FCFS? | Ja: eine Schwelle nahe der Preisuntergrenze (2 EUR/kg) verliert im Mittel **29,5 %** - fast identisch mit FCFS (30,4 %); die Wahl der Schwelle ist der Hebel, nicht ihr bloßes Vorhandensein. |
| Erreicht die DP-Regel mehr Umsatz bei WENIGER Auslastung? | Ja - der Kern-Befund: bei T = 25, 2.500 kg, Korrelation 0,3 liegt die mittlere Auslastung der DP-Regel bei **91,1 %** gegenüber **95,3 %** bei FCFS, bei gleichzeitig höherem Umsatz (21.893 gegenüber 14.860 EUR im Mittel). Die DP-Regel hält bewusst Kapazität für später erwartete, besser bezahlte Anfragen zurück. |
| Ist die Korrelation ein starker Hebel? | Schwächer als die Restzeit: der FCFS-Rückstand bei Korrelation 0/0,3/0,6 (T = 25, 2.500 kg) liegt bei 28,7/32,1/31,1 % - deutlich flacher als der Restzeit-Effekt der Schwellenregel oben. |

**Warum "die DP-Regel erreicht mehr Umsatz bei weniger Auslastung" der zentrale Aufhänger ist:** eine höhere
Auslastung wird oft mit "mehr Erfolg" gleichgesetzt - hier zeigt die Messreihe das Gegenteil: die Regel mit
dem HÖHEREN Umsatz nutzt die Kapazität bewusst NICHT vollständig aus, weil sie Platz für später erwartete,
besser bezahlte Fracht freihält. Der klassische Yield-Management-Effekt, hier mit Gewicht statt Sitzplätzen.

## Beim Bauen der Vorab-Messreihe gefunden

Drei echte Bugs, alle vor dem ersten Sweep-Lauf in `packen-planung/messreihe_uld_buchung/` gefunden und
behoben (siehe dortiges `ERGEBNIS.md`, mechanisch übernommen, nicht erneut aufgetreten):

- **Kapazitätsüberschreitung durch Rundung:** eine frühe Fassung der DP-Regel prüfte die Zulässigkeit gegen
  die gerundete Restkapazität (50-kg-Gitter) statt gegen die echte kontinuierliche Restkapazität - bei
  450 Testläufen überschritt das die Kapazität. Behoben: die Zulässigkeit wird immer gegen die echte
  Restkapazität geprüft, nur der Bid-Price-Vergleich selbst nutzt das Gitter. In diesem Repo als PFLICHT-
  Regressionstest übernommen (`tests/test_model.py::test_dp_regel_prueft_gegen_echte_nicht_gerundete_restkapazitaet`,
  mit einer adversarisch konstruierten Instanz, bei der das Gitter auf einen höheren Wert rundet als die
  echte Restkapazität zulässt).
- **Einheitenfehler in der Brute-Force-Referenz** (nicht im Modell selbst): "Preis je kg" wurde einmal mit
  "Gesamtpreis" verwechselt und lag um den Faktor ~200 daneben - beim Gegenlesen aufgefallen, nicht durch
  einen Test allein.
- **Zu strenge Testerwartung:** ein erster Test verlangte, dass die DP-Regel auf JEDER einzelnen
  Zufallsinstanz mindestens so gut ist wie FCFS/Schwelle - eine falsche Erwartung an eine stochastisch
  optimale Regel (Optimalität gilt im Erwartungswert, nicht pfadweise; 8 von 60 Instanzen unterboten die
  DP-Regel zufällig). Test auf den gepaarten Mittelwert mit Standardfehler umgestellt - in diesem Repo
  identisch übernommen (`tests/test_model.py::test_dp_regel_im_mittel_besser_als_fcfs_und_schwelle`).

## Ehrliche Grenzen

- **Anfrageverteilung ist bekannt und stationär** (kein Prognosefehler) - wie bei `revenue-management-demo`
  Version 1, eine bewusste Vereinfachung.
- **Nur ein Gewichtslimit**, keine parallele Volumengrenze (reale Luftfracht ist oft volumen- UND
  gewichtslimitiert, je nachdem was zuerst bindet - hier nicht modelliert).
- **Kein Overbooking/No-Show** (wie im Schwesterstück explizit ausgeklammert).
- **Das Kapazitätsgitter (50-kg-Schritte) ist eine Diskretisierungs-Näherung** - die Brute-Force-Referenz
  bestätigt sie nur auf einem winzigen, vollständig enumerierten Beispiel, nicht in voller Auflösung.
- **Preis- und Gewichtsverteilung erfunden, nicht kalibriert.**
- **Die Preisschwelle ist ein reiner Live-Regler** ohne eigene Messreihen-Abdeckung - die vorgerechnete
  Messreihe (Kernabschnitt, Regime-Tabelle) bezieht sich immer auf die zwei GEMESSENEN Schwellen (7 und
  2 EUR/kg), unabhängig vom aktuellen Reglerstand.

## Tests

74 Tests, siehe Ausgabe von `_venvs/test/Scripts/python.exe -m pytest tests -v` (Laufzeit rund 10 s):

- `tests/test_model.py` - die 12 Korrektheits-Checks aus `messreihe_uld_buchung/check.py` (Handrechnung,
  Kapazitätsgrenze über 450 Läufe, Schwellenregel-Einhaltung, Nullkapazität, DP-Wertfunktion monoton in
  Kapazität und Restzeit, Randbedingung V[T]=0, T=1-Grenzfall, Brute-Force-Referenz auf einem winzigen
  vollständig enumerierten Gitter, DP im Mittel signifikant besser [>2 Standardfehler, NICHT pfadweise],
  Regressionstest gegen wirkungslose Schwellen, Determinismus), PLUS den PFLICHT-Kapazitäts-Regressionstest
  (echte gegen gerundete Restkapazität) und sieben gezielte Epsilon-/Grenzfall-Tests (siehe Fehler-Einbau-Test
  unten).
- `tests/test_frozen_reference.py` - vier eingefrorene Anfragefolgen (feste Gewicht-/Preis-Zahlen, keine
  Zufallsziehung zur Testzeit), CI-robust gegen NumPy-Versionsdrift.
- `tests/test_results.py` - Zell-Zuordnung (AP 0: alle 18 Reglerkombinationen liegen exakt auf einer
  gemessenen Zelle), abgeleitete Kennzahlen, Meldungstext.
- `tests/test_presets.py`, `tests/test_stories.py` - Permalink-Parsing (Begrenzen/Einrasten der Stufenregler,
  Klemmen des kontinuierlichen Schwellenreglers), alle fünf Presets bestehen ihre Abnahmekriterien gegen die
  Messreihe.
- `tests/test_visualization.py`, `tests/test_pdf_export.py` - Plotly-Figuren und PDF-Export bauen ohne
  Fehler.
- `tests/test_claims.py` - jede Zahl aus dem README-Abschnitt "Befunde" gegen `data/uldb2_results.json`
  nachgerechnet.
- `tests/test_app.py` - AppTest: Skelett, Footer, jedes Preset, Permalink, alle Regler an Min/Max, ein
  Regressionstest gegen einen wirkungslosen Preisschwellen-Regler, PDF-Download, keine toten Datei-Links,
  echte Umlaute im sichtbaren Text.

Zusätzlich: `tools/mutation_check.py` (Fehler-Einbau-Test für `uldb2_model.py`/`uldb2_dp.py`, 18 handverlesene
Mutanten, siehe `tools/mutants.py`; nach zwei nachgezogenen Testlücken-Runden 18/18 gefunden, 0 überlebt,
reproduzierbar sowohl mit vier parallelen Jobs als auch sequenziell) und `tools/check_full.py` (volles
Bau-Gate: Wiederholung der Messreihe gegen `data/uldb2_results.json` - hier **bitgleich**, weil die
Zellen-Seeds über `zlib.crc32` statt Pythons prozess-gesalzenem `hash()` erzeugt werden, siehe
`tools/sweep.py`).

## Dateistruktur

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Einstiegspunkt |
| `uldb2_constants.py` | Reglerstufen, Presets, Farben, feste Annahmen |
| `uldb2_presets.py` | Reglerspezifikation, Permalink, Presets, Seed-Knopf |
| `uldb2_model.py` | `Request`, `make_requests`, `revenue_of`, `policy_fcfs`, `policy_threshold` (aus `messreihe_uld_buchung/buchung.py` mechanisch übernommen, Logik unverändert) |
| `uldb2_dp.py` | `dp_value_function`, `policy_dp`, `CAP_STEP` (aus `buchung.py` mechanisch übernommen, Logik unverändert) |
| `uldb2_results.py` | Laden und Auswerten von `data/uldb2_results.json` (18 Zellen) |
| `uldb2_visualization.py` | Zeitleiste, Kapazitätsverlauf (Flächendiagramm), Rückstand-über-Restzeit-Grafik |
| `uldb2_stories.py` | Abnahmekriterien der fünf Presets |
| `uldb2_pdf_export.py` | Buchungsannahme-Bericht als PDF |
| `uldb2_format.py` | Zahlenformate mit deutschem Dezimalkomma |
| `tools/sweep.py` | Reproduktion der Messreihe (nicht in CI) |
| `tools/check_full.py` | Volles Bau-Gate (bitgleicher Vergleich) |
| `tools/gen_frozen_reference.py` | Ursprung von `tests/data/uldb2_frozen.json` (nicht in CI) |
| `tools/mutants.py`, `tools/mutation_check.py` | Fehler-Einbau-Test der Kernmodule |
| `data/uldb2_results.json` | Messreihe: 18 Zellen × 150 Instanzen |
| `tests/` | Testsuite |

## Bewusst nicht umgesetzt

Overbooking/No-Show, eine parallele Volumengrenze, Prognoseunschärfe der Nachfrage, Kalibrierung an echten
Buchungsdaten, dynamische Preisanpassung der festen Schwelle, eine Messreihen-Abdeckung der Preisschwelle
(reiner Live-Regler) - teils identisch mit den offenen Punkten von `revenue-management-demo`.

## Lokal ausführen

```
pip install -r requirements-dev.txt
streamlit run app.py
```

---

Gebaut mit Streamlit, Plotly, NumPy und fpdf2.
