# Ugrinsky Wind Wall V5 – Generatorgehäuse, Lagerung und Dokumentation

## Ziel

Die bestätigten Rotorbauteile V4.3 bleiben die geometrische Basis. V5 ergänzt
einen vollständig modellierten Generatoraufbau für den späteren Einbau in einen
Holzzaun. Beide Magnetrotoren drehen mit der durchgehenden M8-Gewindestange;
Spule, Spulenkassette, Generatorgehäuse, Generator-Deckel und oberer Lagerhalter
bleiben stationär. Die Ausgabe umfasst prüfbare CAD-Modelle, STEP/STL-Dateien,
aktuelle Explosionszeichnungen und eine überarbeitete deutsche DOCX-Anleitung.

## Verbindliche Rotorbasis

- Sieben Stufen: ein Base-Modul, fünf identische Standardmodule, ein Top-Modul.
- Verriegelung gegen den Uhrzeigersinn in Winddrehrichtung.
- Dauerhafte Rastung im Bajonett; keine radialen Sicherungsschrauben.
- Geschlossene untere Kreisbahn im weiblichen Bajonett; die vertikalen
  Einführfenster enden oberhalb der Bahn.
- Flügelwand 2,0 mm; bündige, helikale Übergänge mit Nut und Feder.
- Freie Modulmitte; nur kurze M8-Führungsringe in den Endbereichen.
- Base-Flügel reichen bis in die massive obere Magnetplatte und verbinden sich
  flügelförmig mit deren zentralem Trägerring. Die früheren sechs geraden
  Radialrippen des oberen Magnetträgers entfallen.
- Base und Top erhalten lokal verstärkte Kraftbereiche für M8-Muttern.
- Die bisherige große Top-Closure entfällt.

## Rotierender Generatorstrang

Von oben nach unten:

1. Base-Modul mit integrierter oberer Magnetplatte und 18 Taschen für Magnete
   mit nominal 10 × 2 mm.
2. Rotierende Lagerscheibe des 51105, über einen gedruckten Zentrierbund mit
   knapp 25 mm Durchmesser zum Base-Modul ausgerichtet.
3. Durchgehende M8-Gewindestange.
4. Untere Magnetplatte mit 18 Magnettaschen innerhalb des Generatorgehäuses,
   unterhalb der stationären Spule.
5. Formschlüssige M8-Sechskantaufnahme in der unteren Magnetplatte.

Die untere Magnetplatte muss innerhalb des geschlossenen Gehäuseraums rotieren.
Sie darf weder Spulenkassette noch Gehäuseboden, Seitenwand, Deckel oder
Schraubkanäle berühren. Magnetpolarität und Luftspalte bleiben in den
Explosionszeichnungen eindeutig bezeichnet.

## Unteres Axiallager 51105

Das vorgesehene einseitig wirkende Axialkugellager 51105 hat die normativen
Hauptabmessungen 25 × 42 × 11 mm. Die Konstruktion verwendet zunächst folgende
PLA-Prototypmaße:

- stationärer Außensitz: 42,2 mm;
- Gesamttiefe des Einbauraums: 11,2 mm;
- rotierender Zentrierbund: nominal knapp unter 25 mm;
- zentrale Durchführung für die M8-Welle und ihre Mutteraufnahme.

Die stationäre Lagerscheibe stützt sich auf einem zentralen Bund des
Generator-Deckels ab. Die rotierende Lagerscheibe wird durch den Zentrierbund
des Base-Moduls geführt. Das Lager übernimmt die axiale Rotorlast. Ein
dreistufiger Passungscoupon muss vor einer Druckfreigabe unterschiedliche
Sitzmaße um das Nominalmaß prüfen. Die Maße sind nicht als Presspassung
freigegeben, bevor Lager und Coupon real vermessen wurden.

## Stationäres Generatorgehäuse

Der erste Entwurf ist ein von oben montierbarer Topf:

- ungefähr 130 mm Gehäuse-Außendurchmesser;
- mindestens 120 mm nutzbarer Innenraum;
- geschlossener Boden mit ausreichendem Abstand zur unteren Magnetplatte und
  deren M8-Hardware;
- vier gleichmäßig verteilte äußere Bodenlaschen zur Verschraubung nach unten
  auf einen Holzrahmen;
- verstärkter seitlicher Kabelausgang als Prototyp, ausdrücklich noch nicht
  wasserdicht;
- symmetrische Grundarchitektur, damit später eine umgedrehte oder abgedichtete
  Variante konstruiert werden kann.

Die Befestigungslaschen dürfen den rotierenden Innenraum nicht einschränken.
Ihre Holzschrauben liegen außerhalb aller Magnet- und Spulenbereiche.

