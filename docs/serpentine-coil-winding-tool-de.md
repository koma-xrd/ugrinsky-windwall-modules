# Waagerechtes Steck-Wickelrad und freier Drahtabroller

## Zweck und Grenzen

Zwei unabhängige, manuelle PLA-Module helfen beim Vorwickeln einer späteren
Serpentinenspule aus Kupferlackdraht. Das Wickelrad liegt waagerecht auf einem
51105-Axiallager. Die separate Kupferrolle steht aufrecht auf ihrem Drehteller.
Beide Module verwenden exakt dieselbe 190 × 190 mm große Basis; für gleichzeitigen
Betrieb zweimal drucken und zwei komplette 51105-Lager kaufen.

Die elf Einstellungen reichen von 100–200 mm in 10-mm-Schritten. Das Maß
bezeichnet die nominale Hülle der sechs Kontaktflächen: Die Wicklung bildet ein
gerundetes Sechseck, keinen zugesicherten Kreis. Alle sechs Schuhe müssen auf
derselben Zahl sitzen. Der Referenzaufbau zeigt 150 mm.

Der Abroller bleibt unverändert: Teller Ø150 mm, Zentriernippel Ø15 mm und
20 mm hoch, gedruckte Steckachse und das vorhandene 51105-Stecksystem.
Die Spule dreht frei; Draht von Hand führen und die Vorratsrolle von Hand stoppen.
Es gibt weder automatischen Vorschub noch eine Bremse.

## Sicherheit

Schutzbrille tragen. Haare, Kleidung, Finger, Drahtenden und Klebeband von allen
rotierenden Teilen fernhalten. Nur im Stillstand einstellen, tapen oder abziehen.
Vor jedem Einsatz Nabe, Sechskant, Rad, Steckzungen, Schuhe und Lagersitze auf
Risse, Weißbruch, Lockerung und Verschleiß prüfen. Bei Auffälligkeiten sofort stoppen.

Akkuschrauberbetrieb ist nicht freigegeben. Die obere Sechskantaufnahme ist für
einen späteren 1/4-Zoll-Bit vorgesehen, aber Drehzahl, Drehmoment, Laufzeit und
motorischer Betrieb sind nicht physisch validiert. CAD-Prüfungen sind keine
Festigkeits-, Lagerlebensdauer- oder Betriebsgenehmigung.

## Dateien und Stückliste

Die isolierte Werkzeugfreigabe liegt unter `release/winding-tool/`; sie verändert
weder das V5-Produktionsinventar noch dessen `PRINT_SOURCES`.
`stl/` enthält acht Druckmaster, `step/` dieselben acht CAD-Master,
`assembly/` beide Baugruppen. `bom.json` nennt die Mengen, `manifest.json`
die Geometrie-, Topologie-, STEP-Rückimport- und Hash-Prüfungen.

Für beide Module zusammen: 14 gedruckte Teile aus acht Mastern und zwei
vollständige gekaufte 51105-Lager. Die drei dargestellten Teile eines 51105 sind
untere Scheibe, Wälzkranz und obere Scheibe; keine Lagerteile drucken.

<!-- BEGIN print-bom -->
| Menge | Master | STL-Stamm | Material |
| ---: | --- | --- | --- |
| 1 | `winding_jig/coil_wheel` | `winding_jig_coil_wheel` | PLA |
| 6 | `winding_jig/contact_shoe` | `winding_jig_contact_shoe` | PLA |
| 1 | `winding_jig/hand_crank` | `winding_jig_hand_crank` | PLA |
| 1 | `winding_jig/horizontal_hub` | `winding_jig_horizontal_hub` | PLA |
| 1 | `winding_jig/rotating_grip` | `winding_jig_rotating_grip` | PLA |
| 2 | `wire_payoff/base` | `wire_payoff_base` | PLA |
| 1 | `wire_payoff/platter` | `wire_payoff_platter` | PLA |
| 1 | `wire_payoff/printed_spindle` | `wire_payoff_printed_spindle` | PLA |
<!-- END print-bom -->

<!-- BEGIN hardware-bom -->
| Menge | Kaufteil | Nennmaße und Umfang |
| ---: | --- | --- |
| 2 | `51105 thrust bearing` | 25 x 42 x 11 mm; complete set with separate lower and upper washers |
<!-- END hardware-bom -->

## Drucken und Passungen prüfen

