# Einfaches Steck-Wickelrad und freier Drahtabroller

## Zweck und Grenzen

Zwei unabhängige, rein manuelle Module helfen beim Vorwickeln einer späteren
Serpentinenspule aus 0,18-mm-Kupferlackdraht. Das vertikale Wickelrad trägt sechs
gleiche, vollständig abnehmbare Kontaktschuhe. Eine Handkurbel dreht das Rad über
eine gedruckte Welle in zwei 608-Lagern. Der separate Abroller trägt die
aufrechte Vorratsrolle auf einem frei drehenden Teller mit einem 51105-Axiallager.
Alle Verbindungen der beiden Werkzeuge sind schraubenlose Steck-/Rastverbindungen.

Die elf Markierungen reichen von 100–200 mm in 10-mm-Schritten; die
Referenzdarstellung verwendet 150 mm. Das Maß bezeichnet die nominale Hülle der
sechs Kontaktflächen. Die Wicklung bildet ein gerundetes Sechseck, keinen
zugesicherten Kreis. Alle Druckteile sind PLA-Prototypen. Die Werkzeugteile
gehören nicht zum V5-Produktionsinventar oder dessen `PRINT_SOURCES`.

Akkuschrauberbetrieb ist nicht freigegeben

Elektrische Eigenschaften, physische Funktion, Festigkeit und Ermüdung der
gedruckten Welle, Lebensdauer der Rastzungen, Lager- und Steckpassungen,
Maßhaltigkeit und Wiederholbarkeit, Lackschutz, Standfestigkeit, Stoppverhalten,
Entnahmekraft, Drehzahl und Produktionstauglichkeit sind nicht physisch validiert.
Es gibt keine freigegebene Drehzahl, Belastung oder endgültige Windungszahl.
CAD-, STL- und STEP-Prüfungen ersetzen keine Messung am gedruckten Prototyp.

## Sicherheit vor jedem Versuch

Schutzbrille tragen. Dünner Draht kann die Haut schneiden, sich verheddern,
reißen und zurückschnellen. Lose Enden kontrollieren; Draht nie um Finger wickeln.
Haare binden und Kleidung, Schmuck, Hände und lose Leitungen aus dem Drehbereich
halten. Vor Einstellen, Tapen, Entnehmen oder Lösen einer Verhedderung beide
Module vollständig anhalten und Drahtspannung kontrolliert abbauen.

Vor jedem Einsatz Welle, alle Rastzungen und Schnappringe, Schuhe, Turm und
Grundplatten auf Risse, Weißbruch, Verformung, Abrieb und gelockerte Verbindungen
prüfen. Drahtflächen müssen sauber und glatt sein. Beschädigte Teile ersetzen;
bei Klemmen, ruckendem Draht, Lackabrieb, Kippen oder ungewöhnlicher Reibung stoppen.
Beide Module auf einer stabilen Werkbank getrennt gegen Rutschen/Kippen sichern.
Optionale Werkbankzwingen sind Werkstattausrüstung; sie greifen nur an den
vorgesehenen Klemmlanden und bleiben außerhalb von Kurbel, Draht und Entnahmeweg.

## Release und Zeichnungen

`release/winding-tool/manifest.json` ist das Dateiinventar mit SHA-256-Prüfsummen,
Mengen, Druckorientierungen, CAD-Nennmaßen, Besitz-/Bewegungsgruppen und Audits.
`bom.json` enthält die kanonische Stückliste. Das kopierbare Release enthält
`stl/`, `step/`, `assembly/`, `drawings/` und diese Anleitung unter `docs/`.
Jedes STL hat einen gleichnamigen STEP-Master. Die zwei Baugruppen heißen
`simplified_winding_jig.step` und `free_running_wire_payoff.step`.

- `winding-jig-reference.png`: beide montierten Module bei 150 mm,
  Antriebsdetail, aufrechte Vorratsrolle, Drehsinn und Drahtzufuhr B → A.