## Spulenkassette

Die Serpentinen-Spule sitzt in einer separaten, austauschbaren stationären
Kassette mit ungefähr 118 mm Außendurchmesser. Sie wird:

- nach unten durch eine umlaufende Gehäuseschulter getragen;
- radial durch einen Passring mit zunächst 0,3–0,4 mm Druckspiel zentriert;
- durch eine eindeutige Nase/Tasche gegen Verdrehung gesichert;
- durch den verschraubten Deckel axial nach oben gehalten;
- nach Abnahme des Deckels nach oben entnommen;
- seitlich mit Zugentlastungsmöglichkeit aus dem Gehäuse geführt.

Ein eigener Passungscoupon prüft die radiale Kassettenschnittstelle. Die
Spulenwicklung bleibt als experimentelle 20/40/80-Windungs-Matrix für jeden
gemessenen Drahtdurchmesser dokumentiert; es wird keine endgültige Wicklungszahl
behauptet.

## Generator-Deckel

Der stationäre Deckel erfüllt vier Aufgaben:

1. Spulenkassette axial sichern;
2. zentralen stationären Sitz des 51105 tragen;
3. den oberen Magnetrotor mit definiertem Luftspalt von der Spule trennen;
4. den Gehäusetopf verschließen.

Sechs gleichmäßig verteilte M4-Durchgangsschrauben und gefangene
M4-Sechskantmuttern verbinden Deckel und Topf. Gedruckte Gewinde werden im
PLA-Prototyp vermieden. Der Deckel darf nicht mitrotieren.

## Luftspalte und Einbaureihenfolge

Die ersten CAD-Nennwerte betragen oben und unten jeweils 1,5 mm von der
Magnetfläche zur aktiven Wicklungsfläche. Beide magnetischen Abstände enthalten
den dazwischenliegenden Kunststoff: oben die 1,00 mm dicke Deckelmembran,
unten den 1,00 mm dicken Kassettenboden. Sie gelten nur für bündig oder tiefer
sitzende Magnete. Die mechanischen Freigänge betragen oben 0,35 mm zwischen
Magnetfläche und Deckelmembran und unten 0,50 mm zwischen Magnetfläche und
Kassettenboden. Weitere 0,15 mm zwischen Kassettenoberkante und Deckelunterseite
erlauben die axiale Rückhaltung. Diese Bezugsebenen sind die verbindliche,
im Abschlussreview bestätigte Interpretation; die Nenngeometrie bleibt unverändert.
Die Einbaureihenfolge ist:

1. untere Magnetplatte und M8-Hardware in den Gehäusetopf einsetzen;
2. Spulenkassette auf Schulter und Verdrehsicherung setzen;
3. stationären Deckel montieren;
4. 51105 auf stationären und rotierenden Zentrierflächen einsetzen;
5. Base-Rotor und restlichen Rotorstapel montieren.

Ein Kollisionsaudit prüft jeden rotierenden Körper gegen alle stationären
Körper. Vorgesehene Lagerkontakte werden separat benannt; alle anderen
Überschneidungen müssen unter der numerischen Toleranz liegen.

## Oberer stationärer Lagerhalter

Der obere Lagerhalter wird neu konstruiert und verwendet keine
Original-Befestigungspunkte:

- rechteckige Platte, zunächst 80 × 50 × 12 mm;
- 608-Lager, 8 × 22 × 7 mm;
- von oben zugänglicher Prototypsitz 22,2 × 7,2 mm;
- geschlossene untere Schulter von ungefähr 3 mm;
- zentrale M8-Durchführung;
- vier symmetrische, von unten zugängliche versenkte Bohrungen für ungefähr
  4 × 40 mm Holzschrauben;
- Befestigung von unten gegen einen vorhandenen oberen Holzrahmen;
- der Holzrahmen verschließt den Lagersitz oben und hält das Lager gefangen.

Der 608-Lagerpunkt führt hauptsächlich radial. Das 51105 trägt die Axiallast.
Eine lokal abgeschliffene M8-Gewindestange ist zulässig; eine gedruckte
Führungshülse gehört nicht zum Entwurf. Zwischen rotierendem Top-Modul und
stationärem Lagerhalter bleibt ein definierter Sicherheitsabstand.

## Aerodynamischer oberer Abschluss

Der Ugrinsky-Rotor muss für diese Konstruktionsstufe nicht durch eine große
rotierende Scheibe geschlossen werden. Das Top-Modul behält nur den lokal
verstärkten M8-Kraftbereich. Eine optionale aerodynamische Endscheibe kann
später vergleichend getestet werden, gehört aber nicht zu V5.

