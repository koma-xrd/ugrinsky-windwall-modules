# Asymmetrische Drahtmulde für den Wickelschuh

## Ziel

Der steckbare `winding_jig_contact_shoe` erhält eine durchgehend gerundete,
asymmetrische U-Auflage. Sie hält den lackierten Kupferdraht während des
Wickelns axial auf dem Schuh, ohne die spätere Entnahme der mit Klebeband
gebundenen Spule zu behindern.

Der Wire-Payoff bleibt vollständig unverändert.

## Profil und Bezugsmaße

- Der tiefste Punkt der U-Mulde liegt auf dem gewählten nominellen
  Wickelradius. Die Einstellung 100 mm erzeugt daher weiterhin eine nominelle
  100-mm-Wicklung; die Schultern dürfen diesen Bezugsdurchmesser nicht
  verkleinern.
- Die rad- beziehungsweise rückseitige Schulter steht etwa 2,5 bis 3,0 mm über
  dem Muldenboden. Sie bildet den stärkeren Schutz gegen axiales Abrutschen zum
  Rad.
- Die freie vordere Schulter steht etwa 1,0 bis 1,5 mm über dem Muldenboden.
  Sie führt den Draht, bleibt aber bewusst niedriger als die rückseitige
  Schulter.
- Muldenboden, Übergänge und beide Schultern sind stetig gerundet. Es gibt
  keine scharfen Kanten im Drahtkontaktbereich.
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

## Klebeband und Entnahme

- Alle drei Klebebandpassagen pro Schuh bleiben mindestens 12 mm breit in
  tangentialer und axialer Richtung.
- Die Passagen schneiden beide Schultern vollständig frei. Es darf keine dünne
  Restwand vor dem Klebeband entstehen.
- Das bestehende Prüfmodell verwendet weiterhin geschlossene Streifen mit
  10 mm tangentialer Breite, 4 mm radialer Stärke und 10 mm axialer Höhe.
- Nach dem Lösen müssen alle sechs Schuhe bei 100, 150 und 200 mm kontinuierlich
  nach vorn entfernt werden können. Danach muss die gebundene Spule nach vorn
  austreten können.
- Die niedrige freie Schulter darf diesen Weg nicht blockieren oder einen
  zusätzlichen Demontageschritt erfordern.

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

1. Ein Regressionstest schlägt am bisherigen flachen Schuh fehl und bestätigt
   am neuen Schuh die asymmetrischen Schulterhöhen sowie den nominellen
   Muldenradius.
2. Alle elf Durchmessereinstellungen behalten identische Schuhgeometrie und
   korrekte Lochzuordnung.
3. Sämtliche Band-, Nachbarpassagen-, Mesh-, STEP-, Druckbett- und
   Entnahmeprüfungen bestehen.
4. Zwei vollständige Neuaufbauten liefern identische Release-Dateien.
5. Anleitung und Zeichnungen zeigen und benennen die asymmetrische U-Mulde
   wahrheitsgemäß.