- `winding-jig-range.png`: 100/150/200-mm-Hüllen, alle elf Markierungen,
  18 Stationsidentitäten und tatsächliche Bandwinkel sowie Schuhdetail.
- `winding-tool-exploded.png`: vollständige getrennte Montagegruppen,
  Lagerzuordnung, Steckfolge und Entnahme der getapten Spule nach vorn.

Die Montagegruppen zeigen jedes Bauglied einmal; Betriebsbilder darunter zeigen
dieselben Teile in aufeinanderfolgenden Zuständen. Abstände und unterschiedliche
Ansichtsmaßstäbe dienen der Lesbarkeit. Die gestrichelte Vorratsrolle ist eine
Beladungsskizze und kein zusätzliches Produktteil.

## Vollständige Stückliste

12 unterschiedliche Druckmaster ergeben 19 gedruckte Teile aus PLA. Nur die
nachfolgend aufgeführten Master drucken. Die Zahlen sind aus den tatsächlichen
Baugruppen-Vorkommen abgeleitet. Lager sind Kaufteile, keine Druckkörper.

<!-- BEGIN print-bom -->
| Menge | Master | STL-Stamm | Material |
| ---: | --- | --- | --- |
| 1 | `winding_jig/base` | `winding_jig_base` | PLA |
| 2 | `winding_jig/bearing_retainer` | `winding_jig_bearing_retainer` | PLA |
| 1 | `winding_jig/bearing_tower` | `winding_jig_bearing_tower` | PLA |
| 1 | `winding_jig/coil_wheel` | `winding_jig_coil_wheel` | PLA |
| 6 | `winding_jig/contact_shoe` | `winding_jig_contact_shoe` | PLA |
| 1 | `winding_jig/hand_crank` | `winding_jig_hand_crank` | PLA |
| 1 | `winding_jig/printed_shaft` | `winding_jig_printed_shaft` | PLA |
| 1 | `winding_jig/rotating_grip` | `winding_jig_rotating_grip` | PLA |
| 2 | `winding_jig/snap_collar` | `winding_jig_snap_collar` | PLA |
| 1 | `wire_payoff/base` | `wire_payoff_base` | PLA |
| 1 | `wire_payoff/platter` | `wire_payoff_platter` | PLA |
| 1 | `wire_payoff/printed_spindle` | `wire_payoff_printed_spindle` | PLA |
<!-- END print-bom -->

<!-- BEGIN hardware-bom -->
| Menge | Kaufteil | Nennmaße und Umfang |
| ---: | --- | --- |
| 2 | `608 bearing` | 8 x 22 x 7 mm |
| 1 | `51105 thrust bearing` | 25 x 42 x 11 mm; complete set with separate lower and upper washers |
<!-- END hardware-bom -->

Die englischen Kaufteil-IDs und Angaben bleiben identisch zu `bom.json`.
Ein 51105-Satz enthält untere Gehäusescheibe, Wälzkranz und obere Wellenscheibe.
Die beiden Scheiben bleiben separate Kaufteile; gedruckte Laufbahnen ersetzen
sie nicht. Zusätzlich benötigt werden Draht, 10-mm-Klebeband, Messmittel,
Markierstift, geeignete Entgratmittel und Schutzbrille. Band und Reinigungsmittel
zuerst an einem Drahtrest auf Lackverträglichkeit prüfen.

## PLA drucken und nacharbeiten

Die gelieferten STL-Dateien liegen bereits in ihrer dokumentierten Orientierung
auf Z = 0. Nicht nochmals blind um die angegebenen Winkel drehen. Das Manifest
speichert die Drehungen in X/Y/Z-Reihenfolge aus den Konstruktionskoordinaten.
Alle Master passen geometrisch auf 220 × 220 mm; dies ist keine Druckfreigabe.