## Passungsproben

V5 erzeugt mindestens:

- 51105-Außensitz-Coupon mit drei Durchmessern;
- 25-mm-Zentrierbund-Coupon;
- 608-Sitz-Coupon mit drei Durchmessern;
- Spulenkassetten-Passungssegment;
- bestehenden Magnettaschen-Coupon;
- bestehenden männlichen/weiblichen Bajonett-Rastcoupon.

Jeder Coupon wird als eigenes STL ausgegeben und mit den verwendeten Maßen in
einem Manifest dokumentiert.

## Explosionszeichnungen

Aktuelle Zeichnungen zeigen mindestens:

- vollständigen siebenstufigen Rotor;
- alle drei Rotormodultypen und ihre Übergänge;
- Base-Modul, 51105 und Generator-Deckel im Schnitt;
- vollständigen Generator mit oberer Magnetplatte, Spule und unterer
  Magnetplatte innerhalb des Gehäuses;
- stationäre und rotierende Teile durch Farbe und Legende getrennt;
- untere Gehäusebefestigungslaschen und seitlichen Kabelausgang;
- oberen 608-Lagerhalter und die Montage von unten am Holzrahmen;
- vollständige Gesamtmontage zwischen unterem und oberem Zaunrahmen.

Keine Zeichnung darf Generatorgehäuse oder Spule als rotierend darstellen.

## DOCX-Anleitung

Die vorhandene deutsche Anleitung wird neu erzeugt und enthält:

- aktuelle V4.3/V5-Teileliste und Dateinamen;
- Druckhinweise für PLA-Test und später ASA;
- Montage des Generators in korrekter Reihenfolge;
- Einbauorientierung von 51105 und 608;
- Kennzeichnung stationärer/rotierender Komponenten;
- Magnetpolung und beide Luftspalte;
- Spulenkassetten-Sicherung und seitliche Kabelführung;
- Serpentinen-Testmatrix für gemessene Drahtdurchmesser;
- Warnung vor direktem Anschluss an den 48-V-Bleiakku;
- bekannte Grenzen: keine Wasserdichtheit, keine freigegebenen Presspassungen,
  keine abschließend bestimmte Wicklung und keine physische Dauerfestigkeit.

Die DOCX wird strukturell und barrierearm geprüft. Eine visuelle Seitenprüfung
und PDF-Ausgabe erfolgen nur, wenn ein geeigneter LibreOffice-Renderer
verfügbar ist; fehlende Renderprüfung darf nicht als bestanden bezeichnet
werden.

## Ausgaben

Die stabile Release-Ausgabe enthält:

- STEP und STL aller aktuellen Druckteile;
- STEP der verriegelten Rotor- und Generatorbaugruppen;
- Coupon-STLs und Maßmanifest;
- Explosionszeichnungen als hochauflösende PNGs;
- aktuelle deutsche DOCX-Anleitung;
- maschinenlesbares Release-Manifest mit Abmessungen, Stückzahlen und
  Validierungsstatus.

Veraltete Top-Closure-Ausgaben werden entfernt oder ausdrücklich als obsolet
markiert. Die generierten Dateien bleiben reproduzierbare Build-Artefakte.

## Prüfung und Freigabegrenzen

Automatisierte Prüfungen decken mindestens ab:

- gültige, zusammenhängende Druckkörper;
- Lager- und Couponmaße;
- freie M8-Wellenpassage;
- Position der unteren Magnetplatte innerhalb des Gehäuses;
- Stillstand aller Gehäuse-/Spulenteile;
- Luftspalte und Kollisionsfreiheit;
- Sicherung der Spulenkassette in allen Freiheitsrichtungen;
- Befestigungszugang für Deckel, Bodenlaschen und oberen Lagerhalter;
- Vollständigkeit von Exportmanifest, Zeichnungen und DOCX.

Automatisierte Geometrieprüfungen ersetzen keine reale Passungs-, Magnet-,
Wicklungs-, Belastungs-, Schwingungs-, Wetter- oder Sicherheitsprüfung. Der
erste Release bleibt ein PLA-Passungsprototyp.

## Versionskontrolle und Veröffentlichung

Der bestehende Rotorstand ist durch Commit `cdd1c2d` gesichert. Die V5-Arbeit
erhält nach bestandenen fokussierten Prüfungen einen weiteren Commit. Nach
abschließender Prüfung werden Quellcode, Tests, Dokumentation und die vereinbarte
Release-Struktur zum konfigurierten GitHub-Remote `origin` gepusht. Ein Push
erfolgt erst, wenn die erzeugten Dateien und bekannten Einschränkungen im
Abschlussbericht genannt sind.
