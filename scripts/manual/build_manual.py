"""Build the German prototype manual from release data and E01–E11 drawings.

The document describes a measured development workflow, not a validated turbine.
Existing renderer PNGs allow the bundled document runtime to run without CAD.
If figures are absent, the corresponding renderer is invoked lazily and requires
its CAD dependencies. Release dimensions and STL paths come from the manifest.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(ROOT / 'src'))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.manual.manual_data import load_manual_data


PART_NAMES = {
    'P01': 'base_rotor_module', 'P02': 'standard_rotor_module',
    'P03': 'top_rotor_module', 'P04': 'top_closure', 'P05': 'lower_magnet_rotor',
}


def _paragraph(doc, text, *, lead=None):
    paragraph = doc.add_paragraph()
    if lead:
        paragraph.add_run(lead + ' ').bold = True
    paragraph.add_run(text)
    return paragraph


def _page(doc, title):
    heading = doc.add_heading(title, 1)
    heading.paragraph_format.page_break_before = True


def _steps(doc, steps):
    for number, text in enumerate(steps, 1):
        _paragraph(doc, text, lead=f'{number}.')


def _table(doc, headers, rows, widths, *, centered=()):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for column, width in zip(table.columns, widths):
        column.width = Mm(width)
    properties = table._tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        item = OxmlElement('w:' + edge)
        for key, value in (('val', 'single'), ('sz', '4'), ('color', 'D9D9D9')):
            item.set(qn('w:' + key), value)
        borders.append(item)
    properties.append(borders)
    margins = OxmlElement('w:tblCellMar')
    for edge, size in (('top', 90), ('bottom', 90), ('left', 100), ('right', 100)):
        item = OxmlElement('w:' + edge)
        item.set(qn('w:w'), str(size))
        item.set(qn('w:type'), 'dxa')
        margins.append(item)
    properties.append(margins)
    header = OxmlElement('w:tblHeader')
    table.rows[0]._tr.get_or_add_trPr().append(header)
    for row_index, values in enumerate([headers, *rows]):
        row = table.rows[0] if row_index == 0 else table.add_row()
        no_split = OxmlElement('w:cantSplit')
        row._tr.get_or_add_trPr().append(no_split)
        for column_index, (cell, text, width) in enumerate(zip(row.cells, values, widths)):
            cell.width = Mm(width)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            fill = '253C50' if row_index == 0 else ('F2F5F7' if row_index % 2 else 'FFFFFF')
            shading = OxmlElement('w:shd')
            shading.set(qn('w:fill'), fill)
            cell._tc.get_or_add_tcPr().append(shading)
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(0)
            paragraph.paragraph_format.line_spacing = 1.03
            if column_index in centered:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = paragraph.add_run(str(text))
            run.font.size = Pt(10)
            if row_index == 0:
                run.bold = True
                run.font.color.rgb = RGBColor.from_string('FFFFFF')
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def _figure_paths(project_root, data):
    paths = {key: project_root / item['figure_file'] for key, item in data['drawings'].items()}
    missing = {key for key, path in paths.items() if not path.is_file()}
    if missing & {f'E{i:02}' for i in range(1, 7)}:
        from scripts.manual.cad_figures import render_cad_figures

        for record in render_cad_figures(project_root, project_root / 'output/manual-figures'):
            paths[record.drawing_id] = record.path
    if missing & {f'E{i:02}' for i in range(7, 12)}:
        from scripts.manual.electrical_figures import render_electrical_figures

        for record in render_electrical_figures(project_root, project_root / 'output/manual-figures'):
            paths[record.drawing_id] = record.path
    return paths


def _figure(doc, drawing_id, data, paths):
    drawing = data['drawings'][drawing_id]
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.keep_with_next = True
    paragraph.paragraph_format.space_after = Pt(3)
    image = paragraph.add_run().add_picture(str(paths[drawing_id]), width=Mm(174))
    image._inline.docPr.set('descr', f"{drawing_id}: {drawing['description']}")
    image._inline.docPr.set('title', drawing['title'])
    caption = doc.add_paragraph(f"{drawing_id}  {drawing['title']}", style='Caption')
    caption.paragraph_format.keep_together = True


def _setup_document():
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.left_margin = section.right_margin = Mm(18)
    section.top_margin, section.bottom_margin = Mm(16), Mm(17)
    section.footer_distance = Mm(8)
    for name, size in (('Normal', 11), ('Title', 27), ('Heading 1', 18),
                       ('Heading 2', 13), ('Caption', 10)):
        style = doc.styles[name]
        style.font.name = 'Arial'
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string('000000')
        style.paragraph_format.space_after = Pt(7)
        style.paragraph_format.line_spacing = 1.08
        style.paragraph_format.widow_control = True
        if name in ('Title', 'Heading 1', 'Heading 2'):
            style.paragraph_format.keep_with_next = True
            style.paragraph_format.space_before = Pt(0 if name != 'Heading 2' else 8)
        if name == 'Caption':
            style.font.italic = False
    lang = OxmlElement('w:lang')
    lang.set(qn('w:val'), 'de-DE')
    doc.styles['Normal'].element.get_or_add_rPr().append(lang)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer.add_run('Ugrinsky Bauanleitung  |  ').font.size = Pt(9)
    field = OxmlElement('w:fldSimple')
    field.set(qn('w:instr'), 'PAGE')
    footer._p.append(field)
    doc.core_properties.title = 'Ugrinsky Wind Wall Bauanleitung'
    doc.core_properties.subject = 'Deutscher Werkstattablauf für einen unvalidierten Prototyp'
    doc.core_properties.author = 'Windwall Projekt'
    return doc


def _scope(doc, data):
    dimensions = data['dimensions']
    mm = lambda value: f'{value:.2f}'.replace('.', ',')
    doc.add_paragraph('Ugrinsky Wind Wall\nBauanleitung', style='Title')
    _paragraph(doc, 'Siebenstufiger Rotor mit experimentellem Axialflussgenerator\nStand 9. September 2026')
    doc.add_heading('1 Umfang und Prototypstatus', 1)
    _paragraph(doc, 'Diese Anleitung führt vom Passungscoupon über den mechanischen Aufbau bis zu vergleichbaren Testspulenmessungen. Sie richtet sich an erfahrene Maker mit Messmitteln und einem geschützten Prüfplatz. Erst die dokumentierten Versuche erlauben die Auswahl von Wicklung, Lagerung und Ladeelektronik.')
    _paragraph(doc, 'Die STL-Dateien sind Produktionskandidaten. Passung, PLA-Festigkeit, Magnetrückhaltung, Lagerhalterung, Überdrehzahl, elektrische Funktion und Außenbetrieb sind noch nicht physisch validiert. Es gibt keine zugesicherte Leistung oder sichere Betriebsdrehzahl.', lead='Prototyp:')
    doc.add_heading('Hauptmaße aus dem CAD Modell', 2)
    _table(doc, ['Größe', 'Nennwert', 'Bedeutung'], [
        ('Stufen', '7', '1 Basis + 5 Standard + 1 Top'),
        ('Rotordurchmesser', mm(dimensions['rotor_diameter_mm']) + ' mm', 'Aerodynamischer Außendurchmesser'),
        ('Belastete Teilung', mm(dimensions['loaded_stage_pitch_mm']) + ' mm', 'Axialer Abstand verriegelter Stufen'),
        ('Aerodynamische Höhe', mm(dimensions['loaded_height_mm']) + ' mm', 'Gesetzter Sieben-Stufen-Stack'),
        ('Modellierte Stangenhülle', mm(dimensions['rod_envelope_mm']) + ' mm', 'Kein verbindliches Zuschnittmaß'),
        ('Luftspalt je Seite', '1,5 mm nominal', 'Nur mit bündigen oder versenkten Magneten'),
    ], [49, 38, 87])
    _paragraph(doc, 'Die reale M8-Stangenlänge folgt dem gemessenen Stack samt Muttern, Scheiben, Lagerung und externen Stützen. Erst trocken aufbauen, erforderliche Gewindeeingriffe und Freigänge prüfen, danach ablängen und entgraten.')
    _paragraph(doc, 'Generator nicht direkt mit dem Akku verbinden.', lead='Elektrische Sicherheit:')


def _boms(doc, data, manifest):
    _page(doc, '2 Druckteile und STL Dateien')
    _paragraph(doc, 'Für einen Rotor werden neun Druckkörper aus fünf unterschiedlichen STL-Dateien benötigt. Der obere Magnetträger ist bereits Teil von P01. Mengen und Pfade folgen dem Release-Manifest; die Pfade gelten relativ zu build/.')
    released = {part['name']: part for part in manifest['production_parts']}
    rows = []
    for part_id, item in data['printed_parts'].items():
        record = released[PART_NAMES[part_id]]
        rows.append((part_id, item['quantity'], item['description'], record['stl_path']))
    _table(doc, ['ID', 'Stück', 'Druckkörper', 'STL Referenz'], rows, [13, 15, 69, 77], centered=(0, 1))
    doc.add_heading('Coupons vor den großen Teilen', 2)
    _table(doc, ['Coupon', 'STL Referenz', 'Prüfzweck'], [
        ('Magnettaschen', 'coupons/magnet_pocket_coupon.stl', '10,8 / 11,0 / 11,2 mm; Tiefe 2 mm'),
        ('Bajonettpaar', 'coupons/bayonet_male.stl\ncoupons/bayonet_female.stl', 'Einsetzen und Verriegeln'),
        ('Verbindungspaar', 'coupons/joint_male.stl\ncoupons/joint_female.stl', 'Treiber und Rückhalter im Zusammenspiel'),
    ], [35, 80, 59])
    _paragraph(doc, 'Stehendes Generatorgehäuse, Wickelraum und Deckel sowie Lager- und Distanzhüllen sind provisorische Referenzgeometrien der Gesamtbaugruppe. Sie gehören nicht zu den fünf aufgeführten STL-Kandidaten. Die Befestigung des Stators und die externe Abstützung müssen konstruiert und geprüft werden; diese Anleitung ersetzt dafür keine Fertigungszeichnung.', lead='Abgrenzung:')

    _page(doc, '3 Kaufteile für Aufbau und Versuche')
    _paragraph(doc, 'Erforderlich bedeutet hier: für den geplanten Prototyp vorgesehen. Reale Maße, Werkstoffe und Eignung bleiben zu prüfen. Schraubenlängen nicht ungeprüft in abweichende Druckteile übernehmen.')
    ids = ('H01', 'H02', 'H03', 'H04', 'H05', 'H08', 'H09', 'H10', 'H11', 'H17')
    rows = [(key, data['hardware'][key]['quantity'], data['hardware'][key]['description'],
             data['hardware'][key]['specification']) for key in ids]
    _table(doc, ['ID', 'Menge', 'Bauteil', 'Vorgabe und Prüfbedarf'], rows, [12, 19, 57, 86], centered=(0, 1))

    _page(doc, 'Kaufteile mit offener Auswahl')
    doc.add_heading('Provisorische Lagerung und Distanzierung', 2)
    rows = [(key, data['hardware'][key]['quantity'], data['hardware'][key]['description'],
             data['hardware'][key]['specification']) for key in ('H06', 'H07')]
    _table(doc, ['ID', 'Menge', 'Referenz', 'Offene Prüfung'], rows, [12, 19, 57, 86], centered=(0, 1))
    doc.add_heading('Elektronik nach den Messungen auswählen', 2)
    rows = [(key, data['hardware'][key]['description'], 'Nach Messung auswählen')
            for key in ('H12', 'H13', 'H14', 'H15', 'H16')]
    _table(doc, ['ID', 'Funktion', 'Bemessung'], rows, [14, 99, 61], centered=(0,))
    _paragraph(doc, 'Für H12 bis H16 sind Spannungsfestigkeit, Dauer- und Fehlerstrom, Kühlung, Abschaltvermögen und Leiterquerschnitt offen. Ein nominelles 48-V-System liefert dafür keine ausreichende Dimensionierung. Auch der Ladealgorithmus muss zum konkreten Nass-, AGM- oder Gel-Akku passen.')
    doc.add_heading('Werkzeuge und Prüfmittel', 2)
    _paragraph(doc, 'Bereitlegen: Messschieber, Mikrometer für Draht, Tiefenmaß, Fühlerlehren, Winkelmarkierung, passende M3-Werkzeuge und M8-Schlüssel, Drehzahlmesser, geeignetes True-RMS-Multimeter, Widerstandsmessung, Temperaturfühler und definierte Leistungswiderstände. Für kleine Spulenwiderstände Messleitungswiderstand abziehen oder Vierleitermessung verwenden.')
    _paragraph(doc, 'Zusätzlich erforderlich sind Schutzbrille, Trennstücke für Magnete, eine stabile nichtmagnetische Montagehilfe, Berührungsschutz und eine sichere mechanische Stillsetzmöglichkeit. Der Prüfplatz muss lose Teile zurückhalten und von Personen getrennt sein.')


def _printing(doc):
    _page(doc, '4 Druck und Vorbereitung')
    doc.add_heading('PLA Prototyp auf dem Bambu Lab P2S', 2)
    _paragraph(doc, 'Ausgangspunkt ist der Bambu Lab P2S mit 0,4 mm Düse und vorhandenem PLA. Die folgenden Einstellungen sind Versuchsempfehlungen, keine Druckfreigabe. Zuerst alle Coupons mit demselben Filament und Profil wie die späteren Teile drucken.')
    _steps(doc, [
        'STL in Millimetern und unverändertem Maßstab importieren. Die Exportdateien stehen mit ihrer Unterseite bei Z = 0. In der Schichtvorschau prüfen, welche Nabe oder Fläche tatsächlich aufliegt und wo die Magnettaschen liegen.',
        'Als Start 0,20 mm Schichthöhe und das zum Filament passende Herstellerprofil verwenden. Temperaturen, Bauplatte und Kühlung nach Filament- und Druckerhinweisen einstellen; kein unbekanntes Universalprofil übernehmen.',
        'An belasteten Naben, Bajonetten und Treibern zunächst 5 bis 6 Wandlinien und 5 bis 6 Deckschichten prüfen. Für größere Innenräume 30 bis 40 Prozent Infill als Versuchswert wählen. Die Vorschau muss zusammenhängende tragende Wände zeigen; mehr Infill ersetzt keine gute Schichthaftung.',
        'Support nur dort einsetzen, wo die Vorschau ungestützte kritische Flächen zeigt. Kontaktflächen, Rampen und Magnettaschen müssen danach vollständig zugänglich sein. Eine Stützstruktur darf keine Passfläche dauerhaft verformen.',
        'Teile abkühlen lassen, entnehmen und Stützreste vorsichtig entfernen. Grate und Elefantenfuß abtragen, ohne Rampen, Treiber oder Taschengrund zu verändern. Fehlerhafte Schichten und Risse führen zum Aussortieren.',
    ])
    doc.add_heading('Coupon Prüfungen', 2)
    _table(doc, ['Prüfung', 'Vorgehen', 'Weiter erst wenn'], [
        ('Bajonett und Naht', 'Trocken einsetzen, von Hand verriegeln, erneut lösen.', 'Kein Zwang, kein Riss und vollständiges Setzen.'),
        ('Magnettasche', 'Reale Magnete in 10,8 / 11,0 / 11,2 mm prüfen; Tiefe und Überstand messen.', 'Passung, Klebespalt und Rückhaltung sind dokumentiert.'),
        ('M3 und M8', 'Pilotloch, Gewindeeingriff, Scheibenauflage und Werkzeugzugang prüfen.', 'Schrauben greifen, ohne Wände zu sprengen.'),
    ], [37, 75, 62])
    _paragraph(doc, 'ASA ist eine spätere Materialvariante. Dafür Trocknung, Lüftung, Temperaturen und Druckraumführung nach dem konkreten Herstellerprofil festlegen. Wegen anderer Schrumpfung alle Coupons, Belastungs- und Retentionsprüfungen wiederholen. Ein Materialwechsel allein validiert weder Wetterfestigkeit noch Dauerbetrieb.')


def _generator(doc, data, paths):
    _page(doc, '5 Generator mechanisch montieren')
    _paragraph(doc, 'Zunächst ohne Magnete und ohne elektrische Verbindung arbeiten. E02 trennt rotierende Druckteile von stehenden, noch provisorischen Hüllen. Im fertigen Versuch muss der Stator sicher gegen Mitdrehen und die Lagerung gegen axiales Wandern gehalten sein.')
    _figure(doc, 'E02', data, paths)
    _steps(doc, [
        'P01 und P05 auf Ebenheit, Risse und freie M8-Bohrung prüfen. Gewindestange rollen lassen und auf Geradheit prüfen; Grate entfernen. Bei klemmender Bohrung die Ursache messen, keine Stange einschlagen.',
        'Basis-Klemmstelle H02 in P01 trocken einsetzen. Stehende Teile auf einer stabilen Versuchshalterung ausrichten. Für H06 weder Lagerprodukt noch Presssitz aus der 12 × 8 × 6-mm-Hülle ableiten.',
        'P05, H07 und die untere Scheiben-/Mutternstelle entsprechend E02/E06 trocken ordnen. Die reale H07-Länge so bestimmen, dass die Magnetflächen parallel stehen und alle stehenden Teile freigängig bleiben.',
        'Lager und Stator separat abstützen. Erst nach bestätigter axialer Halterung und Abgrenzung aller drehenden Flächen mit Magneten weiterarbeiten. Wenn die Halterung noch fehlt, endet der Aufbau am Trockenversuch.',
    ])
    _page(doc, '6 Magnetträger vorbereiten')
    _figure(doc, 'E03', data, paths)
    _paragraph(doc, 'P01 trägt den oberen Magnetring integriert; P05 ist der untere separate Rotor. Insgesamt werden 36 nominal 10 x 2 mm große Scheibenmagnete H10 benötigt, 18 je Rotor. Jede Scheibe vor Einbau auf Ausbrüche, Beschichtungsschäden, Durchmesser und Dicke prüfen.')
    _paragraph(doc, 'Die modellierten Taschen sind 11 mm weit und 2 mm tief. Ein Magnetnennmaß von 10 mm garantiert weder einen geeigneten Klebespalt noch ausreichende Rückhaltung. Mit dem Coupon 10,8 / 11,0 / 11,2 mm die echte Druckpassung ermitteln und magnetischen Überstand mit Tiefenmaß dokumentieren.')
    _paragraph(doc, 'Neodym-Magnete können Finger einklemmen und beim Zusammenprall splittern. Schutzbrille tragen, einzelne Magnete mit nichtmagnetischen Abstandhaltern führen und Werkzeug sowie lose Metallteile fernhalten. Abstand zu empfindlicher Elektronik und medizinischen Implantaten gemäß Magnet- und Gerätehinweisen einhalten.', lead='Starke Magnete:')
    _paragraph(doc, 'H11 ist noch zu entwickeln: Kleber allein ist kein nachgewiesener Schutz gegen Ablösung und Fliehkraft. Klebstoffverträglichkeit, Aushärtung und eine formschlüssige Rückhaltung am Coupon prüfen; dabei einen vollständig abgeschirmten Versuch verwenden.', lead='Vor Rotation:')

    _page(doc, 'Magnete im Trockenlayout prüfen')
    _figure(doc, 'E07', data, paths)
    _steps(doc, [
        'Rotoren eindeutig als oben und unten kennzeichnen. Die wirksamen, einander zugewandten Magnetflächen nummerieren. E07 zeigt beide Flächenseiten; vor dem Umdrehen die Lage der ersten Tasche markieren.',
        'Einen Referenzmagneten mit bekannter Polung oder einen geeigneten Polprüfer verwenden. Magnete einzeln prüfen und die sichtbare Polfläche markieren. Ohne Nordreferenz zumindest zwei eindeutige komplementäre Gruppen festlegen und später die Gegenüberstellung prüfen.',
        'Je Rotor benachbarte Pole abwechselnd N–S anordnen. An jedem Umfangsplatz müssen sich die gegenüberliegenden Magnetflächen anziehen. Gleiche Pole dürfen sich dort nicht gegenüberstehen. Mit Abstandhaltern prüfen und jedes Paar im Protokoll abhaken.',
        'Erst nach vollständigem Trockenlayout, Coupon und geprüfter Rückhaltung kleben. Flächen nach Klebstoffanweisung vorbereiten, Magnetlage kontrollieren und vollständig aushärten lassen. Rotoren bis dahin getrennt sichern.',
    ])
    _paragraph(doc, 'Magnetringe niemals ungebremst zusammenschnappen lassen. Zum Zusammenführen eine steife Montageführung und nichtmagnetische Distanzstücke benutzen; Finger aus dem Spalt halten.', lead='Quetschgefahr:')

    _page(doc, 'Luftspalte und Lagerung einstellen')
    _figure(doc, 'E06', data, paths)
    _paragraph(doc, 'Der Nennluftspalt beträgt 1,5 mm auf jeder Statorseite. Dieses CAD-Maß setzt bündige oder versenkte Magnete voraus. Ein Überstand verkleinert den realen Freigang. Kleber, Wicklung, Isolierung und Rückhaltebauteile müssen bei der realen Messung berücksichtigt werden.')
    _steps(doc, [
        'Stehende Wicklungsaufnahme provisorisch, aber formstabil fixieren. Die Hüllen des Wickelraums (118 mm außen, 12,4 mm Bohrung, 12 mm hoch) sowie des Deckels sind Platzhalter; daraus folgt keine vollständig nutzbare Wicklungshöhe.',
        'An mehreren Umfangsstellen oben und unten den kleinsten realen Freigang messen. Rotor zunächst von Hand vollständig drehen. Axiales Spiel, Taumeln und Verformung unter der Klemmung separat erfassen.',
        'Bei Kontakt oder schwankendem Spalt anhalten und Ursache korrigieren. Einen schleifenden Rotor nicht durch Anziehen der M8-Mutter freiziehen. Nach jeder Änderung von Wicklung, Klebung oder Lagerung erneut prüfen.',
    ])
    _paragraph(doc, 'Für einen Drehversuch müssen reale Lagerwahl, Sitz, axiale Halterung und Statorbefestigung nachgewiesen sein. Eine kollisionsfreie CAD-Hülle erfüllt diese Bedingungen noch nicht.', lead='Prüfstopp:')


def _winding(doc, data, paths):
    _page(doc, '7 Durchgehende Testwicklung herstellen')
    _paragraph(doc, 'Die luftkernige Serpentinen-Testwicklung folgt einem durchgehenden Leiterpfad zwischen Innen- und Außenradius. Sie ist eine experimentelle Spule. Drahtdurchmesser, Windungszahl und fertige Verschaltung stehen erst nach den Messungen fest.')
    _figure(doc, 'E08', data, paths)
    _steps(doc, [
        'Mit dem vorhandenen nominalen 0,18 mm Kupferlackdraht beginnen. Den Durchmesser über der Emaille an mehreren Stellen mit einem Mikrometer und geringer Messkraft erfassen. Spule, Drahtcharge und Messwert beschriften.',
        'Startende A1 mit ausreichend Anschlussreserve markieren und weich an der Schablone fixieren. Den Pfad in einer einzigen fortlaufenden Richtung verfolgen. Nicht nach einem Sektor umkehren oder einzelne Teilspulen ohne Verschaltungsplan anfügen.',
        'Von Pin zu Pin abwechselnd Innen- und Außenradius anlaufen. Die 18 radialen Schenkel folgen E08. Eine Windung ist ein vollständiger Umlauf des Serpentinenpfads; die 18 Schenkel sind keine 18 einzelnen Windungen.',
    ])

    _page(doc, 'Wickelschablone und Varianten')
    _figure(doc, 'E09', data, paths)
    _steps(doc, [
        'Eine steife ebene Schablone vorbereiten. Glatte, abgerundete und elektrisch isolierte Pins verwenden. Pinlage aus dem gemessenen Wickelraum ableiten; E09 ist eine Prinzipskizze, keine ungeprüft maßstäbliche Bohrschablone.',
        '20 vollständige Umläufe locker und gleichmäßig wickeln. Jeden Umlauf zählen, den Draht ohne Knicke führen und Kreuzungen vermeiden. Dann getrennte 40- und 80-Windungs-Testspulen nur anfertigen, wenn die gemessenen Außen-, Innen- und Höhenmaße Platz lassen.',
        'Nicht durch starkes Ziehen, Pressen oder erzwungenes Packen passend machen. Bei Platzmangel Variante abbrechen, Maße dokumentieren und Schablone oder Drahtauswahl erneut bewerten.',
        'Die Spule noch auf den Pins an mehreren Stellen mit weichem Band oder Faden binden. Erst danach vorsichtig abheben, Ende A2 markieren, Emaille unter Vergrößerung auf Schäden prüfen und Anschlussenden zugentlasten.',
        'Durchgang, Widerstand und Außen-/Innenmaß sowie maximale Höhe messen. Auffällige Widerstandssprünge oder beschädigte Emaille bedeuten Nacharbeit beziehungsweise Verwerfen. Bis die Tests ein Design auswählen, nicht vergießen.',
    ])


def _measurements(doc, data, paths):
    _page(doc, '8 Testspulen vergleichbar messen')
    _figure(doc, 'E10', data, paths)
    _paragraph(doc, 'Alle Varianten bei gleicher Drehzahl, Magnetanordnung, Luftspalt und vergleichbarer Ausgangstemperatur messen. Spulennummer, tatsächliche Windungszahl, Drahtdurchmesser über Emaille, Messgerät und Messbereich aufzeichnen. Ein Leerlaufspannungswert allein ist kein Leistungsnachweis.')
    _steps(doc, [
        'Bei stillgesetztem Rotor isolierte Messleitungen verlegen und sichern. Drehzahlmarker befestigen, Schutzhaube schließen. Im Leerlauf das True-RMS-Voltmeter zwischen A1 und A2 anschließen; keine Batterie verwenden.',
        'Langsam auf eine vorher begrenzte Prüfdrehzahl bringen. Drehzahl und AC-Leerlaufspannung gemeinsam aufnehmen. Rotor mechanisch stillsetzen, bevor Leitungen oder Messbereiche umgesteckt werden.',
        'Eine definierte Last mit gemessenem Widerstand und ausreichender Wärmeabfuhr anschließen. Das Amperemeter liegt in Reihe, das Voltmeter parallel zur Last. Laststrom, Lastspannung, Drehzahl, Anfangs-/Endtemperatur und Laufzeit protokollieren.',
        'Die optionale DC-Messung separat hinter einem passend bemessenen Gleichrichter aufbauen. AC-RMS- und DC-Werte nicht vermischen. Niemals ein Amperemeter direkt über eine Spannungsquelle legen.',
    ])

    _page(doc, 'Messwerte auswerten und Wicklung wählen')
    doc.add_heading('Spannung pro Windung', 2)
    _paragraph(doc, 'Für jede passende Testspule den Quotienten AC-Leerlaufspannung / Windungszahl bei identischer Drehzahl berechnen. Stark unterschiedliche Quotienten sprechen für eine geänderte Geometrie, Polung, Messbedingung oder einen Wicklungsfehler und müssen vor einer Hochrechnung untersucht werden.')
    _paragraph(doc, 'N_final = N_test * V_ac_target / V_ac_test')
    _paragraph(doc, 'Das Ergebnis auf die nächste ganze Windung aufrunden. N_test ist die gezählte Windungszahl der vermessenen Testspule; V_ac_test ihre gemessene AC-Spannung bei der festgelegten Drehzahl. V_ac_target ist das für die spätere Elektronik begründete AC-Ziel unter derselben Vergleichsbedingung. V_ac_test muss größer als null sein.')
    _paragraph(doc, 'Die Formel ist eine erste lineare Abschätzung bei gleicher Geometrie und Drehzahl. Mehr Windungen ändern Platzbedarf und Widerstand. Die berechnete Spule muss erneut auf Passung, Lastspannung und Temperatur geprüft werden. N_final bezeichnet den Rechenwert, keine freigegebene Endwicklung.')
    _paragraph(doc, '48 V ist die nominale Batteriespannung, nicht automatisch V_ac_target. Tatsächliche Ladespannung, Gleichrichterverluste, Regler-Eingangsbereich, Anlauf und Spannung unter Last bestimmen das Ziel. Kein universeller AC-zu-DC-Faktor ersetzt die Messung an dieser Wellenform.')
    doc.add_heading('Vergleichsentscheidung', 2)
    _table(doc, ['Kriterium', '20 Windungen', '40 Windungen', '80 Windungen'], [
        ('Passt ohne Druck', '____', '____', '____'),
        ('AC Volt pro Windung', '____', '____', '____'),
        ('Widerstand bei T₀', '____', '____', '____'),
        ('Spannung an gleicher Last', '____', '____', '____'),
        ('Erwärmung nach gleicher Zeit', '____', '____', '____'),
        ('Weitere Prüfung erforderlich', '____', '____', '____'),
    ], [66, 36, 36, 36])
    _paragraph(doc, 'Bei zu hohem Widerstand oder Platzmangel auch andere tatsächlich gemessene Drahtdurchmesser untersuchen. Einen größeren Durchmesser nicht aus einer vermuteten Generatorleistung ableiten. Erst nach stabilen Messreihen eine Wicklung auswählen und danach Isolierung, Fixierung und gegebenenfalls Verguss gesondert erproben.')


def _rotor(doc, data, paths):
    _page(doc, '9 Sieben Stufen montieren')
    _figure(doc, 'E01', data, paths)
    _paragraph(doc, 'Von unten nach oben folgen Basis P01, fünf identische P02 und Top P03. P04 schließt oben ab. Vor dem Stapeln alle sechs Nahtstellen mit Coupons erproben; nur saubere, unbeschädigte Fügeteile verwenden.')
    _steps(doc, [
        'Die Basis auf der geraden M8-Stange und einer stabilen Montagehilfe ausrichten. Generatorteile gegen unkontrollierte Magnetkräfte sichern. Blätter nicht als Schraubstockflächen oder Hebel verwenden.',
        'Ein P02 auf die Welle führen, Einsetzstellung gemäß E04 wählen, bis zum vollständigen Eingriff absenken und gegen den Uhrzeigersinn verriegeln. Nach jeder Stufe Sitz und Freigang prüfen.',
        'Die übrigen vier P02 und danach P03 gleichartig fügen. Im verriegelten Zustand sind die Modulreferenzen ausgerichtet. Die interne Blattverdrehung von +60° bleibt erhalten; an jeder ausgerichteten Naht entsteht der bewusst beibehaltene Phasensprung von -60°.',
    ])
    _paragraph(doc, 'Die belastete Teilung beträgt 69,64 mm und die aerodynamische Gesamthöhe 487,84 mm. Einzelteile sind mit ihren Verbindungsgeometrien höher als die wirksame Teilung; deshalb nicht sieben STL-Hüllhöhen addieren.')

    _page(doc, 'Bajonett und Rückhalteschrauben')
    _figure(doc, 'E04', data, paths)
    _steps(doc, [
        'Von oben gesehen ist die Einsetzstellung -18° relativ zur verriegelten Nullstellung, also 18° im Uhrzeigersinn. Die Vorzeichen beziehen sich auf eine positive CCW-Richtung.',
        'Drei Nasen durch die Einführungen führen und axial vollständig einsetzen. Das obere Teil um 18° gegen den Uhrzeigersinn bis zum Sitz verriegeln. CCW bedeutet counterclockwise, von oben gesehen gegen den Uhrzeigersinn; die geplante Rotation zieht die Verbindung in dieser Richtung selbst nach.',
        'Prüfen, dass beide Treiber vollständig greifen und die Naht geschlossen ist. Klemmt die Verbindung vor dem Sitz, wieder lösen und Passung prüfen. Schrauben dürfen diesen Arbeitsschritt nicht erzwingen.',
        'Je Naht zwei radiale H04 vorsichtig einsetzen, zusammen zwölf an sechs Nähten. Die nominalen M3 × 12-mm-Rückhalter verhindern das Rückdrehen und Lösen. Gewindeeingriff am Coupon prüfen; überdrehte oder gerissene Aufnahmen ersetzen.',
    ])
    _paragraph(doc, 'Die M3-Nahtschrauben ziehen die Verbindungen nicht zusammen und tragen keine M8-Vorspannung. Die axialen Sitzflächen und M8-Klemmung müssen unabhängig davon korrekt funktionieren.', lead='Lastpfad:')

    _page(doc, '10 Top Klemmung und Abschluss')
    _figure(doc, 'E05', data, paths)
    _steps(doc, [
        'Vor P04 die obere H03-Scheibe eben auf ihre vorgesehene Auflage setzen. H02 zugänglich aufschrauben und mit passendem Werkzeug gegenhalten. Die Kraft darf nicht über Blattkanten oder Abdeckung laufen.',
        'Den vollständig gesetzten Stack vorsichtig mit M8 klemmen. Es gibt kein validiertes Anzugsdrehmoment für diese PLA-Konstruktion. Nicht nach einem Stahl-Schraubentabellenwert anziehen; bei Verformung, Knacken oder blockiertem Lager sofort lösen und untersuchen.',
        'Rundlauf an Welle, Magnetflächen und Rotorumfang messen. Welle über eine volle Umdrehung von Hand bewegen und kleinsten Spalt protokollieren. Nach der Klemmung muss die Lagerung weiterhin frei laufen.',
        'P04 aufsetzen und mit zwei H05 lösbar befestigen. Die Abdeckung übernimmt keine M8-Klemmkraft. Werkzeugzugang und spätere Demontage kontrollieren; die M8-Stange darf nicht gegen den Deckel drücken.',
    ])
    _paragraph(doc, 'Für die Balance den Rotor bei stiller Umgebung in mehreren Startlagen prüfen. Wiederholt nach unten laufende schwere Stellen zuerst auf falsch sitzende Teile oder Kleberüberschuss untersuchen. Keine ungesicherten Ausgleichsgewichte ankleben. Dynamische Balance und zulässiger Rundlauf bleiben Prüfaufgaben.')


def _safety(doc, data, paths):
    _page(doc, '11 Ladekette und elektrische Sicherheit')
    _figure(doc, 'E11', data, paths)
    _paragraph(doc, 'Generator nicht direkt mit dem Akku verbinden.', lead='Verbot:')
    _paragraph(doc, 'Die Funktionskette lautet: Generator → geeignet bemessener Gleichrichter → Überstromschutz → Wind-Laderegler mit Diversion/Dump Load → batterieseitige Sicherung → 48-V-Bleiakku-Bank. Alle elektrischen Bemessungswerte: Nach Messung auswählen.')
    _paragraph(doc, 'E11 zeigt Funktionen und keine universelle Klemmenbelegung. Diversionsregler können geräteabhängig parallel zur Batterie arbeiten. Den konkreten Anschlussplan, die Anschlussreihenfolge, Ladegrenzen und Fehlerfallreaktionen aus dem gewählten Reglerhandbuch übernehmen. Ein reiner Solarladeregler ist nicht automatisch geeignet.')
    _paragraph(doc, 'Die Überschusslast muss die nachgewiesene maximal mögliche Quellenleistung unter den vorgesehenen Bedingungen aufnehmen können, ohne den Regler zu überlasten. Sie wird heiß und braucht sichere Wärmeabfuhr sowie Berührungsschutz. Der Morningstar-Herstellerleitfaden [S2] erläutert die grundsätzliche Diversionsbemessung; seine Produktwerte sind keine Auswahl für diesen Prototyp.')
    _paragraph(doc, 'Batterien liefern sehr hohe Kurzschlussströme. Schmuck ablegen, isolierte Werkzeuge verwenden, Pole abdecken und Polarität vor Anschluss messen. Sicherungen passend zu Leitungen, DC-Spannung und Abschaltvermögen nahe der jeweiligen Quelle anordnen; H16 nahe dem Batterieanschluss.', lead='Kurzschluss und Verpolung:')

    _page(doc, '12 Inbetriebnahme und Betriebssicherheit')
    doc.add_heading('Vor dem ersten Drehversuch', 2)
    _steps(doc, [
        'Alle mechanischen Prüfungen dokumentieren: Magnetrückhaltung, Lagerhaltung, Statorfixierung, sechs Nähte, M8-Klemmung, Luftspalte und freie Handdrehung. Offene Retentions- oder Lagerfragen schließen einen angetriebenen Versuch aus.',
        'Stabile Befestigung, Schutzhaube und sicheren Abstand herstellen. Haare und Kleidung sichern. Niemals bei laufendem Rotor an Welle, Blätter oder Leitungen greifen. Handschuhe nur bei stillgesetzter Montage einsetzen, nicht an drehenden Teilen.',
        'Mit begrenztem Antrieb langsam beginnen und von außerhalb des Gefahrenbereichs beobachten. Vorher festlegen, wie der Antrieb gestoppt und der Rotor mechanisch gesichert wird. Unbekannte Überdrehzahl nicht im freien Wind erproben.',
        'Drehzahl, Geräusch, Schwingung und Temperatur in kurzen Läufen überwachen. Bei steigender Temperatur, Schleifen, Rissen, Lockern oder Vibration sofort stoppen. Nach Stillstand sichern und alle Verbindungen erneut prüfen.',
    ])
    _paragraph(doc, 'Generator und Widerstandslast können heiß werden. Vor Berührung abkühlen lassen. Keine provisorischen Leitungen an rotierenden Teilen entlangführen. Eine abgetrennte elektrische Last kann die Drehzahl erhöhen; vor dem Trennen den Rotor mechanisch stillsetzen.', lead='Wärme und Überdrehzahl:')
    _paragraph(doc, 'Beim Laden von Bleiakkus kann Wasserstoff entstehen. Gut belüftet arbeiten, Zündquellen und Funken fernhalten. Den konkreten Akkutyp und sein Herstellerhandbuch beachten; Ladeprofil und Temperaturkompensation passend einstellen. AGM- und Gel-Akkus nicht öffnen oder nachfüllen. Hinweise nach Trojan [S1] und dem Handbuch der tatsächlich verwendeten Batterie.', lead='Batterie und Lüftung:')
    _paragraph(doc, 'Dieser Prototyp ist nicht gegen Feuchtigkeit validiert. Trocken und kontrolliert prüfen, bei Kondensation oder Nässe nicht betreiben. PLA, offene Lagerung und provisorische Elektronik sind keine Außeninstallation. Den Aufbau niemals unbeaufsichtigt laufen oder laden lassen.', lead='Umgebung und Aufsicht:')

    _page(doc, '13 Wartung und Fehlersuche')
    _paragraph(doc, 'Vor jeder Arbeit Rotor stillsetzen, mechanisch sichern und elektrische Quellen nach dem gerätespezifischen Trennplan isolieren. Erst nach Spannungsprüfung an Leitungen arbeiten. Ein Windrotor kann sich unerwartet wieder in Bewegung setzen.')
    doc.add_heading('Prüfung vor und nach jedem Versuch', 2)
    _paragraph(doc, 'Magnetmarkierungen und Rückhaltung, Klebefugen, Nahtschrauben, M8-Sitz, Risse und Verformung prüfen. Rundlauf und Luftspalt mit dem Ausgangsprotokoll vergleichen. Drahtausgänge, Zugentlastung und Isolierung kontrollieren. Laufzeit, Höchsttemperatur und Änderungen aufzeichnen. Nach Materialwechsel oder Umbau die betroffenen Coupon- und Belastungstests wiederholen.')
    _table(doc, ['Beobachtung', 'Mögliche Ursache', 'Prüfung bei Stillstand'], [
        ('Naht schließt nicht', 'Grat, Druckverzug, falsche Winkelstellung', 'Lösen; -18° und Eingriff prüfen; Coupon vergleichen.'),
        ('Rotor schleift', 'Magnetüberstand, Spulenhöhe, Axialspiel, verzogene Scheibe', 'Kleinsten Spalt rundum messen; Kontaktursache beheben.'),
        ('Starke Schwingung', 'Unwucht, verbogene Welle, lose Klemmung', 'Nicht weiterlaufen lassen; Welle und Sitz kontrollieren.'),
        ('Kaum AC Spannung', 'Unterbrechung, falsche Pole oder Messbereich', 'Durchgang, Polpaare, Drehzahl und Messgerät prüfen.'),
        ('Spannung bricht ein', 'Last zu klein, hoher Spulenwiderstand, Drehzahl sinkt', 'Lastwert, Strom, Draht und tatsächliche Drehzahl erfassen.'),
        ('Spule wird heiß', 'Zu hoher Strom, Isolationsschaden, schlechte Wärmeabfuhr', 'Abkühlen; Widerstand und Emaille prüfen; Versuch neu bemessen.'),
        ('Akku lädt nicht', 'Ladeziel, Eingangsspannung oder Reglerkonfiguration unpassend', 'Keine Überbrückung; Messwerte und Herstellerplan prüfen.'),
    ], [40, 58, 76])
    _paragraph(doc, 'Aus wiederkehrenden Fehlern keine höheren Drehzahl- oder Temperaturgrenzen ableiten. Bei fortschreitendem Schaden das betroffene Teil ersetzen und die Ursache klären. Ein erfolgreich verlaufener kurzer Versuch ist kein Dauerfestigkeitsnachweis.')


def _records_and_sources(doc, data):
    _page(doc, '14 Formeln und Messblätter')
    _table(doc, ['Größe', 'Beziehung', 'Gültigkeit'], [
        ('Spannung pro Windung', 'u = V_ac_test / N_test', 'Gleiche Drehzahl und Geometrie; gleiche Messart.'),
        ('Lastleistung DC', 'P = V_dc × I_dc', 'Stationäre DC-Werte an derselben Last.'),
        ('Ohmsche Last AC', 'P = V_rms² / R_last', 'Rein ohmsche, bekannte Last; tatsächlicher RMS-Wert.'),
        ('Kupferverlust', 'P_cu = I_rms² × R_spule', 'Widerstand bei erfasster Temperatur; Näherung.'),
        ('Erwärmung', 'ΔT = T_ende − T_start', 'Gleiche Laufzeit und Umgebung vergleichen.'),
    ], [39, 61, 74])
    doc.add_heading('Messblatt für Draht und Passung', 2)
    _paragraph(doc, 'Datum __________________  Prüfer __________________\nDrahtcharge __________________  Messgerät __________________\nSchablone und Material __________________  Umgebung ______ °C')
    _table(doc, ['Spule', 'Windungen', 'd über Emaille mm', 'Außen mm', 'Innen mm', 'Höhe mm', 'R kalt Ω'], [
        ('____', '20', '____', '____', '____', '____', '____'),
        ('____', '40', '____', '____', '____', '____', '____'),
        ('____', '80', '____', '____', '____', '____', '____'),
        ('____', '____', '____', '____', '____', '____', '____'),
    ], [20, 24, 32, 24, 24, 24, 26])
    _paragraph(doc, 'Prüfung der Emaille ______________________________________________\nDurchgang und Messleitungskorrektur ______________________________\nBindung und Anschlussreserve ____________________________________\nPasst ohne Druck in den realen Wickelraum __________________________')
    doc.add_heading('Messblatt für Leerlauf und Last', 2)
    _paragraph(doc, 'Spule ______  Windungen ______  Luftspalt oben/unten ______ / ______ mm\nMessart AC RMS oder DC ______  Gerät / Bereich _____________________')
    _table(doc, ['n min⁻¹', 'V leer', 'R Last Ω', 'V Last', 'I Last A', 'Zeit s', 'T₀ / T₁ °C'], [
        ('____', '____', '____', '____', '____', '____', '____ / ____'),
        ('____', '____', '____', '____', '____', '____', '____ / ____'),
        ('____', '____', '____', '____', '____', '____', '____ / ____'),
    ], [25, 22, 25, 22, 25, 20, 35])

    _page(doc, 'Mechanische Messung und Entscheidung')
    _paragraph(doc, 'Aufbauversion __________________  Material __________________\nDatum __________________  Prüfer __________________')
    _table(doc, ['Prüfpunkt', 'Istwert oder Befund', 'Bestanden / offen'], [
        ('Coupon und Magnetabmessungen', '________________________', '________________'),
        ('Polpaare 1 bis 18', '________________________', '________________'),
        ('Rückhaltung beider Magnetringe', '________________________', '________________'),
        ('Lager und Stator axial gehalten', '________________________', '________________'),
        ('Kleinster Spalt oben / unten', '________ / ________ mm', '________________'),
        ('Axiales Spiel und Rundlauf', '________ / ________ mm', '________________'),
        ('Sechs Nähte und zwölf H04', '________________________', '________________'),
        ('M8 Stack und zwei H05', '________________________', '________________'),
        ('Reale Stangenlänge', '___________________ mm', '________________'),
        ('Schutzhaube und Stillsetzen', '________________________', '________________'),
    ], [70, 63, 41])
    doc.add_heading('Ergebnis der Wicklungsversuche', 2)
    _paragraph(doc, 'Vergleichsdrehzahl __________ min⁻¹   Ausgewählte Testspule __________\nN_test ______  V_ac_test ______ V  V_ac_target ______ V\nBegründung des Spannungsziels ___________________________________\nBerechnete Windungszahl __________  Aufgerundet __________\nErneute Passungs- und Lastprüfung ________________________________')
    _paragraph(doc, 'Offene Punkte vor Elektronikauswahl ______________________________\n______________________________________________________________\nOffene Punkte vor einem weiteren Drehversuch ______________________\n______________________________________________________________')
    _paragraph(doc, 'Eintrag und Unterschrift dokumentieren einen Versuch. Sie ersetzen keine technische Freigabe für Außen-, Sturm- oder unbeaufsichtigten Betrieb.')

    _page(doc, '15 Zeichnungsindex und Quellen')
    _table(doc, ['ID', 'Zeichnung', 'Teilebezug'], [
        (key, item['title'], ', '.join(item['items'])) for key, item in data['drawings'].items()
    ], [15, 86, 73])
    doc.add_heading('Projektquellen und Aussagegrenzen', 2)
    _paragraph(doc, '[P1] build/manifest.json, assembly_audit und production_parts. Quelle der Stückzahlen, STL-Pfade, belasteten Maße und noch nicht validierten Prüfzustände.')
    _paragraph(doc, '[P2] src/windwall/parameters.py und die CAD-Module rotor_modules.py, generator.py, top_closure.py sowie assembly.py. Parametrische Geometrie und Baugruppenbeziehungen.')
    _paragraph(doc, '[P3] docs/generator-reference-measurements.md. Messung externer Referenz-STLs und dokumentierte Rekonstruktionsentscheidungen. Mesh-Messwerte sind keine realen Magnet- oder Lagermaße.')
    _paragraph(doc, 'Festgelegte Projektvorgaben sind sieben Stufen, CCW-Verriegelung, nominal 36 Magnete und die Testreihe 20/40/80. Die 11-mm-Taschen und provisorischen stehenden Hüllen sind Rekonstruktionsentscheidungen. Druckparameter und Werkstattablauf sind Empfehlungen. Leistung, Endwicklung, Kaufprodukte und Betriebsgrenzen bleiben unbekannt, bis Versuche sie belegen.')

    _page(doc, 'Herstellerhinweise für die Ladetechnik')
    _paragraph(doc, 'Die folgenden externen Quellen geben allgemeine Sicherheits- und Auslegungsregeln. Sie bestätigen keine Leistung dieses Rotors und sind keine Produktempfehlung. Bei der Auswahl gelten die aktuellen Handbücher der tatsächlich eingesetzten Geräte. Quellen geprüft am 9. September 2026.')
    doc.add_heading('S1 Trojan Battery', 2)
    _paragraph(doc, 'Battery Maintenance. Herstellerhinweise zu Belüftung, Vermeidung von Funken, korrekten Ladeeinstellungen und Gefahren der Überladung. Die im Herstellertext genannten Spannungen gehören zu seinen jeweiligen Batterietypen und werden hier nicht als 48-V-Sollwerte übernommen.')
    _paragraph(doc, 'https://www.trojanbattery.com/resources/battery-maintenance')
    _paragraph(doc, 'AES AGM and Standard AGM Battery Maintenance. Hinweise zur AGM-Behandlung, Belüftung und zum Verbot des Nachfüllens bei geschlossenen AGM-Batterien.')
    _paragraph(doc, 'https://www.trojanbattery.com/trojan-aes-batteries/aes-agm-standard-agm-battery-maintenance')
    doc.add_heading('S2 Morningstar Corporation', 2)
    _paragraph(doc, 'Diversion Charge Control Manual, besonders Abschnitte 6.4.4 und 6.4.5. Die Last muss Quellenenergie aufnehmen können und gleichzeitig innerhalb der Reglergrenzen bleiben. Die dortigen TriStar-Beispiele sind gerätespezifisch und dürfen nicht ungeprüft auf dieses System übertragen werden.')
    _paragraph(doc, 'https://www.morningstarcorp.com/wp-content/uploads/technical-doc-diversion-manual-en.pdf')
    doc.add_heading('Vor der ersten Batterieverbindung ergänzen', 2)
    _paragraph(doc, 'Batteriehersteller und Typ ________________________________________\nBatteriehandbuch und Revision ___________________________________\nReglermodell und Handbuch ______________________________________\nGleichrichter und Kühlkonzept ____________________________________\nSchutzorgane und Leitungsbemessung _____________________________\nDump Load und sichere Wärmeabfuhr ______________________________\nGeprüfter Anschlussplan ________________________________________')
    _paragraph(doc, 'Solange diese Auswahl und die mechanischen Prüfungen offen sind, bleibt die Entwicklung beim geschützten Messaufbau mit definierter Last. Generator nicht direkt mit dem Akku verbinden.')


def build_manual(project_root: Path, output_path: Path) -> Path:
    """Create the complete German DOCX and return the requested output path."""
    project_root = Path(project_root).resolve()
    output_path = Path(output_path)
    data = load_manual_data(project_root)
    manifest = json.loads((project_root / 'build/manifest.json').read_text(encoding='utf-8'))
    paths = _figure_paths(project_root, data)
    doc = _setup_document()
    _scope(doc, data)
    _boms(doc, data, manifest)
    _printing(doc)
    _generator(doc, data, paths)
    _winding(doc, data, paths)
    _measurements(doc, data, paths)
    _rotor(doc, data, paths)
    _safety(doc, data, paths)
    _records_and_sources(doc, data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)
    return output_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or args.project_root / 'output/Ugrinsky-Wind-Wall-Bauanleitung.docx'
    print(build_manual(args.project_root, output))


if __name__ == '__main__':
    main()