| Druckteil | Orientierung der gelieferten STL-Datei |
| --- | --- |
| Wickelbasis | Breite Werkbankseite auf dem Bett |
| Lagerturm | Seitenfläche auf dem Bett, Raststege parallel zu den Schichten |
| Wickelrad | Hintere plane Radfläche auf dem Bett, Markierungen oben |
| Kontaktschuh | 90° um Konstruktions-X; Stützen nur an innerer Fläche/Fuß |
| Zwei Außenclips und zwei Schnappringe | Flache Ringseite auf dem Bett |
| Druckwelle | Achse parallel zum Bett; ebene Antriebsfläche unten, Release-Drehung (90°, −30°, 0°) |
| Handkurbel | Griffzapfen parallel zum Bett, unteren Nabenbereich unterstützen |
| Drehgriff | Auf der Stirnfläche |
| Abrollerbasis | Flache Werkbankfläche unten; kurze innere Nutbrücke prüfen |
| Abrollerspindel | Achse waagerecht, 90° um Y; Kern unterstützen |
| Abrollerteller | Ebene Lagerkontakt-Unterseite unten, integraler Dorn nach oben |

Slicer-Vorschau jeder Schicht prüfen. Rastschlitze, Lochreihen, Markierungen,
Bandpassagen und Lagerflächen müssen frei bleiben. Materialprofil, Schichthöhe,
Wandzahl, Füllung, Stützen und Druckhaftung durch eigene PLA-Proben bestimmen.
Zuerst eine einzelne Schuhverbindung, einen Ring und die Lagerpassungen prüfen.
Rastzungen nur über ihre zugänglichen Flächen und mit geringem Weg betätigen;
bei Weißbruch oder übermäßiger Kraft abbrechen. Welle und Zungen sind austauschbar.

Jede drahtberührende Oberfläche nacharbeiten: sechs Kontaktkonturen, alle
Passagenmündungen, Startstelle, Schichtnähte, Tellerkante, Dorn und tatsächlicher
Drahtweg. Grate, Elefantenfuß und Stützspuren restlos entfernen, Kanten glätten
und reinigen. Mit einem Drahtrest bei geringer Spannung auf Lackabschabung prüfen.
Lagerzapfen glätten, ohne Passflächen unkontrolliert abzutragen. Beschädigte
Schuhe ersetzen; eine sichtbare Verrundung allein beweist keinen Lackschutz.

## Montage A: Wickelrad mit Ständer

1. Rechteckigen Turmschlüssel in die Basis stecken, bis beide seitlich
   zugänglichen Haken einrasten. Schlüsselflächen tragen die Betriebslast.
2. Zwei 608 von ihren jeweiligen äußeren Stirnseiten in den Turm einsetzen.
   Außenclips an den Ohren zusammendrücken, in die Nut einsetzen und entspannen.
   Beide Clips müssen sitzen; ihre Ohren bleiben durch die Fenster erreichbar.
3. Druckwelle von der offenen Vorderseite durch beide 8-mm-Lagerbohrungen führen.
   Das schmale hintere Polygon passiert die Lager. Schlechte Passung nicht erzwingen.
4. Beide offenen Schnappringe in die Nuten beiderseits des vorderen 608 setzen.
   Sie begrenzen die Welle axial in beide Richtungen. Zugängliche Ringöffnungen
   und vollständig sitzende Nuten prüfen.
5. Kurbel auf das hintere Polygon stecken, bis beide Haken greifen. Geschlitztes
   Ende des integralen Griffzapfens zusammendrücken und Drehgriff aufschieben.
   Der Griff muss sich frei drehen; die Kurbel bleibt axial gehalten.
6. Rad auf das vordere Polygon stecken, bis beide von vorn lösbaren Haken greifen.
   Formschluss, axialen Halt und einen vollständigen langsamen Handumlauf prüfen.
