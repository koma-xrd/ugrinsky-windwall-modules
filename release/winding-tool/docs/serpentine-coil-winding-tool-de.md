# Serpentinen-Spule: Wickelvorrichtung und Drahtabroller

## Zweck, Grenzen und Sicherheit

Diese zwei unabhängigen, handbetätigten Werkstatthilfen sind Prototypen:
Modul A wickelt zunächst eine runde Spule; Modul B lässt die Vorratsspule
passiv unter leichter Filzreibung ablaufen. Die Module besitzen getrennte
Grundplatten und keine mechanische Synchronisierung. Sie sind keine
V5-Produktionsteile. Ausgangsmaterial ist 0,18-mm-Kupferlackdraht.

Akkuschrauberbetrieb ist nicht freigegeben

Die vorhandene Sechskantaufnahme ist eine zukünftige Schnittstelle und keine
Betriebsfreigabe. Drehzahl, Drehmomentbegrenzung und Schutzabdeckung sind nicht
ausgelegt oder validiert. Elektrische Eigenschaften, Festigkeit, Ermüdung,
gedruckte Passungen, Wickelqualität und Produktionstauglichkeit sind nicht
physisch validiert. Es gibt keine freigegebene Drehzahl oder Windungszahl.

Schutzbrille tragen. Dünner Draht kann Haut schneiden, sich verheddern, reißen
und mit seinen Enden in die Augen schlagen. Drahtschlaufen und lose Enden
kontrollieren; lange Haare binden, Schmuck und lose Kleidung fernhalten.
Nicht in die laufende Wicklung greifen und Draht nie um Finger wickeln.
Zum Einstellen, Tapen, Entnehmen oder Lösen einer Verhedderung vollständig
anhalten, Kurbel sichern und Drahtspannung kontrolliert abbauen. Bei Rissen,
Klemmen, Abrieb, springendem Draht oder lockeren Verbindungen sofort stoppen.

## Konfiguration und Unterlagen

Die Standardkonfiguration beginnt bei Ø127 mm, einem rechnerischen Startwert.
Bei abweichend erzeugten Releases gelten die folgenden automatisch aus den
Parametern erzeugten Tabellen und deren STEP-Dateien; das Standardmaß ersetzt
keine Messung. Die praktische Kalibrierung weiter unten bleibt erforderlich.

<!-- BEGIN configuration -->
| Merkmal | CAD-Konfiguration dieses Releases |
| --- | --- |
| Wickeldurchmesser min. / Referenz / max. | Ø110 / Ø127 / Ø145 mm |
| Rippen / Bandstellen / Winkelraster | 6 / 18 / 20° |
| Bandbreite / freie Passage | 10 / 12 mm |
| Radialer Freigabeweg | 2 mm |
| Teller / Spulendorn | Ø150 / Ø15 × 20 mm |
| Welle / Sechskant-Schlüsselweite | Ø8 / 6.35 mm |
| Maximales Druckbett | 220 × 220 mm |
| Abrollerfüße / Werkzeugfreiheit unter Basis | 24 mm / kurzer 2,5-mm-Inbusschlüssel |
<!-- END configuration -->

Das Release-Verzeichnis `release/winding-tool/` enthält `manifest.json`,
`bom.json`, `stl/`, `step/`, `assembly/`, `drawings/` und diese Anleitung
unter `docs/`. Die Anleitung bleibt dadurch auch im kopierten Release nutzbar.
Die Tabellen verwenden unveränderte technische IDs aus der maschinenlesbaren
BOM; OD = Außendurchmesser, ID = Innendurchmesser, AF = Schlüsselweite.

Die Zeichnungen im Unterverzeichnis `drawings/`:

- `winding-jig-reference.png`: beide Module montiert, Drahtzufuhr B → A.
- `winding-jig-range.png`: Kopf bei Ø110 / Ø127 / Ø145 mm, sechs Rippen,
  18 nummerierte Bandstellen und vollständiger Entnahmeweg.
- `winding-tool-exploded.png`: getrennte Montagegruppen und Lagerzuordnung.
  Explosionsabstände sind ausschließlich Darstellungsabstände.

## Druckteile, Orientierung und Nacharbeit

14 verschiedene STL-Dateien ergeben 26 Druckteile. Die Dateistämme sind unten
vollständig aufgeführt. Nur diese Körper drucken; Lager, Welle, Schrauben,
Griff, Feder, Filz und Sicherungen sind Kauf- oder anzufertigende Metallteile.

