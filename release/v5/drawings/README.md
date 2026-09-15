# V5-Montagezeichnungen

Die 15 PNG-Dateien E01–E15 sind mit 2400 × 1680 Pixeln aus den aktuellen
CadQuery-Volumenkörpern berechnet. Alle sechs Anleitungen verwenden dieselben
englisch beschrifteten Figuren mit nummerierten Bauteilmarkierungen und einer
gemeinsamen Bewegungslegende.
`figures.json` enthält Bild-ID, Dateiname, Bildunterschrift, Alternativtext,
Beschriftungen, explizite 3D-Merkmalsanker und 2D-Markierungsversätze, Pixelmaße,
CAD-Quellen, Bewegungszuordnung und dargestellte Grenzen. Bauteildatensätze enthalten
zusätzlich Druckbarkeit, Referenzhinweise und gegebenenfalls die Einschraubrichtung.
Die SHA-256 des verwendeten V5-Manifests steht im Kopf des Bildinventars.
Vor dem CAD-Aufbau vergleicht der Renderer die normalisierten angeforderten
Geometrieparameter mit diesem Manifest und weist Abweichungen zurück.

Erneut erzeugen, aus dem Repository-Verzeichnis mit aktivierter Python-Umgebung:

```powershell
$env:PYTHONPATH = '.;src'
python scripts/run_geometry.py -m scripts.manual.v5_figures
```

Eine andere Ausgabe wird mit `--output-dir build/v5-drawings` erzeugt. Der Renderer
importiert keine alten Zeichnungsbilder und ändert keine CAD-Bauteile. Die
Geometrie wird orthografisch projiziert; Schnitte entstehen durch CAD-Booleans.
Die Belichtung und Sortierung der Dreiecke sind deterministisch. Die seitliche
Beschriftung ist über Nummern mit dem Modell verbunden, ohne kreuzende Maßlinien.

| ID | Inhalt |
| --- | --- |
| E01 | Siebenstufiger Rotor, axial getrennte Vormontage |
| E02 | Base, Standard und Top mit glatten bündigen Blattenden |
| E03 | Zentrales Bajonett als einzige formschlüssige Drehmomentschnittstelle |
| E04 | Base-Schulter, M8-Mutter und getrennte 51105-Lagerteile im Schnitt |
| E05 | Unterer Magnetrotor im Gehäuse und Mittelschnitt mit planer 5-mm-Druckfläche, erhöhter unten offener M8-Tasche und oberer integrierter Hülse |
| E06 | Generator-Explosion mit unterem Rotor im Gehäuse unter der Wicklung |
| E07 | Montierter Generator im Mittelschnitt |
| E08 | Kassettenführung, Verdrehsicherung und axiale Rückhaltung |
| E09 | Deckel mit vier M4-Schrauben und gefangenen Muttern |
| E10 | Seitlicher Kabeldurchgang bei 45 Grad |
| E11 | Getrennte 51105-Außensitz- und 25-mm-Pilot-Coupons des Releases |
| E12 | 608-Lagersitz-Coupon mit drei Durchmessern |
| E13 | Oberer Halter: Schrauben von unten ins Holz; montierter Lagerschnitt |
| E14 | Einbau zwischen zwei Holzriegeln und Schnitt durch den unteren Laschenanschluss |
| E15 | Gesamtbaugruppe zwischen zwei Holzriegeln und Generator-Einbaudetail |

