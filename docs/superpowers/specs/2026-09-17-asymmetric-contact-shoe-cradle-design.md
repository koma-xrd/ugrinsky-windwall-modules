# Gerundete Drahtführung mit freier Vorderschulter

## Ziel

Der steckbare `winding_jig_contact_shoe` erhält eine direkt konstruierte,
gerundete Drahtauflage mit einer hohen Schutzschulter an der freien Vorderseite.
Alle sechs Schuhe müssen sich bei fest gehaltener, geschlossener getapter
Wicklung kontinuierlich nach vorn entfernen lassen.

Der Wire-Payoff bleibt vollständig unverändert.

Diese Festlegung ersetzt die ursprünglich geplante höhere rückseitige Schulter:
Sie hätte beim Vorziehen die festgehaltene Wicklung durchdrungen, noch bevor die
Rastpins das 5 mm dicke Rad verlassen. Auch eine positive niedrige Hinterschulter
würde Drahtverformung voraussetzen. Der überarbeitete Weg verlangt weder eine
Verformung der Wicklung noch eine radiale Verlagerung eingerasteter Schuhe.

## Profil und Bezugsmaße

- Der Auflageboden und der gesamte radseitige Auslauf liegen auf dem gewählten
  nominellen Wickelradius. Die Einstellung 100 mm behält ihre nominelle
  100-mm-Hülle; der Schulterrand ist kein Durchmesserbezug.
- Die rad- beziehungsweise rückseitige Entnahmeseite hat genau 0 mm Überhöhung.
  Ihre axiale Endkante ist gerundet; es bleibt keine positive Sperrlippe.
- Die freie vordere Schutzschulter steht 2,5 bis 3,0 mm über dem Boden
  (Konstruktionswert 2,7 mm). Sie bewegt sich beim Vorziehen vom Draht weg.
- Beim Standard-Schuh reicht die nominale Auflage bis zur oberen Bandmündung
  bei Z=23,8 mm. Die gesamte
  9 mm breite Prüfwicklung bei Z=12,5..21,5 mm liegt auf nominalem Radius.
  Die tangential anschließende kubische Rundung steigt bis Z=26,5 mm zur
  Vorderschulter an. Axiale Endabstände folgen der Bandfreiheit, damit auch
  akzeptierte kürzere Schuhe keine rückläufige Außenkontur erhalten.
- Boden, Übergang und Schulter sind stetig gerundet. Es gibt keine scharfen
  Kanten im Drahtkontaktbereich.
- Das Profil ist Bestandteil des einteiligen Schuhmasters. Es gibt kein
  separates Einsatzteil und keine einzelnen Führungsnasen.

## CAD-Konstruktion

Die asymmetrische Außenkontur wird direkt im axial-radialen Querschnitt der
Schuhschale beschrieben und anschließend als zusammenhängende Schalenkontur
erzeugt. Sie wird nicht als nachträglicher zylindrischer Ausschnitt in die
bisherige Schale eingebracht.

Die innere Schalenwand, der Schuhfuß und beide Rastpins behalten ihre bisherigen
Lagen und Schnittstellen. Dadurch bleibt der Schuh mit dem Fuß verbunden und
passt weiterhin in alle vorhandenen Lochpositionen des Wickelrades.
Die nominale Auflage wird getrennt von der zulässigen Schulterüberhöhung
physisch geprüft; die Rotationseinhüllende umfasst den gesamten Schulterrand.

## Klebeband und Entnahme

- Alle drei Klebebandpassagen pro Schuh bleiben mindestens 12 mm breit in
  tangentialer und axialer Richtung.
- Die Passagen bleiben vollständig frei. Der radiale Fräser reicht bis zur
  höchsten Schulter plus 0,4 mm Überlauf (3,1 mm); Überlauf ist keine zusätzliche
  zugesicherte Nutzfreiheit. Es bleibt keine Restwand vor dem Klebeband.
- Das bestehende Prüfmodell verwendet weiterhin geschlossene Streifen mit
  10 mm tangentialer Breite, 4 mm radialer Stärke und 10 mm axialer Höhe bei
  0,25 mm Wandstärke.
- Die feste Drahtprüfhülle bleibt 9 mm axial breit mit 1 mm radialem Aufbau
  und 0,02 mm innerem Abstand zur nominalen Auflage. Bei größeren Einstellungen
  enthält sie die geraden gespannten Verbindungen zwischen den Kontaktbögen.
- Nach dem Lösen müssen alle sechs Schuhe bei 100, 150 und 200 mm kontinuierlich
  nach vorn entfernt werden können. Danach muss die gebundene Spule nach vorn
  austreten können.
- Nach dem Lösen beider Zungen wird jeder Schuh 40 mm rein axial vorgezogen,
  vollständig entspannt und anschließend 40 mm radial außen geparkt. Alle
  sechs Schuhe bleiben als getrennte Servicekörper vorhanden.
- Erst danach wird die feste Wicklung samt 18 geschlossenen Bandhüllen 120 mm
  nach vorn entnommen. Rad, Welle und Ständer bleiben montiert.
- Jede vollständige Translation wird kontinuierlich geprüft, zusätzlich zu
  Zwischenstellungen. Nachbarschuh-, Band-, Rad- und Ständerkollisionen sowie
  Hindernisse zwischen den Endpunkten müssen die Freigabe verhindern.
  Drahtdehnung, Bandschlupf oder radiale Schuhentlastung sind keine Annahmen.

## Druck und Freigabe

- Der Schuh bleibt ein einzelner gültiger, geschlossener und manifold
  druckbarer Körper aus PLA.
- Die bisherige Druckorientierung und das 220-mm-Druckbett bleiben gültig.
- Geänderte Schuh-, Baugruppen-, Zeichnungs- und Manifest-Artefakte werden
  deterministisch neu erzeugt.
- Der bestehende Wire-Payoff und die V5-Freigabe müssen byte-unverändert bleiben.
- Die digitale Freigabe ersetzt keine physische Prüfung von Drahtschutz,
  Passung, Entnahmekraft, Rastlebensdauer oder PLA-Ermüdung.

## Abnahmekriterien

1. Regressionen schlagen am Profil mit hoher Hinterschulter fehl und bestätigen
   nominalen Auslauf, hohe Vorderschulter und feste Wicklung ohne Kollision.
2. Alle elf Durchmessereinstellungen behalten identische Schuhgeometrie und
   korrekte Lochzuordnung.
3. Sämtliche Band-, Nachbarpassagen-, Mesh-, STEP-, Druckbett- und
   Entnahmeprüfungen bestehen.
4. Zwei vollständige Neuaufbauten liefern identische Release-Dateien.
5. Anleitung und Zeichnungen zeigen und benennen den nominalen hinteren Auslauf
   und die hohe freie Vorderschulter wahrheitsgemäß.