<!-- BEGIN print-bom -->
| Menge | Druckteil / STL-Stamm | Modul |
| --- | --- | --- |
| 1 | `winding_frame_base` | winding_jig |
| 2 | `winding_frame_bearing_cap` | winding_jig |
| 1 | `winding_frame_crank` | winding_jig |
| 1 | `winding_frame_head_hub` | winding_jig |
| 1 | `winding_frame_head_retaining_collar` | winding_jig |
| 2 | `winding_frame_upright` | winding_jig |
| 1 | `winding_head_backplate` | winding_jig |
| 1 | `winding_head_cam` | winding_jig |
| 1 | `winding_head_clamp` | winding_jig |
| 6 | `winding_head_rib` | winding_jig |
| 6 | `winding_head_slider` | winding_jig |
| 1 | `wire_payoff_adjuster` | wire_payoff |
| 1 | `wire_payoff_base` | wire_payoff |
| 1 | `wire_payoff_platter` | wire_payoff |
<!-- END print-bom -->

Die STL-Dateien sind auf Z = 0 gesetzt; das Manifest nennt zusätzlich
`print_rotation_y_deg`. STEP-Einzelteile verwenden dieselbe Rotation vor
der vertikalen STL-Verschiebung. Baugruppen-STEPs bleiben in Einbaulage.
Druckbett und Slicer-Vorschau für jedes Teil prüfen:

- Rahmenbasis mit ihrer breiten Unterseite auf das Bett; die vier offenen
  Kopfversenkungen von Stützen säubern. Abrollerbasis hat vier integrale
  24-mm-Füße: beim Druck auf den Füßen braucht die Platte darüber entfernbare
  Stützen. Alternativ Orientierung im Slicer anpassen und Lagersitz schützen.
  Ständer stehen in den gelieferten STL-Dateien auf den Füßen; horizontale
  Lagerbohrungen und Überhänge auf entfernbares Stützmaterial prüfen.
- Rückplatte, Kurvenring, Klemmring, Rippen, Schieber, Nabe, Haltering, Lagerkappen und Kurbel
  sind gegenüber der X-Wickelachse um −90° um Y gedreht; die flache axiale
  Seite liegt unten. Führungsdächer, Mutternfenster und Bandpassagen in jeder
  Schicht kontrollieren. Rippen-Drahtflächen vor Stützspuren schützen.
- Der Abrollerteller bleibt einteilig. Sein unterer Lagerpilot zeigt zum Bett;
  der Tellerüberhang braucht eine im Slicer geprüfte, restlos entfernbare
  Stützstrategie oder eine begründet geänderte Orientierung. Beide Piloten,
  Lageranlage und Drahtkontakt dürfen nicht durch Stützen beschädigt werden.
- Einsteller mit dem breiten Flansch unten drucken. Gewinde wird durch die
  eingelegte M3-Mutter getragen; keine Schraube in bloßen Kunststoff zwingen.

Material, Schichthöhe, Wandzahl, Füllung und Stützen sind Prozessversuche.
Keine Druck- oder Festigkeitsfreigabe ableiten. Zuerst passende Lager- und
Führungsproben sowie eine einzelne Rippe drucken, dann trocken montieren.

Alle drahtberührenden Oberflächen nacharbeiten: jede Rippenkontur, beide
Mündungen aller Bandpassagen, Schichtnähte, Tellerkante, Spulendorn und
tatsächliche Drahtzuführung. Grate, Elefantenfuß und Stützreste entfernen,
Kanten glatt verrunden, reinigen und mit einem Drahtrest bei sehr geringer
Spannung prüfen. Weder Schraubenenden noch Folien-/Bandkanten dürfen Lack
abschaben. Nicht durch Nacharbeit unkontrolliert Lager- oder Führungsmaße
verändern. Beschädigte Rippen ersetzen.

## Vollständige Hardware-Stückliste

Mengen beziehen sich auf beide Module zusammen. Für **jedes** Modul zwischen
vier Tischschrauben mit acht Scheiben und vier Muttern **oder** zwei Zwingen
wählen; diese Alternativen nicht addieren. Die CAD-Hardware ist eine nominale
Auswahl, keine geprüfte Einkaufsliste. Gewindelängen, Köpfe, Scheibenstapel,
Sicherungen und Bewegungsfreiheit am realen Aufbau prüfen. Sonderteile wie
Schulterfolger und quergebohrte Welle erfordern geeignete Fertigung.