7. Alle sechs Schuhe auf dieselbe markierte Einstellung stecken. Beide
   Schlüsselstifte jedes Schuhs gehören in das zugehörige Lochpaar; beide
   rückseitigen Rastzungen müssen greifen. Sechs gleiche Zahlen und zwölf
   vollständig sitzende Stifte kontrollieren.

Die Außenringe beider 608 gehören zum stationären Turm. Schultern und Außenclips
greifen ausschließlich am Außenring an. Die Innenringe folgen der Druckwelle.
Nur das vordere Lager ortet die Welle über die beiden Schnappringe; am hinteren
Außenring bleibt Axialspiel. Die Lager nicht gegeneinander verspannen und keine
Dichtung belasten. Die CAD-Körper sind vollständige Lagerhüllen, keine einzeln
modellierten Innen-/Außenringe. Reale Anlageflächen und Passungen prüfen;
Montagekraft nur in den gerade einzusetzenden Ring einleiten.

Zum Service Rad an den vorderen Haken lösen, Griffende zusammendrücken und
Griff abziehen, Kurbelzungen lösen und Kurbel abziehen. Beide Schnappringe
abnehmen und die Welle nach vorn herausziehen. Außenclips an den Ohren drücken
und durch ihre offenen Fenster herausnehmen, dann Lager entnehmen. Zum
Turmausbau beide seitlichen Basiszungen lösen und Schlüssel herausheben.
Alle Rastteile nach dem Service auf Risse und sicheren Wiedereingriff prüfen.

## Montage B: freier Abroller

1. Untere 51105-Gehäusescheibe (`lower_washer`) auf den ringförmigen Basisboden
   legen; sie bleibt stationär. Wälzkranz (`bearing`) und obere Wellenscheibe
   (`upper_washer`) auflegen. Beide Laufbahnen zeigen zum Wälzkranz. Die obere
   Scheibe trägt den Teller und dreht mit ihm; der Wälzkranz bewegt sich lagerintern.
2. Druckspindel einstecken, bis ihre unteren Rastnasen in der umlaufenden Nut
   greifen. Teller auf den oberen Vierkant drücken, bis die oberen Nasen greifen.
   Der Teller muss ohne Berührung der Basis frei drehen; der Lagerstapel darf
   nicht durch die Rastverbindung axial zusammengedrückt werden.
3. Vorratsrolle aufrecht auf den 150-mm-Teller stellen. Der integrale Dorn
   Ø15 × 20 mm zentriert sie. Tatsächliche Bohrung, Schwerpunkt und Abstand
   prüfen; die Rolle nicht aufpressen. Draht tangential und ohne scharfe
   Umlenkung zum Wickelrad führen. Abstand der unabhängigen Module anpassen.
4. Beim Anhalten den frei laufenden Teller von Hand stoppen, bis auch die
   Vorratsrolle stillsteht. Finger und lose Leitungen vom Spalt unter dem
   Teller fernhalten. Geringe Drahtspannung verwenden, Nachlaufen beobachten.

Zum Beladen/Service Teller senkrecht nach oben abheben; seine rampenförmigen
Rastnasen lösen. Über dem Teller mindestens 40 mm freien Hub vorsehen und
zusätzlich Platz für die tatsächliche Rolle lassen. Exponierte Spindel nach
oben abziehen; anschließend obere Scheibe, Wälzkranz und untere Scheibe einzeln
abheben. Zwei Fingeraussparungen geben den Rand der unteren Scheibe frei.
Umgekehrt montieren und freien Lauf wieder prüfen. Entnahmekraft am Prototyp
testen; bei Klemmen nicht am Draht ziehen.

## Durchmesser und Bandstellen

Im Stillstand alle sechs Schuhe auf dieselbe Zahl setzen: 100, 110, 120, 130,
140, 150, 160, 170, 180, 190 oder 200 mm. Ein Lochschritt entspricht 5 mm Radius.
An drei gegenüberliegenden Schuhpaaren messen; die gedruckte Zahl ist keine
Kalibrierung. Für Einstellwechsel beide Rastzungen lösen und den Schuh ganz
abziehen, dann im neuen Lochpaar einrasten.