Ocker bedeutet rotierend, Türkis stationär. Violett kennzeichnet den separat
bewegten 51105-Wälzbereich beziehungsweise die unaufgelöste 608-Lagerhülle.
Grau kennzeichnet Prüf- oder Freiraumreferenzen. Das Holz ist als stationäre
CAD-Referenz grau dargestellt. Schrauben, Magnete, Wicklung und Lager
sind Nennhüllen. Es werden weder Gewinde noch elektrische Wicklungsdetails behauptet.
Magnete sind im rotierenden Ocker dunkler, der Wicklungsraum im stationären Türkis
heller dargestellt, damit ihre bündigen Grenzflächen erkennbar bleiben.
E06/E07 zeigen zusätzlich je 18 alternierende N/S-Polflächen beider Ringe in
derselben +Z-Projektion, 0 Grad rechts und 90 Grad oben. Beschriftet sind die zur
Wicklung gerichteten Flächen: oben nach unten, unten nach oben. Bei gleichem Winkel
stehen sich N und S gegenüber. Die Polbeschriftung verwendet keine zusätzlichen
Bewegungsfarben; `magnet_poles` hält Winkel, CAD-Flächenposition und Polrichtung fest.
Beide 1,5-mm-Abstände verlaufen von der Magnetfläche zur aktiven Wicklungsfläche
einschließlich der Deckelmembran oben beziehungsweise des Kassettenbodens unten.
Mechanisch bleiben Magnet–Deckel 0,35 mm und Magnet–Kassettenboden 0,50 mm frei;
der stationäre Kassetten–Deckel-Freigang zur Rückhaltung beträgt separat 0,15 mm.

E01 zeigt die Lage vor dem dauerhaften Einrasten, keine zugesicherte Demontage.
E04/E07/E15 begrenzen den oberen Blattbereich für die Detailansicht. E06 zeigt
den vollständigen Base-Körper. E05
blendet Kassette und Deckel zur Einsicht aus. E06 hebt Kassette, Deckel und Base
an; der untere Rotor bleibt in seiner Einbaulage. Die beiden E11-Coupons verwenden
dieselbe Trennung des kombinierten Builders an Y=0 wie der V5-Export.

E14/E15 ergänzen das unveränderte Produkt-CAD um zwei einfache Holzriegel und
untere Holzschrauben als **nicht druckbare Zeichnungsreferenzen**. Der untere
Riegel (Beispiel 260 × 190 × 30 mm) liegt an der Unterseite der vier Gehäuselaschen
an; vier nominale 4 × 30-mm-Schrauben mit flachem Kopf werden von oben eingedreht.
Ihre Achsen stammen direkt aus den vier CAD-Laschen. Der obere Riegel (Beispiel
260 × 70 × 30 mm) liegt auf dem vorhandenen 608-Halter; die vier 4 × 40-mm-
Schraubreferenzen des V5-Builders werden von unten eingedreht. Grau
unterscheidet diese stationären Holzreferenzen von den Druckteilen.
Holzquerschnitte, Schrauben, Vorbohrung und Tragfähigkeit sind vor Ort auszulegen;
die Nennhüllen behaupten keine Gewinde oder geprüfte Verbindung. Der obere Halter
wird erst nach dem Anziehen der M8-Klemmung montiert. Passung, Lagerung auf M8-Gewinde,
Magnetrückhaltung, elektrische Leistung, Festigkeit und Betrieb sind unvalidiert.

Die vorhandenen Vorschauprogramme für Rotorbaugruppe, Generator, Module und
Bajonett-Coupon verwenden nun die aktuellen V5-Schnittstellen. Die Rotorvorschau
teilt den Projektionsrenderer, stellt die offene obere M8-Klemmung dar und zählt
STEP-Volumenkörper getrennt von benannten Komponenten. Die Modulvorschau verwendet
die 60-Grad-Stufenphase. Rigid gemessene Rastüberdeckungen bleiben als ungeprüfte
elastische Passung dokumentiert. Die Programme schicken keinen Druckauftrag.

Auf dieser Windows/CadQuery-Laufzeit kann die native OCP-Nachbereitung nach
erfolgreicher Artefakterzeugung mit einem Fehlerstatus enden. Dateiprüfungen und
Testresultate müssen deshalb zusammen mit dem tatsächlichen Prozessstatus
berichtet werden; ein vorhandenes Bild allein belegt keinen sauberen Prozessabschluss.