<!-- BEGIN hardware-bom -->
| Menge | Stücklisten-ID | Nennauswahl (CAD) |
| --- | --- | --- |
| 1 | `51105 thrust bearing` | 25 x 42 x 11 mm, complete purchased bearing |
| 2 | `608 bearing` | 8 x 22 x 7 mm, sealed radial bearing |
| 1 | `8 mm shaft` | 8 mm steel shaft, 194.9 mm long |
| 3 | `ISO 4032 M3 preload nut` | M3, 5.5 mm across flats, 2.4 mm thick |
| 4 | `M3 bearing cap nut` | ISO 4032 M3, 5.5 mm AF x 2.4 mm |
| 4 | `M3 bearing cap screw` | M3 x 22 mm socket-head screw |
| 4 | `M3 bearing cap washer` | 6 mm OD x 3.2 mm ID x 0.6 mm |
| 1 | `M3 brake adjustment screw` | M3 socket-head screw, 19.9 mm shank |
| 1 | `M3 brake-adjuster nut` | ISO 4032 M3, 5.5 mm across flats, 2.4 mm thick |
| 6 | `M3 guide stop nut` | ISO 4032 M3, 5.5 mm AF x 2.4 mm |
| 6 | `M3 guide stop screw` | M3 x 20 mm socket-head screw |
| 6 | `M3 guide stop washer` | 6 mm OD x 3.2 mm ID x 0.6 mm |
| 6 | `M3 rib attachment pin` | M3 x 22 mm socket-head through-bolt |
| 3 | `M3 x 20 mm socket-head cap screw` | ISO 4762 M3 x 20, 5.5 mm head diameter, 3 mm head height |
| 4 | `M4 upright bolt` | M4 x 20 mm socket-head bolt, 7 mm OD x 4 mm head |
| 4 | `M4 upright nut` | M4 locking nut, 7 mm AF x 5 mm |
| 8 | `M4 upright washer` | 9 mm OD x 4.3 mm ID x 0.8 mm |
| 1 | `brake compression spring` | 8 mm OD, 4 mm ID, 9.2 mm free length |
| 1 | `brake spring washer` | 10 mm OD x 3.4 mm ID x 0.6 mm |
| 6 | `cam follower captive nut` | ISO 4032 M3, 5.5 mm AF x 2.4 mm |
| 6 | `cam follower washer` | 7 mm OD x 4.2 mm ID x 0.6 mm |
| 1 | `crank grip` | 22 mm OD x 24 mm long, 6.6 mm running bore |
| 1 | `crank grip axle` | 6 mm diameter x 41 mm retained axle |
| 2 | `crank grip axle retaining ring` | External retaining ring for 6 mm grooved axle |
| 2 | `crank grip washer` | 6.1 mm ID x 14 mm OD x 0.6 mm |
| 1 | `crank shaft retaining pin` | 4 mm diameter x 30 mm removable cross-pin |
| 1 | `felt brake pad` | 14 mm OD x 3.4 mm ID x 2 mm uncompressed felt |
| 1 | `head collar retaining pin` | 4 mm diameter x 32 mm removable cross-pin |
| 1 | `head hub retaining pin` | 4 mm diameter x 26 mm removable cross-pin |
| 6 | `metal cam follower` | 4 mm shoulder x 6.65 mm, M3 threaded tip x 2.6 mm, 5.5 x 3 mm head |
| 3 | `removable cross-pin keeper` | Keeper clip matched to each 4 mm cross-pin |
| 6 | `rib attachment locknut` | M3 locking nut, 5.5 mm AF x 4 mm |
| 12 | `rib attachment washer` | 6 mm OD x 3.2 mm ID x 0.6 mm |
| 2 | `shaft locator pin` | 3 mm diameter x 20 mm removable cross-pin |
| 2 | `shaft locator pin keeper` | Keeper clip matched to 3 mm locator cross-pin |
| 2 | `shaft shoulder collar` | Steel: 8.2 mm bore, 10.4 mm OD x 6 mm nose, 16 mm OD x 8 mm body |
| 4 | `winding_jig bench bolt` | M5 through-bolt; length = bench thickness + 18 mm |
| 2 | `winding_jig bench clamp` | Small bench clamp for 13 x 60 mm clamp land |
| 4 | `winding_jig bench nut` | M5 locking nut |
| 8 | `winding_jig bench washer` | M5 flat washer |
| 4 | `wire_payoff bench bolt` | M5 through-bolt; length = bench thickness + 42 mm |
| 2 | `wire_payoff bench clamp` | Small bench clamp for 13 x 60 mm clamp land |
| 4 | `wire_payoff bench nut` | M5 locking nut |
| 8 | `wire_payoff bench washer` | M5 flat washer |
<!-- END hardware-bom -->