Es gibt drei Bandöffnungen pro Schuh und 18 Bandstellen insgesamt. Jede Passage
besitzt mindestens 12 mm tangentiale CAD-Freiheit für die 10-mm-Bandbreite und
zusätzlich 12 mm axiale Freiheit für das Wickelpaket. Die Bandbreite verläuft
quer zur Spulenachse entlang des Umfangs. Drei Streifen je Schuh vorbereiten,
mit zugänglichen Enden und Klebeseite zum späteren Umschließen.
Keine freie Bandfahne darf während des Drehens in Lager oder Kurbel geraten.

Die Identitäten 1–18 bilden die nominale Stationsfolge; es gibt keine gleichmäßige physische 20°-Teilung.
Die sechs Schuhmitten liegen 60° auseinander, doch die unveränderten Schuhe
werden radial versetzt. Daher ändern sich die tatsächlichen Winkel der äußeren
Passagen. Dies gilt auch bei 150 mm. Die Tabelle zeigt die aus dem aktuellen CAD
bestimmten Winkel relativ zur jeweiligen Schuhmitte; für Schuh k die Mitte
(k − 1) × 60° addieren und modulo 360° lesen. `actual_tape_angles_deg` im
Manifest enthält alle 18 ungerundeten Werte je Einstellung.

<!-- BEGIN tape-angles -->
| Markierung / Nennhülle (mm) | Physische Winkel je Schuhmitte |
| ---: | --- |
| 100 | −18.43° / 0° / +18.43° |
| 110 | −16.70° / 0° / +16.70° |
| 120 | −15.26° / 0° / +15.26° |
| 130 | −14.04° / 0° / +14.04° |
| 140 | −12.99° / 0° / +12.99° |
| 150 | −12.09° / 0° / +12.09° |
| 160 | −11.31° / 0° / +11.31° |
| 170 | −10.62° / 0° / +10.62° |
| 180 | −10.01° / 0° / +10.01° |
| 190 | −9.46° / 0° / +9.46° |
| 200 | −8.97° / 0° / +8.97° |
<!-- END tape-angles -->

## Von Hand wickeln, tapen und entnehmen

1. Nach Riss-, Passungs- und Freilaufkontrolle Startleitung A markieren. Draht
   an einer geglätteten Schuhfläche mit einem weichen, lösbaren Bandhalt sichern.
   Keine scharfe Kante oder enge Drahtschlinge als Verankerung verwenden.
2. Langsam nur mit der Handkurbel wickeln. Zeichnung 02 zeigt gegen den
   Uhrzeigersinn in der Frontansicht; gewählten Drehsinn markieren und während
   einer Spule beibehalten. Draht leicht führen und Windungen ordentlich legen.
3. Zunächst eine kleine Probespule herstellen. Bei Verheddern, springendem Draht,
   Lackabrieb oder ungewöhnlichem Widerstand stoppen und Ursache beseitigen.
   Beim Wickelstopp den Abroller von Hand stoppen und Enden gegen Rückschlag sichern.
4. Im Stillstand alle 18 Bandstreifen um die Wicklung schließen, ohne sie
   einzuschneiden. Ende B mit Anschlusslänge markieren und kontrolliert trennen.
   A/B, Drehsinn und Windungszahl dauerhaft dokumentieren.
5. Eine Hilfsperson unterstützt die getapte Spule. Jetzt alle sechs Schuhe vollständig
   entfernen: je beide rückseitigen Zungen lösen, den Schuh ganz nach vorn
   ausziehen, Zungen entspannen lassen und den Schuh außerhalb des Entnahmewegs
   ablegen. Sechsmal wiederholen. Ein einzelner Lochschritt nach innen ist kein
   zulässiger Ersatz; bei 100 mm würden Nachbarschuhenden zusammenstoßen.