Alle Druckteile sind PLA-Prototypen für ein höchstens 220 × 220 mm großes
Druckbett. Die STL-Dateien sind bereits dokumentiert ausgerichtet und auf Z=0
gesetzt. Das Rad und die Basis liegen flach; Schuhe um Y=−90° auf ihre ebene
innere Fußfläche gelegt und Nabe sowie
Kurbel um Y=90° gedreht. Stützen an den erforderlichen Unterseiten verwenden,
nicht in Passungen oder Bandkanälen stehen lassen. Die Passflächen sorgfältig
entgraten; Lackdraht darf keine scharfen Kanten berühren.

Zuerst einen Kontaktschuh und die Steckpassungen probedrucken. Seine beiden
mittleren Schienen verjüngen sich zu 3,40 × 2,90 mm großen Steckzungen für
3,50 × 3,00 mm große Radöffnungen: nominal 0,05 mm Spiel je Seite. Die breiteren
Schienen bilden den Anschlag. Es gibt keine Federnase; Halt entsteht durch Reibung.
Bei zu straffem Sitz vorsichtig nacharbeiten, niemals mit Gewalt einsetzen.
Bei lockerem Sitz die Druckeinstellungen anpassen.

Der Nabenpilot endet bei Z=1,5 mm über dem 1-mm-Blindboden der Basis. Gewicht
muss auf dem Lager liegen, nicht auf der Pilotspitze. Die Kurbel besitzt einen
6,35-mm-Sechskant über die Flächen; die Nabenaufnahme nominal 6,45 mm.
Der gerade Stecker hat einen Tiefenanschlag, aber keine Verriegelung.
Der drehbare Griff ist ebenfalls nach oben abnehmbar; beim Transport abnehmen.

## Wickler montieren

1. Eine gemeinsame Basis eben aufstellen. Bei realem Drahtzug bei Bedarf die
   vorgesehenen Randflächen mit Werkstattklemmen sichern, ohne die Drehung zu blockieren.
2. Das 51105 vollständig einlegen: untere Scheibe, Wälzkranz, obere Scheibe.
   Die Kontaktflächen sauber halten; das gekaufte Lager nach dessen Anleitung behandeln.
3. Die gedruckte horizontale Nabe von oben durch die Lagerbohrungen in die Basis
   stecken. Sie muss ohne Bodenkontakt auf der oberen Scheibe sitzen.
4. Das Wickelrad von oben auf den 14-mm-Naben-Sechskant stecken. Der flache Anschlag
   legt seine Unterseite auf Z=33 mm fest: 25 mm über der 8-mm-Basisfläche außerhalb
   des mittigen Lagerbosses. Der Arbeitsraum bleibt ringsum zum Tapen zugänglich.
5. Alle sechs Kontaktschuhe auf dieselbe Zahl stecken. Beide Zungen einsetzen
   und bis zum Anschlag herunterdrücken. Für einen Einstellwechsel den Schuh
   gerade an beiden Schienen herausziehen, nicht verkanten.
6. Die Handkurbel von oben in den zentralen Sechskant stecken und den frei
   drehbaren Griff aufsetzen. Der erhöhte Kurbelarm läuft oberhalb der Schuhe.
7. Langsam ohne Draht von Hand drehen. Lagerlauf, Steckpassungen und Freiraum
   prüfen. Das Rad wird durch Gewicht gehalten, nicht durch fragile Rastnasen.

Lastweg: Rad → Nabe → obere Lagerscheibe → Wälzkranz → untere Scheibe → Basis.
Der lange Pilot führt radial; das Axiallager allein ist keine Radialführung.

## Drahtabroller montieren

Die zweite identische Basis und das zweite vollständige 51105 verwenden.
Das vorhandene Abroller-Stecksystem bleibt erhalten: gedruckte Achse einsetzen,
Lagerstack einlegen und Teller auf die obere Vierkant-Steckverbindung setzen.
Prüfen, dass die bestehenden Rastzungen sauber einrasten, der Pilot frei dreht
und keine Nase beschädigt ist. Die Kupferrolle aufrecht auf den Ø15 × 20 mm
Zentriernippel stellen. Der Teller ist nicht mit der Handkurbel gekoppelt.

Die zwei bestehenden Abroller-Raststellen werden nur für Lager-/Tellerservice
gelöst; sie sind nicht Teil des neuen Wicklerantriebs. Bei Demontage Teller und
Achse gerade nach oben ziehen, damit die vorhandenen Rampen ausweichen können.

## Wickeln, tapen und Spule abziehen

1. Drahtanfang mit einem weichen, lösbaren Bandhalt sichern. Von Hand langsam
   wickeln, Draht führen und den Abroller von Hand stoppen. Keine definierte
   Drahtspannung oder Windungszahl wird durch das Werkzeug garantiert.