Zusätzlich: 0,18-mm-Kupferlackdraht, 10-mm-Klebeband, Messschieber,
geeignete Entgratmittel, Handwerkzeug, Markierstift, Schutzbrille und eine
stabile Werkbank. Band und Reinigungsmittel zunächst auf Lackverträglichkeit
prüfen. Federkennlinie und Filz sind nach gemessener geringer Ablaufreibung
auszuwählen; die Hüllgeometrie allein bestimmt keine Bremskraft.

## Lager: was dreht, was bleibt stehen?

Die beiden **608** sind vollständige Radiallager 8 × 22 × 7 mm. Der Außenring
bleibt jeweils im Ständer, der Innenring folgt der Welle. Die CAD-Hülle ist
stationär klassifiziert, weil interne Ringe/Wälzkörper nicht einzeln modelliert
sind. Das bedeutet nicht, dass das ganze reale Lager stillsteht. Montagekraft
nur in den einzusetzenden Ring einleiten; Welle und Sitze vorher messen.

Beide Außenringe werden zwischen Ständerschulter und angeschraubter Lagerkappe
gehalten. Die Anlage beginnt bei Radius 10 mm; der Bereich innerhalb davon ist
freigestellt. Nur am **linken** 608 begrenzen zwei querverstiftete Stahlbundringe
die Welle in beiden Axialrichtungen. Ihre Ø10,4-mm-Nasen berühren ausschließlich
den Innenring; je Seite bleiben nominal 0,1 mm Luft. Die rechte Welle gleitet
axial im rechten Innenring. Keine Verspannung durch gegeneinander angezogene
Lager erzeugen. Die tatsächlichen Innen- und Außenring-Anlageflächen des gekauften
608 prüfen: weder Dichtung noch der jeweils andere Ring dürfen geklemmt werden.
Die Bundringe und ihre Stifte sind Metallteile, keine Druckteile.