6. Erst nach Abnahme aller sechs Schuhe und mindestens 2 mm radialer Entlastung
   die gehaltene Spule mit sämtlichen geschlossenen Bandstellen nach vorn
   abziehen. Rad, Welle, Kurbel und Ständer bleiben dabei montiert. Nicht am
   Kupfer ziehen oder die Spule über eine Kante hebeln; bei Hängenbleiben stoppen.

Der geprüfte CAD-Serviceweg zieht jeden Schuh 40 mm vor und parkt ihn 40 mm
radial außen; die Spule wird anschließend 120 mm vorgezogen. Dies sind
Freiraumdarstellungen, keine gemessenen Entnahmekräfte. Die CAD-Prüfhülle umfasst
9 mm axiale Wicklungsbreite, 1 mm radialen Aufbau und 18 geschlossene Bandhüllen
(10 mm tangentiale Streifenbreite, 10 mm axiale Schleifenhöhe, 4 mm radialer
Abstand zwischen Innen- und Außenkontur, 0,25 mm Wand). Die Bandhüllen folgen
den gekrümmten Kontaktflächen und umschließen konservativ auch die nach innen
laufenden Drahtsehnen über den Bandöffnungen. Die 10 mm axiale
Schleifenhöhe ist nicht die Bandbreite. Größere oder unregelmäßige Wicklungen
benötigen eine eigene Prüfung des vollständigen Entnahmewegs.

## Serpentinenform und Kontrolle der Probespule

Getapte Wicklung ohne scharfe Knicke in die geplante Serpentinenform legen.
Bandstellen dabei nach Bedarf umverteilen: ihre physischen Ausgangswinkel sind
nicht gleichmäßig. Beim Vergleich mit einer Kassette an deren vorgesehenen
Führungen abwechselnd innen und außen entlanglegen. Anschlussweg und A/B-Marken
erhalten; die Vorrichtung bestätigt weder korrekte Polung noch elektrische Addition.

Nach jeder Probespule Drahtlack an allen Schuh-, Band- und Führungskontakten unter
Vergrößerung auf Kratzer, Einschnitte und blankes Kupfer prüfen. Gekreuzte/lose
Windungen, verdrillte Anschlüsse, klemmendes Band und bleibende Verformung prüfen.
Gemessene Durchmesser, Windungszahl, Draht-/Bandcharge, Drehsinn, A/B, Nachlaufen,
Entnahmekraft-Beobachtung und Passung in der vorgesehenen Serpentinenform notieren.
Danach sämtliche PLA-Verbindungen, Welle, Lager und Drahtflächen erneut prüfen.
Fehlerhafte Probe kennzeichnen und nicht als Betriebswicklung verwenden.
Widerstand und Isolation nur mit einem geeigneten Messverfahren beurteilen;
ein Durchgangstest allein erteilt keine elektrische Freigabe.

## Reproduzieren

Aus dem Repository-Hauptverzeichnis mit eingerichtetem CAD-Python:

```powershell
$env:PYTHONPATH = "$PWD;$PWD/src"
python scripts/run_geometry.py scripts/build_winding_tool.py
python scripts/run_geometry.py -m unittest tests.test_winding_tool_export -v
```

Für eigene Prüfungen `--output-dir build/winding-tool-check` nutzen. Der Builder
erzeugt CAD, BOM, drei PNGs mit je 2000 × 1400 Pixeln und diese Anleitung. Die
markierten Stücklisten- und Winkeltabellen werden aus der aktuellen BOM und CAD
synchronisiert. Erst nach bestandenen Audits und Hashprüfungen erscheint das
Erfolgsmanifest. Quell- und Release-Anleitung der Standardkonfiguration sind
byte-identisch. Ein bekannter nativer OCP-Fehler beim Prozessende kann nach
bestandenen Tests oder fertiger Veröffentlichung auftreten; Testergebnis und
nativen Prozessstatus getrennt protokollieren.