2. Die gerundete untere Schuhauflage verhindert das Abrutschen nach unten.
   Oberhalb davon bleibt die Kontaktfläche auf nominalem Radius; der obere
   Rand hat genau 0 mm radialen Überstand. Es gibt keine obere Zentrierlippe.
3. Anhalten. Durch die drei Bandöffnungen pro Schuh alle 18 Bandstellen mit
   10-mm-Klebeband umwickeln. Die Kanäle sind nach oben offen und besitzen
   mindestens 12 mm tangentialen und axialen Freiraum. Band unter der Wicklung
   hindurchführen und die Schlaufe schließen; Rad und Lagerung bleiben montiert.
4. Wicklung, Drahtanfang und Drahtende sichern. Kurbel samt Griff senkrecht
   nach oben abnehmen.
5. Die getapte Spule senkrecht nach oben über die offenen Schuhe abheben.
   Alle sechs Schuhe bleiben eingesteckt; sie weder nach innen versetzen noch
   für den normalen Spulenabzug entfernen. Nicht am Lackdraht reißen.
6. Nach jeder Probespule Drahtlack, Bandkontakt und Druckteile prüfen.
   Bei erhöhtem Widerstand stoppen und die Ursache suchen.

Der geprüfte CAD-Serviceweg berücksichtigt einen 9 mm hohen Wicklungsquerschnitt
mit 1 mm radialem Aufbau und 18 geschlossene, tangential 10 mm breite
Klebebandschlaufen. Er prüft die gesamte Bewegung, nicht nur Anfang und Ende:
zuerst Kurbel/Griff +Z, dann Spule/Band +Z über alle eingesteckten Schuhe.
Größere Wicklungsquerschnitte und die reale Abzugskraft sind nicht freigegeben.

## Bandwinkel und Durchmesser

Die sechs Schuhmitten liegen 60° auseinander. Die drei Passagen je Schuh liegen
auf dem unveränderten gekrümmten Schuh und ändern ihren physischen Winkel mit dem
gewählten Durchmesser. Die Nummern 1–18 bezeichnen die Folge, keine gleichmäßige
physische 20°-Teilung. Für Schuh k gilt: Mitte = k × 60°, Außenstellen = Mitte ±α.

<!-- BEGIN tape-angles -->
| Markierung / Nennhülle (mm) | Physische Winkel je Schuhmitte |
| ---: | --- |
| 100 | −18.23° / 0° / +18.23° |
| 110 | −16.53° / 0° / +16.53° |
| 120 | −15.11° / 0° / +15.11° |
| 130 | −13.91° / 0° / +13.91° |
| 140 | −12.89° / 0° / +12.89° |
| 150 | −12.00° / 0° / +12.00° |
| 160 | −11.23° / 0° / +11.23° |
| 170 | −10.55° / 0° / +10.55° |
| 180 | −9.94° / 0° / +9.94° |
| 190 | −9.41° / 0° / +9.41° |
| 200 | −8.92° / 0° / +8.92° |
<!-- END tape-angles -->

## Zeichnungen und Modellprüfung

- `winding-jig-reference.png`: beide Module, obere Steckkurbel und 25-mm-Arbeitsraum.
- `winding-jig-range.png`: Einstellungen 100/150/200 mm, Bandstellen und offener Schuh.
- `winding-tool-exploded.png`: vollständige Teilegruppen, Lagerreihenfolge und Abzug.

Die CAD-Prüfungen umfassen alle elf Einstellungen, tatsächliche Steckpassungen,
Bandwege, durchgehende Dreh- und Abzugsräume, Lagerlastweg, gemeinsame Basis,
Druckbettgrenzen, gültige Einzelkörper, geschlossene STL-Netze und STEP-Rückimport.
Der Prüfquerschnitt wird bis zur tatsächlichen unteren Auflage abgesenkt;
alle sechs Schuhe müssen ihn gegen weiteres Absinken stützen. Geschlossene
Bandwicklungen und der Abzug werden aus derselben aufliegenden Position geprüft.
Manifest-Erfolg setzt alle Prüfungen voraus; eine Behauptung in Metadaten ersetzt
keine Geometrieprüfung. Die gemeinsame Basis behält ihre bisherigen STL/STEP-Hashes.

## Verbleibende Prototypgrenzen

Nicht physisch validiert sind PLA-Festigkeit, Reibhalt, Sechskantverschleiß,
Lagerpassungen und -lebensdauer, Stabilität bei realem Drahtzug, Lackschutz,
Wickelgenauigkeit, Tape-Handhabung und Abzugskraft. Die Konstruktion enthält keine
zugesicherte Betriebsdrehzahl, Belastbarkeit oder Produktionsfreigabe.