Die Nennauswahl berücksichtigt die Abstützmaße des
[SKF-608-2RSH-Datenblatts](https://www.tme.eu/Document/83a59906c97cb2ff6c50c795411b45d2/SKF608-2RSH.pdf):
Innenringbund Ø10–10,5 mm, Gehäusebundöffnung höchstens Ø20 mm. Die CAD-Prüfung
schließt zusätzlich den Dichtungsbereich bis Ø19,2 mm von der Anlage aus;
andere Fabrikate trotzdem am realen Lager prüfen.

Das **51105** ist ein vollständiges Axiallager 25 × 42 × 11 mm mit drei
dargestellten Mitgliedern, nicht drei Lager:

1. Gehäusescheibe (`housing_washer`) bleibt unten im Sitz der Abrollerbasis.
2. Wälzkranz (`rolling_envelope`) besitzt eigene lagerinterne Bewegung.
3. Wellenscheibe (`shaft_washer`) dreht oben mit dem Teller.

Beide Laufbahnen zeigen zum Wälzkranz. Scheiben anhand der tatsächlichen
Lagergeometrie und Herstellerkennzeichnung zuordnen. Der Standard-Lagersitz
Ø42,2 mm und der rotierende Pilot Ø24,8 mm sowie die 608-Sitze Ø22,2 mm sind
Passungskandidaten, keine garantierten Presspassungen. Das Manifest nennt die
tatsächlichen Lagerparameter des Releases. Teller abheben und Spule wechseln,
ohne den stationären Gehäusesitz zu zerlegen.

## Montage A: Wickelvorrichtung

1. Sechs M3-Folgermuttern von unten in die Schieber einsetzen. Je Rippe den
   Schlüssel mit dem Schieber verbinden; M3×22-Querbolzen, je zwei Scheiben
   und Sicherungsmutter verwenden. Köpfe und Muttern bleiben außerhalb der
   Führungswände; die Führung nicht zusammendrücken.
2. Schieber/Rippen von außen in die Rückplatte einschieben. Die sechs
   abnehmbaren M3-Anschlagschrauben samt Muttern und Scheiben montieren.
   Ohne diese Anschläge nicht wickeln. Jede Führung muss über den gesamten
   Verstell- und Freigabeweg gleiten, ohne dass der Schieber austritt.
3. Kurvenring über die sechs Folgerpositionen setzen. Sechs Metallschulterfolger
   mit Scheiben in die gefangenen Muttern einsetzen. Der Schulterstapel hält
   die nominelle 0,2-mm-Bewegungsluft; normale Schrauben unbekannter Länge
   dürfen den Ring nicht einklemmen. Alle sechs Folger müssen in ihren
   Kurvenbahnen sitzen. Den separaten Klemmring aufsetzen.
4. Drei M3-Vorspannmuttern radial in den Haltering einsetzen, dann die drei
   M3×20-Schrauben lose einsetzen. Der Haltering liegt vor der Rippenseite;
   sein Ø4×32-Querbolzen lässt sich außerhalb der Wicklung herausziehen.
   Nabe mit drei formschlüssigen Mitnehmern, Kopf und Haltering zunächst ohne
   Welle zusammenstecken und auf weicher Unterlage zusammenhalten. Die beiden
   Kopfquerbolzen erst nach dem Welleneinbau in Schritt 5 einsetzen.
   Nabenmitnehmer müssen vollständig in der Rückplatte sitzen. Kein Drehmoment
   allein über eine Druckpassung übertragen.
5. Ständer mit vier M4×20-Sockelkopfschrauben befestigen: Köpfe und je eine
   0,8-mm-Scheibe von unten in die 4,9-mm-tiefen Basisversenkungen setzen.
   Oben je eine Scheibe und M4-Sicherungsmutter auflegen. Die Füße liegen
   direkt auf der Platte. Kein Teil dieses Stapels darf unter Z=0 vorstehen.
   Beide 608 einsetzen, je Lager eine Kappe mit zwei M3×22-Schrauben,
   Außenscheiben und Muttern befestigen. Nur den Außenring erfassen.
   Eine zweite Person hält den Kopfstapel zwischen den Ständern. Welle von
   links durch äußeren Stahlbundring, linkes 608 und inneren Stahlbundring,
   dann Nabe/Kopf/Haltering, rechtes 608 und Kurbel führen. Bundringnasen zum
   linken Innenring ausrichten.
   Zwei Ø3×20-Stifte mit Sicherungen an den im STEP/Manifest angegebenen
   Positionen einsetzen, danach beide Kopfbolzen Ø4 mit ihren Sicherungen.
   Die drei Antriebsstifte sind Ø4; nicht mit den Bundringstiften verwechseln.
   Wellenbohrungen entgraten, axialen Freigang und Fluchtung prüfen.
6. Kurbel mit eigenem Querbolzen und Clip sichern. Griff mit Achse, zwei
   Scheiben und zwei passenden Sicherungsringen montieren. Nutpositionen der
   Griffachse am realen Scheibenstapel festlegen; CAD-Hüllen bilden Nuten
   nicht aus. Der Griff muss frei drehen, alle Sicherungen müssen halten.
7. Kopf auf Referenz stellen. Die drei Vorspannschrauben gleichmäßig gegen
   den Klemmring anlegen, sodass der Kurvenring gehalten wird; keine validierten
   Anzugsmomente vorgeben. Die Reaktion läuft über Rückplatte/Nabe, Querbolzen,
   Welle und Haltering. Nach Klemmen erneut sechs gleiche Radien prüfen.
8. Eine volle Umdrehung langsam von Hand prüfen: Kurbel, Handraum, Ständer,
   Folger, Anschläge und Bandstellen dürfen nicht kollidieren. Bei Widerstand
   Ursache beseitigen, nicht stärker kurbeln.

## Montage B: Abroller und Bremse

1. Gehäusescheibe, Wälzkranz und Wellenscheibe in der genannten Reihenfolge
   montieren. Sitze säubern; keine Kraft über die Wälzkörper einleiten.
2. M3-Mutter in das seitliche Fenster des gedruckten Einstellers einsetzen.
   Feder auf den Boden der Basistasche setzen, darüber die Federscheibe,
   dann Einsteller und Filz. Der Einsteller lässt sich im freien Zustand
   durch den seitlichen Servicezugang einsetzen. Die zwei geraden Flanschkanten
   müssen zwischen den Führungswänden liegen; sie verhindern Mitdrehen beim
   Schraubenverstellen und bleiben im gesamten 1-mm-Hub im Eingriff.
3. M3-Bremsschraube von unten durch ihren festen Kopfsitz in die Einstellermutter
   führen. Sie muss im gesamten Einstellbereich eingreifen. Filz liegt zwischen
   Einsteller und Tellerunterseite; Metallteile dürfen den Teller nicht berühren.
   Ein kurzer 2,5-mm-Inbusschlüssel passt von der offenen +X-Seite unter die
   montierte Basis zwischen ihre 24-mm-Füße. Der kurze Schenkel zeigt nach oben.
   Je 60° verstellen, Schlüssel nach unten aussetzen und neu ansetzen.
4. Teller mit Lagerpilot aufsetzen. Der obere angefaste Dorn Ø15 × 20 mm
   zentriert die Vorratsspule in der Standardkonfiguration. Tatsächliches
   Spulenloch, Schwerpunkt und Entnehmbarkeit prüfen; keine Spule aufpressen.
5. In freilaufender Stellung beginnen. Die CAD-Einstellung 0…1 entspricht
   0…1 mm Filzkompression und besitzt 1 mm Abstand zwischen starrem Anschlag
   und Teller; dies sind keine Umdrehungen am realen Einsteller. Schraube in
   kleinen Schritten verstellen, reale Filzanlage und Widerstand beobachten.
   Nur so viel Schleppreibung wählen, dass die Spule beim Anhalten nicht
   unkontrolliert nachläuft. Kein starres Festklemmen des Tellers zulassen.
6. Zum Filzwechsel vollständig stoppen, Teller abnehmen, Bremse entspannen
   und Bremsschraube entfernen. Filz/Einsteller seitlich herausnehmen; Feder
   und Scheibe kontrolliert halten. Nach Montage freien Lauf erneut prüfen.

## Werkbank und Drahtweg

Beide Grundplatten einzeln gegen Rutschen und Kippen befestigen. Je Modul
entweder vier M5-Durchgangsschrauben mit Scheiben und Sicherungsmuttern an
geeigneter Werkbank oder zwei Zwingen auf den zugänglichen 13×60-mm-Klemmlanden
verwenden. Länge und Unterseitenzugang vor Ort prüfen; Schraubenköpfe,
Zwingen und Hände müssen außerhalb von Kurbel und Drahtweg bleiben.
Die Abrollerfüße bleiben auf der Werkbank; keine zusätzliche Tischöffnung für
die Bremse ist vorgesehen. Den mittleren Raum zwischen den Füßen für den
Schlüssel freihalten. Bei Schraubmontage reicht die M5-Schraube durch Fuß und
Platte (32 mm); hierfür gilt Werkbankdicke + 42 mm als Nennauswahl. Am Rahmen
gilt Werkbankdicke + 18 mm. Die vier Rahmen-M4-Stapel vor Tischmontage prüfen.
Links neben der Wickelwelle mindestens 220 mm freien Auszugsraum und über dem
Kopf mindestens 200 mm Hebeweg für die Entnahme reservieren.

Abroller so ausrichten, dass der Draht von der Vorratsspule tangential und
ohne scharfe Umlenkung zu den Rippen läuft. Abstand und Winkel am realen
Spulentyp bestimmen; die Zeichnung legt keinen Zwangsvorschub oder gemeinsamen
Sockel fest. Freies Drahtende sicher halten und zunächst ohne Wicklung testen.

## Durchmesser einstellen, Band einlegen, von Hand wickeln

1. Vollständig anhalten. Alle drei Vorspannschrauben lösen, bis der Kurvenring
   frei verstellbar ist. Ring gleichmäßig auf den Sollwert drehen; sechs
   Rippen müssen synchron radial folgen. Referenzmarke Ø127 mm zunächst
   als Startwert verwenden, dann gegenüberliegende Kontaktflächen messen.
2. Kurvenring mit den drei Schrauben wieder halten. Gleichmäßige Rippenradien
   und sicheren Eingriff aller sechs Folger kontrollieren. Die äußeren
   Anschläge bleiben montiert; nicht über die Nennlimits hinaus wickeln.
3. 18 ausreichend lange Streifen 10-mm-Klebeband in die nummerierten Stationen
   1…18 legen. Klebeseite so orientieren, dass die fertige Wicklung umschlossen
   werden kann. Freie Enden zugänglich halten; Band darf weder Folger noch
   Kurvenring oder Welle berühren. Jede Passage ist nominell mindestens 12 mm
   breit, ihre Druckausführung muss die tatsächliche Bandbreite frei passieren lassen.
4. Startleitung **A** markieren und am Band mit weichem, lösbarem Halt sichern.
   Draht nicht an Schraube, scharfem Loch oder engem Knick verankern.
   Eine kleine Probespule beginnen; noch keine endgültige Windungszahl festlegen.
5. Kurbel von Hand betätigen und Draht nur leicht führen. In der Frontansicht
   auf die Rippen gegen den Uhrzeigersinn wickeln (Zeichnung 02). Auf der
   Gegenseite erscheint dieselbe Rotation umgekehrt. Den gewählten Drehsinn
   auf der Spule markieren und während einer Spule beibehalten.
6. Windungen sauber nebeneinander führen. Nicht durch hohe Drahtspannung
   zusammenpressen. Bei Nachlaufen, Verheddern oder Lackabrieb anhalten,
   Drahtspannung abbauen und Drahtweg/Bremse korrigieren.
7. Nach der gewählten Zahl von Runden anhalten. Die 18 vorbereiteten Streifen
   um die Wicklung schließen, ohne Draht einzuschneiden. Ende **B** mit
   ausreichender Anschlusslänge markieren und kontrolliert abtrennen;
   Enden gegen Zurückschnellen sichern.

## Spule lösen und serpentinenförmig legen

Alle drei Vorspannschrauben lösen. Kurvenring nach innen verstellen, bis jede
Rippe mindestens **2 mm radial** von der gewickelten Kontur zurücksteht
(bei abweichender Konfiguration den Freigabeweg der Tabelle verwenden).
Bei der kleinsten Wickelstellung ist dieser zusätzliche Weg nur zur Entnahme
vorgesehen. Er erweitert den nominalen Wickelbereich nicht.
Band darf nicht in der Rippe hängen; nicht am Kupfer ziehen oder die Wicklung
gewaltsam abhebeln.

Die Spule kann erst nach dem folgenden vollständigen Ausbauweg aus dem
geschlossenen Zwei-Ständer-Rahmen entnommen werden (Zeichnung 02):

1. Drahtenden sichern und 18 Bandstellen schließen. Kopf/Rippen mindestens
   2 mm radial lösen. Eine zweite Person unterstützt Kopf, Nabe und Haltering
   gemeinsam, hält den Ringstapel zusammen und sichert Kurbel und Bundringe.
2. Alle fünf Querbolzen entsichern: zwei Kopfbolzen Ø4, Kurbelbolzen Ø4 und
   zwei linke Bundringbolzen Ø3. Kopf- und Bundringbolzen nach oben herausziehen;
   den Kurbelbolzen seitlich ziehen. Lagerkappen und Ständer bleiben fest montiert.
3. Die entgratete Welle **220 mm nach links** ganz herausziehen. Lose Teile
   kontrolliert halten; die zweite Person unterstützt weiter den Kopf samt Spule.
4. Kopf mit Nabe/Haltering und getapter Spule gemeinsam **200 mm nach oben**
   zwischen den Ständern herausheben. Auf einer weichen Unterlage den Kopf
   zusammenhalten. Jetzt liegt die Spule oberhalb des gesamten Rahmens.
5. Die Spule **50 mm axial zur Rippenseite** abziehen. Nicht am Draht ziehen.
   Der CAD-Entnahmeversuch umfasst bis 10 mm Wicklungsbreite, 3 mm radialen
   Aufbau und 0,5 mm nach innen stehendes Band. Größere oder unregelmäßige
   Wicklungen vorab separat prüfen; bei Hängenbleiben abbrechen.

Zum Wiederaufbau Welle, alle fünf Stifte und Sicherungen einsetzen, das linke
Axialspiel und den freien Lauf prüfen und erst dann den nächsten Wickelversuch
beginnen. Die Spule anschließend ohne scharfe Knicke an den
18 Bandpositionen in die offene Serpentinenform bringen. In der V5-Kassette
abwechselnd an der inneren und äußeren Seite der 18 gerundeten Führungen
entlanglegen. Bandstellen gleichmäßig verteilen, Lack und Anschlussleitungen
vor Druckstellen schützen. **Ein vollständiger Umlauf um alle 18 Führungen
ist eine elektrische Windung**. A/B und Wickeldrehsinn vor dem Einsetzen
dauerhaft dokumentieren. Die Vorrichtung beweist weder korrekte Polung noch
elektrische Addition der Abschnitte.

Für einen Rippenwechsel Kopf nach Entspannen von der Welle abnehmen,
Folger und zugehörigen äußeren Anschlag entfernen und Rippe/Schieber nach
außen ausziehen. Erst dann den tangentialen Rippenbolzen lösen. Eine normale
Spulenentnahme erfordert keinen Ausbau dieser Verbindung.

## Physische Ø127-mm-Kalibrierung und Kontrolle der Probespule

Ø127 mm ist aus der aktuellen Führungsmittellinie berechnet. Banddicke,
Lackdraht, Windungszahl, gedruckte Radien und Umformung verändern den realen
Bedarf. Vor einer längeren Wicklung:

1. Referenzmarke anfahren und klemmen. An drei gegenüberliegenden
   Rippenpaaren den tatsächlichen Durchmesser messen; Messpunkte,
   Abweichung, Material und Druckeinstellungen notieren.
2. Eine kleine Probespule mit dokumentierter Windungszahl, Drahtcharge,
   Bandart und geringer Spannung wickeln, tapen und mit mindestens 2 mm
   radialer Entlastung abnehmen. Nicht allein nach der Gravur urteilen.
3. In der Kassette serpentinenförmig einlegen. Länge, Lage der 18 Bandstellen,
   Anschlussweg, Wicklungshöhe und Abstand zu angrenzenden Bauteilen prüfen.
   Bei Bedarf Durchmesser innerhalb 110…145 mm vorsichtig anpassen und
   die Probe wiederholen; tatsächlichen Einstellwert und Messdurchmesser notieren.
4. Nach jeder Probespule Drahtlack an Rippen- und Bandkontaktstellen unter
   Vergrößerung auf Kratzer, Einschnitte und blankes Kupfer prüfen. Auf
   gekreuzte/lose Windungen, verdrillte Leitungen und klemmende Bandstellen achten.
5. Rippen, Führungen, Kurvenfolger, Anschläge, Klemmschrauben, Sicherungen,
   Lager und Filz auf Abrieb, Risse, Lockerung und ungewollte Erwärmung prüfen.
   Freien Handlauf und geringes Nachlaufen erneut kontrollieren.
6. Widerstand und Isolation nur mit geeignetem Messverfahren beurteilen;
   keine elektrische Freigabe aus Geometrie oder bloßem Durchgang ableiten.
   Fehlerhafte Probe kennzeichnen und nicht als Betriebswicklung verwenden.

Protokoll mindestens mit Datum, gemessenem Durchmesser an drei Paaren,
Windungszahl, Wickeldrehsinn, A/B, Draht-/Banddaten, Bremsbeobachtung, Lackzustand,
Entnehmbarkeit und Kassettenpassung führen. Erst physische Versuche können
Passung und Prozess bestätigen; diese Veröffentlichung enthält solche
Mess- oder Produktionsnachweise nicht.

## Reproduzieren und prüfen

Aus dem Repository-Hauptverzeichnis mit dem eingerichteten CAD-Python:

```powershell
$env:PYTHONPATH = "$PWD;$PWD/src"
python scripts/run_geometry.py scripts/build_winding_tool.py
python scripts/run_geometry.py -m unittest tests.test_winding_tool_export -v
```

Der Builder erzeugt Geometrie, Stückliste, drei Zeichnungen und Anleitung
zusammen; erst danach erscheint das Erfolgsmanifest mit SHA-256-Prüfsummen.
Tabellen zwischen den HTML-Markierungen werden aus Parametern und BOM
aktualisiert. Geometrie- und Dateiprüfungen sind keine physische Validierung.
Ein bekannter nativer OCP-Fehler beim Prozessende kann nach bestandenen
Python-Tests auftreten; Testergebnis und Prozessstatus getrennt protokollieren.
