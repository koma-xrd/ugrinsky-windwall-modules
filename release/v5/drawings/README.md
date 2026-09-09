# V5-Montagezeichnungen

Die 15 PNG-Dateien E01–E15 sind mit 2400 × 1680 Pixeln aus den aktuellen
CadQuery-Volumenkörpern berechnet. Die Figuren enthalten deutsche Beschriftungen,
nummerierte Bauteilmarkierungen und eine gemeinsame Bewegungslegende.
`figures.json` enthält Bild-ID, Dateiname, Bildunterschrift, Alternativtext,
Beschriftungen, Pixelmaße, CAD-Quellen, Bewegungszuordnung und dargestellte Grenzen.
Die SHA-256 des verwendeten V5-Manifests steht im Kopf des Bildinventars.

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
| E02 | Base, Standard und Top als drei Druckmodultypen |
| E03 | Dauerhaftes Bajonett und Nut-Feder-Blattnaht |
| E04 | Base-Schulter, M8-Mutter und getrennte 51105-Lagerteile im Schnitt |
| E05 | Unterer Magnetrotor innerhalb des aufgeschnittenen Gehäuses |
| E06 | Generator-Explosion mit unterem Rotor im Gehäuse unter der Wicklung |
| E07 | Montierter Generator im Mittelschnitt |
| E08 | Kassettenführung, Verdrehsicherung und axiale Rückhaltung |
| E09 | Deckel mit sechs M4-Schrauben und gefangenen Muttern |
| E10 | Seitlicher Kabeldurchgang bei 45 Grad |
| E11 | Getrennte 51105-Außensitz- und 25-mm-Pilot-Coupons des Releases |
| E12 | 608-Lagersitz-Coupon mit drei Durchmessern |
| E13 | Oberer Halter: Schrauben von unten ins Holz; montierter Lagerschnitt |
| E14 | Einbau am vorhandenen oberen Holzrahmen |
| E15 | Gesamtbaugruppe und Generator-Einbaudetail |

Ocker bedeutet rotierend, Türkis stationär. Violett kennzeichnet den separat
bewegten 51105-Wälzbereich beziehungsweise die unaufgelöste 608-Lagerhülle.
Grau kennzeichnet Prüf- oder Freiraumreferenzen. Das Holz ist als stationäre
CAD-Referenz ebenfalls türkis dargestellt. Schrauben, Magnete, Wicklung und Lager
sind Nennhüllen. Es werden weder Gewinde noch elektrische Wicklungsdetails behauptet.
Magnete sind im rotierenden Ocker dunkler, der Wicklungsraum im stationären Türkis
heller dargestellt, damit ihre bündigen Grenzflächen erkennbar bleiben.

E01 zeigt die Lage vor dem dauerhaften Einrasten, keine zugesicherte Demontage.
E04/E06/E07/E15 begrenzen den oberen Blattbereich für die Detailansicht. E05
blendet Kassette und Deckel zur Einsicht aus. E06 hebt Kassette, Deckel und Base
an; der untere Rotor bleibt in seiner Einbaulage. Die beiden E11-Coupons verwenden
dieselbe Trennung des kombinierten Builders an Y=0 wie der V5-Export.

Das V5-CAD enthält einen lokalen oberen Holzrahmen, keinen vollständigen Zaun.
Unterer Rahmen und seine Schrauben sind nicht modelliert. Der obere Halter wird
erst nach dem Anziehen der M8-Klemmung montiert. Passung, Lagerung auf M8-Gewinde,
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
