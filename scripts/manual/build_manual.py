"""Build the German V5 assembly and experiment manual from release JSON and PNGs.

Paragraph, table and inline-figure helpers are ported from feature/assembly-manual.
Content is specific to the approved V5 design; no CAD module or older asset
snapshot is imported. Fixed metadata and ZIP member times make rebuilds stable.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.manual.manual_data import PART_LABELS, dimensions, load_manual_data, mm


TITLE = "Ugrinsky Wind Wall V5 Bauanleitung"


def _paragraph(doc, text, *, lead=None):
    paragraph = doc.add_paragraph()
    if lead:
        paragraph.add_run(lead + " ").bold = True
    paragraph.add_run(text)
    return paragraph


def _page(doc, title, *, level=2):
    heading = doc.add_heading(title, level)
    heading.paragraph_format.page_break_before = True


def _steps(doc, steps):
    for number, (lead, text) in enumerate(steps, 1):
        _paragraph(doc, text, lead=f"{number}. {lead}.")


def _table(doc, headers, rows, widths, *, centered=()):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for column, width in zip(table.columns, widths):
        column.width = Mm(width)
    properties = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        item = OxmlElement("w:" + edge)
        for key, value in (("val", "single"), ("sz", "4"), ("color", "D9D9D9")):
            item.set(qn("w:" + key), value)
        borders.append(item)
    properties.append(borders)
    margins = OxmlElement("w:tblCellMar")
    for edge, size in (("top", 90), ("bottom", 90), ("left", 100), ("right", 100)):
        item = OxmlElement("w:" + edge)
        item.set(qn("w:w"), str(size))
        item.set(qn("w:type"), "dxa")
        margins.append(item)
    properties.append(margins)
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    for row_index, values in enumerate([headers, *rows]):
        row = table.rows[0] if row_index == 0 else table.add_row()
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for column_index, (cell, text, width) in enumerate(zip(row.cells, values, widths)):
            cell.width = Mm(width)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            shading = OxmlElement("w:shd")
            shading.set(qn("w:fill"), "3F3F3F" if row_index == 0 else ("F4F4F4" if row_index % 2 else "FFFFFF"))
            cell._tc.get_or_add_tcPr().append(shading)
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(0)
            paragraph.paragraph_format.line_spacing = 1.05
            if column_index in centered:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = paragraph.add_run(str(text))
            run.font.size = Pt(10)
            if row_index == 0:
                run.bold = True
                run.font.color.rgb = RGBColor.from_string("FFFFFF")
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def _figure(doc, drawing_id, data):
    drawing = data["drawings"][drawing_id]
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.keep_with_next = True
    paragraph.paragraph_format.space_after = Pt(3)
    image = paragraph.add_run().add_picture(str(drawing["path"]), width=Mm(174))
    image._inline.docPr.set("descr", drawing["alt_text"])
    image._inline.docPr.set("title", drawing_id)
    caption = doc.add_paragraph(f"{drawing_id}  {drawing['caption']}", style="Caption")
    caption.paragraph_format.keep_together = True


def _setup_document():
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.left_margin = section.right_margin = Mm(18)
    section.top_margin = section.bottom_margin = Mm(18)
    section.footer_distance = Mm(8)
    for name, size in (("Normal", 11), ("Title", 26), ("Subtitle", 12),
                       ("Heading 1", 18), ("Heading 2", 13), ("Heading 3", 11), ("Caption", 10)):
        style = doc.styles[name]
        style.font.name = "Arial"
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string("000000")
        style.font.underline = False
        for color in style.element.xpath(".//w:color"):
            for attribute in ("themeColor", "themeTint", "themeShade"):
                color.attrib.pop(qn("w:" + attribute), None)
        for border in style.element.xpath(".//w:pBdr"):
            border.getparent().remove(border)
        style.paragraph_format.space_after = Pt(7)
        style.paragraph_format.line_spacing = 1.08
        style.paragraph_format.widow_control = True
        if name in ("Title", "Subtitle", "Heading 1", "Heading 2", "Heading 3"):
            style.paragraph_format.keep_with_next = True
            style.paragraph_format.space_before = Pt(8 if name == "Heading 2" else 0)
        if name == "Caption":
            style.font.italic = False
    lang = OxmlElement("w:lang")
    lang.set(qn("w:val"), "de-DE")
    doc.styles["Normal"].element.get_or_add_rPr().append(lang)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer.add_run("Ugrinsky V5  |  ").font.size = Pt(9)
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    footer._p.append(field)
    properties = doc.core_properties
    properties.title = TITLE
    properties.subject = "V5 Montage und Spulenversuche für einen unvalidierten PLA Prototyp"
    properties.author = "Windwall Projekt"
    properties.last_modified_by = "Windwall Projekt"
    properties.language = "de-DE"
    properties.created = properties.modified = datetime(2026, 9, 9, tzinfo=timezone.utc)
    properties.revision = 1
    return doc


def _scope(doc, data):
    manifest = data["manifest"]
    parameters = manifest["parameters"]
    shaft_bounds = manifest["fence_assembly_audit"]["shaft_bounds_z_mm"]
    doc.add_paragraph(TITLE, style="Title")
    doc.add_paragraph("Montage und Spulenversuche für den PLA Prototyp", style="Subtitle")
    doc.add_heading("1 Zweck und Grenzen", 1)
    _paragraph(doc, "Diese Anleitung führt durch Passproben, Druck, Montage des siebenstufigen Rotors und vergleichbare Spulenversuche. Baue zuerst einen geschützten Werkstattaufbau. Erst reale Messungen erlauben die Auswahl der Wicklung, der Magnetbefestigung und der Ladeelektronik.")
    _paragraph(doc, "V5 ist physisch nicht validiert. CAD-Prüfungen bestätigen geometrische Eigenschaften, aber keine sichere Drehzahl, Dauerfestigkeit, Leistung oder Eignung für unbeaufsichtigten Außenbetrieb. Die Passungen sind keine freigegebene Presspassung. Der seitliche Kabelausgang und das Gehäuse sind nicht wasserdicht.", lead="Prototypstatus.")
    _paragraph(doc, "Den Generator nicht direkt an einen 48-V-Bleiakku anschließen. Für die ersten Versuche ausschließlich einen geschützten Messaufbau mit definierter, passend bemessener Last verwenden.", lead="Elektrische Grenze.")
    _table(doc, ["Merkmal", "V5 Nennwert"], [
        ("Rotorstufen", f"{parameters['rotor']['stage_count']}: 1 Base, {parameters['rotor']['standard_stage_count']} Standard, 1 Top"),
        ("Rotordurchmesser", mm(parameters["rotor"]["rotor_diameter_mm"]) + " mm"),
        ("Stufenteilung und Rotorhöhe", dimensions((manifest["assembly_audit"]["nominal_stage_pitch_mm"], manifest["assembly_audit"]["aerodynamic_height_mm"]))),
        ("Verlängerte Wellenhülle", mm(shaft_bounds[1] - shaft_bounds[0]) + " mm; kein verbindliches Zuschnittmaß"),
        ("Druckkörper", f"{manifest['production_quantity']} aus {len(data['parts'])} unterschiedlichen STL-Dateien"),
    ], [67, 107])
    _page(doc, "Gesamtaufbau verstehen")
    _figure(doc, "E15", data)
    _paragraph(doc, "Ocker bezeichnet den rotierenden Strang. Türkis bezeichnet stationäre Druckteile. Violett kennzeichnet Lagerbereiche; deren Wälzkörper und Laufringe haben unterschiedliche Bewegungen. Graue Holz-, Schrauben- und Freiraumreferenzen sind keine Druckteile.")
    _paragraph(doc, "Die beiden Magnetträger drehen gemeinsam mit Welle, M8-Klemmung und Rotorstapel. Spule, Kassette, Gehäuse, Deckel und oberer Halter bleiben stationär. Der untere Magnetrotor läuft innerhalb des Gehäuses unterhalb der stationären Spule.")
    _paragraph(doc, "Zum Nachschlagen: Kapitel 2 und 3 enthalten Teile und Kaufhardware; 4 und 5 Druck und Passproben; 6 bis 9 Wicklung und Montage; 10 und 11 Messung und Inbetriebnahme; 12 und 13 Wartung, Fehlersuche und Versuchsprotokoll.")


def _inventory(doc, data):
    _page(doc, "2 Druckteile und Dateien", level=1)
    _paragraph(doc, "Die Mengen gelten für einen vollständigen Rotor einschließlich Generatorgehäuse und oberem Halter. Der obere Magnetträger ist in der Base integriert. STL-Dateien liegen unter release/v5/stl/, die zugehörigen STEP-Dateien unter release/v5/step/.")
    _table(doc, ["Stück", "Druckteil", "STL Datei", "STEP Datei"], [
        (part["quantity"], PART_LABELS[part["name"]], Path(part["stl_path"]).name, Path(part["step_path"]).name)
        for part in data["parts"]
    ], [11, 43, 60, 60], centered=(0,))
    _paragraph(doc, "Base, Standard, Top und unterer Magnetrotor sind rotierend. Gehäuse, Spulenkassette, Generator-Deckel und oberer Lagerhalter sind stationär. Die Release-STLs stehen am Druckbett auf Z = 0; dies ist keine automatisch optimierte Druckorientierung.")
    _page(doc, "Passproben und Baugruppen")
    _paragraph(doc, "Alle folgenden Coupons einmal für die erste Passprüfung drucken. Wiederhole sie bei verändertem Material, Profil oder Passmaß. Die Coupon-STLs liegen unter release/v5/coupons/, ihre STEP-Dateien unter release/v5/step/.")
    _table(doc, ["Stück", "Coupon STL", "Coupon STEP"], [
        (1, Path(part["stl_path"]).name, Path(part["step_path"]).name)
        for part in data["coupons"].values()
    ], [12, 81, 81], centered=(0,))
    doc.add_heading("Baugruppen zur Kontrolle", 2)
    for assembly in data["manifest"]["assemblies"]:
        _paragraph(doc, assembly["step_path"])
    _paragraph(doc, "Diese STEP-Baugruppen dienen zur Montagekontrolle. Die Datei fence_assembly.step enthält die verlängerte Welle für den oberen Halter. Holz und Kaufteile werden nicht aus Baugruppen heraus als Druckteile exportiert.")


def _hardware(doc, data):
    _page(doc, "3 Kaufteile und Werkzeug", level=1)
    _paragraph(doc, "Die Tabelle beschreibt den geplanten Prototyp. Kaufe erst nach Abgleich mit den realen Teilen. Nennhüllen beweisen weder Gewindeeingriff noch Schraubenkopfsitz oder Tragfähigkeit.")
    _table(doc, ["Stück", "Bauteil", "Maß und Auswahl"], data["hardware"], [12, 49, 113], centered=(0,))
    _paragraph(doc, "Das 51105 wird als vollständiges Lager gekauft, einschließlich beider Scheiben und Wälzkörper. Diese werden in der CAD-Baugruppe getrennt dargestellt. Für die M4-Schrauben reale Durchstecklänge, Mutternhöhe, Kopf und Bodenabstand messen; die Hülle ist keine Kaufempfehlung für eine bestimmte Schraubenlänge.")
    doc.add_heading("Material für Wicklung und Messung", 2)
    _paragraph(doc, "Kupferlackdraht mit 0,18 mm Ausgangsdurchmesser, isolierte Anschlusslitzen, geeignete Löt- und Isoliermittel sowie eine erprobte Zugentlastung bereitlegen. Weitere Drahtdurchmesser erst vermessen. Befestigungs- und Vergussstoffe benötigen einen Verträglichkeitstest mit Drahtlack, Magnetbeschichtung und Druckmaterial.")
    _paragraph(doc, "Erforderliche Messmittel sind Messschieber, Mikrometer, Tiefenmaß, Fühlerlehren, Drehzahlmesser, geeignetes True-RMS-Multimeter, Temperaturfühler und definierte Leistungswiderstände. Für kleine Widerstände Messleitungswiderstand berücksichtigen oder Vierleitermessung nutzen. Passende M4- und M8-Werkzeuge, Schutzbrille und eine nichtmagnetische Montagehilfe ergänzen den Arbeitsplatz.")


def _printing(doc, data):
    _page(doc, "4 Druck vorbereiten", level=1)
    _paragraph(doc, "Beginne mit PLA und den Coupons auf dem Bambu P2S mit 0,4 mm Düse. Nutze das zum tatsächlich geladenen PLA passende Materialprofil. Als noch zu prüfenden Ausgangspunkt 0,20 mm Schichthöhe im Slicer betrachten. Temperatur, Kühlung, Wandlinien, Infill und Stützen erst anhand der Passproben und der vollständigen Schichtvorschau festlegen.")
    _paragraph(doc, "Die Rotorwand beträgt im CAD " + mm(data["manifest"]["parameters"]["blade"]["wall_thickness_mm"]) + " mm. Stelle sicher, dass der Slicer dünne Wandbereiche lückenlos erzeugt. Materialstärke allein bestätigt keine Festigkeit; Orientierung und Layerhaftung bestimmen die tatsächliche Belastbarkeit mit.")
    _table(doc, ["Teilgruppe", "Orientierung und Prüfung"], [
        ("Magnet und Lagercoupons", "Taschen nach oben; Elephant Foot und Stützreste von Passflächen fernhalten."),
        ("Base", "Magnettaschen öffnen in Einbaulage nach unten. Z-up und gewendete Lage im Slicer vergleichen; Taschen, Muttertasche und Blattübergänge prüfen."),
        ("Standard und Top", "Exportierte Z-up-Lage prüfen; untere Klauen und obere Rastbahnen müssen frei und nach dem Druck zugänglich sein."),
        ("Unterer Magnetrotor", "Magnettaschen nach oben; Rückentasche und Auflage auf dem Bett kontrollieren."),
        ("Gehäuse", "Geschlossener Boden auf dem Bett, Öffnung nach oben; Laschen und Schraubkanäle vollständig prüfen."),
        ("Kassette", "Auflage unten, Wicklungsraum nach oben; Schlüssel und Kabelöffnung ohne Grat."),
        ("Deckel und oberer Halter", "Lagersitze nach oben bevorzugen, sofern Unterseite sauber abgestützt werden kann; keine Stützreste im Lagersitz."),
    ], [46, 128])
    _paragraph(doc, "Bajonettdächer und Hinterschneidungen benötigen eine überprüfte Brücke oder zugängliche Stützen. Lasse keine unentfernbaren Stützen in geschlossenen Rastbahnen. Prüfe jede Schicht der Vorschau vor dem Start; zuerst Coupons, anschließend eine reale Verbindung aus zwei Stufen, erst danach den ganzen Satz drucken.")
    _paragraph(doc, "ASA ist eine spätere Materialstufe. Nach dem Wechsel Passmaße, Verzug, Verbindungskräfte, Magnetbefestigung und Belastung erneut prüfen. Ein Materialwechsel allein gibt den Rotor nicht für Wetter, Wärme oder Dauerbetrieb frei. Für Verarbeitung und Belüftung die Hinweise des tatsächlich verwendeten Filaments und Druckers beachten.")


def _fits(doc, data):
    _page(doc, "5 Passproben und Lager prüfen", level=1)
    _paragraph(doc, "Miss die realen Lager, Magnete und Muttern vor dem Druck. Markiere Material, Profil und Orientierung auf jeder Probe. Ein maßhaltiger Coupon muss sich ohne Risse, Verkanten oder unkontrollierte Gewalt fügen lassen; die passende Auswahl dokumentieren und vor dem Druck großer Teile in die Konstruktion übernehmen.")
    rows = []
    for name, label, key in (("51105_outer_seat_coupon", "51105 Außensitz", "seat_diameters"),
                             ("25mm_pilot_coupon", "51105 Zentrierbund", "pilot_diameters"),
                             ("608_seat_coupon", "608 Außensitz", "seat_diameters"),
                             ("magnet_pocket_coupon", "Magnettaschen", "pocket_diameters"),
                             ("coil_cassette_segment_coupon", "Kassette Radialspiel", "radial_clearances")):
        rows.append((label, " / ".join(mm(value) for value in data["coupons"][name]["fit_dimensions_mm"][key]) + " mm"))
    _table(doc, ["Probe", "Varianten im Release"], rows, [76, 98])
    _paragraph(doc, "Beim Kassettensegment zuerst den männlichen Bogen bündig von der Platte freischneiden und die Schnittkante entgraten. Dann mit den Sitzsegmenten vergleichen. Der Coupon prüft radiales Spiel, nicht die fertige axiale Klemmung durch den Deckel.")
    _paragraph(doc, "Bajonettpaar und vollständiges Verbindungspaar getrennt testen. Einführen, gegen den Uhrzeigersinn verriegeln und Rastung kontrollieren. Die dauerhafte Rastung kann beim Rückdrehen oder Zerlegen beschädigt werden. Kraft, sichtbare Risse, axiales Spiel und Blattnaht protokollieren; die Rastung nicht durch gewaltsames Rückdrehen freimachen.")
    _page(doc, "51105 Passung und Orientierung")
    _figure(doc, "E11", data)
    _paragraph(doc, "51105: " + dimensions((data["manifest"]["parameters"]["bearings"][key] for key in ("thrust_bore_diameter_mm", "thrust_outer_diameter_mm", "thrust_height_mm"))) + ". Die Gehäusescheibe bleibt stationär im zentralen Deckelsitz. Die Wellenscheibe dreht mit der Base und wird durch deren Zentrierbund ausgerichtet. Die Laufbahnen weisen zu den Wälzkörpern. Scheiben und Käfig nach ihrer tatsächlichen Geometrie und Herstellerkennzeichnung zuordnen; nicht allein nach ähnlichem Aussehen vertauschen.")
    _paragraph(doc, "Das 51105 trägt die axiale Rotorlast. Beim Fügen ausschließlich auf die einzusetzende Scheibe drücken und keine Kraft durch Wälzkörper leiten. Das Lager nicht durch Verspannen der Druckteile als Passungswerkzeug missbrauchen.")
    _page(doc, "608 Passung und Orientierung")
    _figure(doc, "E12", data)
    _paragraph(doc, "608: " + dimensions((data["manifest"]["parameters"]["bearings"][key] for key in ("radial_bore_diameter_mm", "radial_outer_diameter_mm", "radial_height_mm"))) + ". Der Außenring sitzt im stationären oberen Halter, der Innenring führt die rotierende M8-Welle. Wälzkörper bewegen sich zwischen den Ringen. Die violette CAD-Hülle löst diese innere Kinematik nicht auf.")
    _paragraph(doc, "Eine M8-Gewindestange ist kein geschliffener Lagerzapfen. Passe eine lokale Lauffläche nur nach Messung und kontrollierter Bearbeitung an; Durchmesser, Rundlauf, Restquerschnitt und sicheren Innenringsitz erneut prüfen. Eine gedruckte Führungshülse ist nicht vorgesehen. Der 608-Punkt führt hauptsächlich radial; vermeide eine ungewollte zweite axiale Verspannung.")


def _winding(doc, data):
    _page(doc, "6 Magnete und Testspule vorbereiten", level=1)
    _paragraph(doc, "Miss Magnetdurchmesser und Dicke einschließlich Beschichtung. Die Taschen sind " + dimensions((data["manifest"]["parameters"]["generator"]["magnet_pocket_diameter_mm"], data["manifest"]["parameters"]["generator"]["magnet_pocket_depth_mm"])) + " als Durchmesser und Tiefe; sie sind keine bestätigte Klemmung für einen Magneten mit 10 × 2 mm Projektmaß. Teste Klebstoff, Beschichtung und Rückhaltung am Coupon. Klebstoffhöhe darf den Luftspalt nicht unbemerkt verringern.")
    _steps(doc, [
        ("Polflächen markieren", "Einen Referenzmagneten benutzen und dieselbe Polfläche aller Magnete markieren. Pole vor dem Einsetzen erneut prüfen. Schutzbrille tragen und Magnete mit nichtmagnetischen Abstandshaltern getrennt halten."),
        ("Oberen Ring bestücken", "Zur Spule zeigen die Pole abwechselnd N S N S rund um den Ring. Eine feste Taschenposition als Start markieren und die gesamte Polfolge protokollieren."),
        ("Unteren Ring zuordnen", "An gleicher Winkelposition steht dem oberen N-Pol unten ein S-Pol gegenüber; beim nächsten Paar entsprechend umgekehrt. Die zur Spule gerichteten Flächen sind entscheidend. Auf der Werkbank gleich orientierte Scheiben können nach dem Umdrehen eine andere Zuordnung zeigen."),
        ("Rückhaltung prüfen", "Magnete vollständig setzen und Befestigung nach dem konkreten Produkt aushärten lassen. Beide Ringe zuerst einzeln prüfen. Die Magnetrückhaltung ist vor jeder Drehprobe ein eigenständiges offenes Prüfkriterium."),
    ])
    doc.add_heading("Serpentinenwicklung als Versuch", 2)
    _paragraph(doc, "Lege den isolierten Draht in wiederholten, zusammenhängenden Serpentinen durch die aktiven Polbereiche der stationären Kassette. Markiere Anfang A, Ende B und den Weg einer vollständigen Wiederholung. Für diese Versuchsreihe zählt eine vollständige Wiederholung derselben Serpentine als eine Windung. Alle drei Testspulen müssen denselben Verlauf und dieselbe Wickelrichtung verwenden.")
    _paragraph(doc, "Prüfe den Verlauf zuerst mit wenigen Wiederholungen bei Handdrehung: Die Beiträge aufeinanderfolgender aktiver Abschnitte sollen sich addieren. Veränderte Polfolge, umgekehrte Teilstücke oder andere Drahtwege können Spannung aufheben. Dokumentiere den realen Verlauf mit Foto oder Skizze; die Kassette legt keine abschließend geprüfte elektrische Wicklung fest.")
    _table(doc, ["Draht", "Windungen", "Vergleich und Messung"], [
        ("0,18 mm, real messen", "20", "Widerstand, Bauhöhe, Leerlaufspannung und Lastmessung bei gleicher Drehzahl"),
        ("0,18 mm, real messen", "40", "Gleicher Verlauf und gleiche Wickelrichtung wie bei 20"),
        ("0,18 mm, real messen", "80", "Nur einsetzen, wenn die reale Wicklung in den geprüften Raum passt"),
    ], [46, 26, 102], centered=(1,))
    _paragraph(doc, "Für jeden später gemessenen Drahtdurchmesser die vollständige Matrix 20, 40 und 80 wiederholen. Leiterdurchmesser und Außendurchmesser mit Lack unterscheiden. Es gibt keine endgültige Windungszahl und keine zugesicherte Leistung. Den verfügbaren Wickelraum nicht mit maximal zulässiger Wärmeentwicklung verwechseln.")
    _paragraph(doc, "Anschlussenden außerhalb aktiver Laufspalte halten. Lötstellen isolieren, die Litzen mechanisch entlasten und Durchgang sowie Isolation zum übrigen Aufbau prüfen. Vor dauerhaftem Verguss zuerst eine entnehmbare Testspule messen; Verguss kann Wärmeabfuhr, Reparatur, Höhe und Passung verändern.")


def _generator(doc, data):
    _page(doc, "7 Generator montieren", level=1)
    _paragraph(doc, "Arbeite bei gesichertem Stillstand mit einer Montagehilfe, die die Anziehung der Magnetringe kontrolliert. Der Gehäusetopf öffnet nach oben. Prüfe vorab Muttertaschen, Schulter, Schlüssel und Kabelweg. Setze die sechs gefangenen M4-Muttern vor dem Verschließen vollständig ein.")
    _steps(doc, [
        ("Unteren Magnetrotor einsetzen", "M8-Drehmomentmutter in die Rückentasche setzen. Unteren Rotor mit Welle und Distanzhülse in den Topf einsetzen, Magnetflächen nach oben. Der komplette Rotor bleibt innerhalb des Gehäuses; Mutter und Wellenende dürfen den geschlossenen Boden nicht berühren."),
        ("Spulenkassette einsetzen", "Die Wicklung zuvor auf Passung und Isolation prüfen. Kassette über die Welle absenken, auf der Gehäuseschulter absetzen und den einzelnen Schlüssel in die Verdrehsicherung führen. Die seitlichen Kabelöffnungen müssen fluchten."),
        ("Stationären Deckel montieren", "Kabel aus dem seitlichen Ausgang führen und entlasten. Deckel plan aufsetzen und die sechs M4-Schrauben in gefangene Muttern einschrauben. Gleichmäßig und schrittweise über Kreuz anziehen; bei Spalt oder Verformung stoppen. Für PLA liegt kein geprüftes Anziehdrehmoment vor."),
        ("51105 einsetzen", "Stationäre Gehäusescheibe auf den Deckelbund setzen, dann Wälzkörper und rotierende Wellenscheibe mit einander zugewandten Laufbahnen einsetzen. Lager sauber halten; den Zentrierbund der Base mit der realen Wellenscheibe abgleichen."),
        ("Base aufsetzen", "Obere Drehmomentmutter einsetzen, Base auf Welle und Lager absenken. Ihre Magnetflächen zeigen zur Spule nach unten. Die Base-Schulter trägt auf der rotierenden Wellenscheibe. Magnetanziehung durch die Montagehilfe begrenzen und Finger aus dem Spalt halten."),
        ("Laufspalte messen", "Welle von Hand vollständig drehen. Jeden Winkel auf Kontakt, Kabelzug und sichtbaren Schlag prüfen. Tatsächliche Magnetflächen, Wicklung und Klebstoff bestimmen die Freigänge. Erst nach erfolgreicher Prüfung mit dem Rotorstapel fortfahren."),
    ])
    _page(doc, "Unterer Rotor im Gehäuse")
    _figure(doc, "E05", data)
    _paragraph(doc, "Die Rückentasche überträgt Drehmoment über die M8-Mutter. Die Distanzhülse dreht mit der Welle; die Spule darf sie nicht berühren. Die im CAD reservierte Hülse misst " + dimensions(data["components"]["spacer"]["dimensions_mm"]["size_xyz"][::2]) + " als Außendurchmesser und Länge. Reale Klemmung und Bodenabstand vor einem Zuschnitt trocken prüfen.")
    _page(doc, "Generator in Einbaureihenfolge")
    _figure(doc, "E06", data)
    _paragraph(doc, "Die angehobenen Teile zeigen den Zugang von oben. Die Wicklung bleibt zwischen den beiden rotierenden Magnetträgern stationär. Den unteren Magnetrotor vor Kassette und Deckel einsetzen; nach dem Verschließen ist der Topfboden kein Montagezugang.")
    _page(doc, "Axiallager und Lastpfad")
    _figure(doc, "E04", data)
    _paragraph(doc, "Die Rotorlast läuft von der Base-Schulter über die Wellenscheibe, Wälzkörper und Gehäusescheibe in den stationären Deckel und weiter über das Gehäuse zum unteren Rahmen. Die M8-Klemmung verbindet rotierende Teile; sie darf den stationären Deckel oder die Wicklung nicht einklemmen.")
    _page(doc, "Beide Luftspalte kontrollieren")
    _figure(doc, "E07", data)
    gaps = data["manifest"]["assembly_audit"]["generator_air_gap_report"]
    _paragraph(doc, f"Oben sind {mm(gaps['upper_air_gap_mm'])} mm und unten {mm(gaps['lower_air_gap_mm'])} mm nominal vorgesehen. Diese Luftspalte gelten nur, wenn Magnete bündig oder tiefer in ihren Taschen sitzen. Überstand, Klebstoff, Wicklungshöhe, axialer Versatz und Rundlauf können den tatsächlichen kleinsten Spalt verringern.")
    _paragraph(doc, "Miss über eine vollständige Handumdrehung und prüfe auch vorhandenes axiales Spiel. Ein berührungsfreier CAD-Zustand bestätigt keine Reserve unter Last. Bei Schleifen weder einschleifen noch mit höherer Drehzahl freifahren; Ursache lokalisieren und den Aufbau korrigieren.")
    _page(doc, "Kassette und Deckel sichern")
    _figure(doc, "E08", data)
    _paragraph(doc, "Die Gehäuseschulter hält die Kassette nach unten, der Passring zentriert radial und der Schlüssel verhindert Verdrehung. Der verschraubte Deckel begrenzt den Weg nach oben. Alle vier Funktionen müssen bei der Trockenmontage vorhanden sein; ein nur lose eingelegter Wicklungsträger ist nicht betriebsbereit.")
    _page(doc, "Deckelschrauben kontrollieren")
    _figure(doc, "E09", data)
    _paragraph(doc, "Sechs M4-Schrauben und sechs gefangene Sechskantmuttern verbinden Deckel und Gehäuse. Der Schraubenzugang erfolgt von oben. Nach dem Anziehen muss der Deckel plan sitzen und die Welle weiterhin frei laufen. Markiere die Schraubenstellung für spätere Sichtkontrollen.")
    _page(doc, "Seitliches Kabel herausführen")
    _figure(doc, "E10", data)
    _paragraph(doc, "Führe die isolierten Anschlusslitzen durch die fluchtenden seitlichen Öffnungen. Die Leitung braucht eine reale Zugentlastung und Kantenschutz; die graue Hülle zeigt lediglich den Kabeldurchgang. Sie ist keine montierte Durchführung und keine Abdichtung. Der Ausgang ist nicht wasserdicht. Halte das freie Kabel vollständig außerhalb der drehenden Teile.")


def _rotor(doc, data):
    _page(doc, "8 Rotorstapel montieren", level=1)
    _figure(doc, "E01", data)
    _paragraph(doc, "Auf die bereits gelagerte Base folgen fünf identische Standardmodule und abschließend das Topmodul. Die M8-Welle läuft durch die freien Mitten und die kurzen Führungsbereiche. Halte den Stapel während der Montage gegen Kippen gesichert.")
    _steps(doc, [
        ("Einfügeposition ausrichten", "Jede neue Stufe anhand der passenden Klauen und Einführfenster gegenüber der darunterliegenden Stufe orientieren. Vor dem endgültigen Fügen müssen Nut und Feder an der Blattnaht zusammenpassen."),
        ("Stufe verriegeln", "Von oben gesehen gegen den Uhrzeigersinn bis zum vorgesehenen Anschlag verriegeln. Die dauerhafte Rastung muss greifen. Kein übermäßiges Drehmoment und keinen Hammer verwenden; bei klemmender Verbindung die Coupons und Passflächen prüfen."),
        ("Naht prüfen", "Sitz aller Klauen, Blattnaht und axiales Spiel jeder Verbindung kontrollieren. Ein sichtbarer Versatz oder ein beschädigter Rastzahn ist ein Abbruchgrund. Den nächsten Abschnitt erst nach dieser Kontrolle aufsetzen."),
        ("Obere Klemmung schließen", "Scheibe und M8-Mutter auf dem verstärkten Topbereich einsetzen. Klemmung vor der Montage des oberen Lagerhalters einstellen. Der reale Lagerlauf und die Blattverbindungen dürfen beim Anziehen nicht verspannt werden."),
    ])
    _page(doc, "Drei Modultypen unterscheiden")
    _figure(doc, "E02", data)
    _paragraph(doc, "Die Base besitzt den oberen Magnetträger und den 51105-Zentrierbund. Das Standardmodul trägt unten das männliche und oben das weibliche Verbindungsteil. Das Topmodul beendet den Stapel mit einem lokalen Kraftbereich für die obere M8-Klemmung. Alle drei Typen sind jeweils ein Druckkörper.")
    _page(doc, "Bajonett und Blattnaht kontrollieren")
    _figure(doc, "E03", data)
    _paragraph(doc, "Die Rastung ist für eine dauerhafte Verbindung vorgesehen. Plane den Rotorstapel als Einheit; ein Spulenwechsel soll keine Trennung der sechs Stufenverbindungen erfordern. Die reale elastische Einfügung und Kraftübertragung bleiben durch Coupons und einen Aufbau aus zwei Stufen zu bestätigen.")


def _frame(doc, data):
    _page(doc, "9 Am Holzrahmen montieren", level=1)
    _paragraph(doc, "Die M8-Klemmung am Topmodul zuerst fertig einstellen und Werkzeugzugang prüfen. Danach die verlängerte M8-Welle durch den oberen Lagerpunkt führen. Rahmenabstand und Stangenlänge ergeben sich aus der realen Trockenmontage einschließlich Lager, Muttern, Spiel und notwendigen Gewindeeingriffen.")
    _steps(doc, [
        ("Unteren Rahmen vorbereiten", "Auflage eben und tragfähig ausführen. Das Gehäuse steht mit vier Bodenlaschen auf dem Holz. Die vier unteren Holzschrauben werden von oben nach unten außerhalb des rotierenden Innenraums eingebracht. Vorbohrung, Randabstand und Schraubenlänge am vorhandenen Holz festlegen."),
        ("Halter montieren", "608 von oben in den offenen Lagersitz des stationären Halters setzen. Halter mit vier Holzschrauben von unten nach oben gegen den oberen Holzrahmen montieren. Die untere Schulter hält das Lager nach unten; das Holz schließt den Sitz und hält es nach oben zurück."),
        ("Welle ausrichten", "Oberen Halter zur unteren Lagerachse ausrichten, bevor die vier Schrauben endgültig gesetzt werden. Die Welle muss ohne seitlichen Zwang durch den 608 laufen. Abstand zu Topmodul, Scheibe und Mutter über eine volle Handumdrehung prüfen."),
        ("Wellenende prüfen", "Die verlängerte Welle muss den Innenring über dessen ganze Breite führen und auch bei axialem Spiel sicher eingreifen. Freiraum am oberen Holz für Wellenende und Bewegung vorsehen. Überstand nicht gegen den Holzrahmen verspannen."),
    ])
    _figure(doc, "E13", data)
    _page(doc, "Befestigung zwischen den Holzriegeln")
    _figure(doc, "E14", data)
    _paragraph(doc, "Die Zeichnung verwendet unten 4 × 30 mm und oben 4 × 40 mm als ungeprüfte Schraubenhüllen. Holzquerschnitte sind Beispiele. Sie sind keine Freigabe für den vorhandenen Zaun oder eine bestimmte Windlast. Die Befestigung und das Holz vor Ort auslegen und prüfen.")
    _paragraph(doc, "Der obere Lagerhalter führt radial. Die vorgesehene axiale Lastabstützung erfolgt am unteren 51105. Nach dem Verschrauben nochmals Handlauf, Lagergeräusch, kleinsten Luftspalt und Kabelabstand kontrollieren. Erst danach den geschützten Prüfstand für Messungen vorbereiten.")


def _measurements(doc):
    _page(doc, "10 Spulen messen und vergleichen", level=1)
    _paragraph(doc, "Vergleiche jede Spule bei denselben protokollierten Drehzahlen und derselben Last. Die drei Windungszahlen sind eine experimentelle Matrix. Ein höherer Leerlaufwert allein zeigt nicht, welche Spule unter Last brauchbar arbeitet.")
    _steps(doc, [
        ("Spule im Stillstand prüfen", "Drahtdurchmesser, Windungszahl, Verlauf, Wicklungshöhe, Widerstand und Umgebungstemperatur notieren. Leiterenden eindeutig A und B markieren. Isolation zu Welle und Magnetträgern kontrollieren."),
        ("Leerlauf messen", "Im geschützten Aufbau langsam und kontrolliert antreiben. Drehzahl und AC-Leerlaufspannung gleichzeitig erfassen. Die Bandbreite des Messgeräts muss zur tatsächlichen Signalform passen. Einen offenen Messkontakt nicht als geringe Generatorleistung deuten."),
        ("Definierte Last anschließen", "Nur eine zuvor passend bemessene Last verwenden. Bei gleicher Drehzahl Spannung, Strom und Temperatur erfassen. Lastwert, Messdauer, Umgebung und Kabelzustand festhalten. Bei heißer Wicklung, Geruch, Vibration oder Kontakt sofort stillsetzen."),
        ("Ergebnisse vergleichen", "Für rein ohmsche Lasten kann die mittlere Leistung aus geeignet gemessenen Effektivwerten bestimmt werden. Bei Gleichrichter oder gepulstem Strom passende DC- oder echte Leistungsmessung verwenden; AC-Werte nicht ungeprüft multiplizieren."),
    ])
    _table(doc, ["Messgröße", "Für jeden Versuch dokumentieren"], [
        ("Identität", "Spulenkennung, Material, realer Drahtdurchmesser, Lackdurchmesser, Windungen und Drahtweg"),
        ("Mechanik", "Magnetpolfolge, Magnetüberstand, Spulenhöhe, kleinster oberer und unterer Luftspalt"),
        ("Elektrik", "Widerstand kalt, Drehzahl, AC-Leerlaufspannung, Lastwert, Lastspannung und Laststrom"),
        ("Wärme und Zeit", "Umgebungstemperatur, Spulentemperatur, Messdauer und Temperaturverlauf"),
        ("Beobachtung", "Anlaufverhalten, Geräusche, Vibration, Schleifen, lockere Teile und Abbruchgrund"),
    ], [42, 132])
    _paragraph(doc, "Eine Windungsskalierung aus der Leerlaufspannung ist höchstens eine erste Näherung bei unverändertem Magnetfeld, Verlauf und gleicher Drehzahl. Widerstand, Kupferfüllung, Bauraum und Erwärmung ändern sich mit. Jede abgeleitete Wicklung muss erneut als reale Spule geprüft werden.")


def _commissioning(doc):
    _page(doc, "11 Geschützt in Betrieb nehmen", level=1)
    _paragraph(doc, "Eine erste Drehprobe setzt bestätigte Magnetrückhaltung, feste Rahmenbefestigung, geschlossene Kassettensicherung und einen freien Handlauf voraus. Abschirmung gegen herausgeschleuderte Teile und eine sichere Stillsetzmöglichkeit vorsehen. Personen, Haare, Kleidung und lose Gegenstände von der Rotation fernhalten.")
    _steps(doc, [
        ("Stillstand kontrollieren", "Schraubenmarkierungen, Rastverbindungen, Lager, Kabel und beide Luftspalte prüfen. Fremdkörper entfernen. Elektrische Messleitungen vor der Bewegung befestigen."),
        ("Langsam beginnen", "Drehung unter kontrollierten Bedingungen stufenweise erhöhen und nach jeder Änderung beobachten. Es gibt keine freigegebene Höchstdrehzahl. Keine Wind-, Sturm- oder Überdrehzahlprobe aus dieser Anleitung ableiten."),
        ("Bei Abweichungen stoppen", "Schleifen, Risse, Magnetbewegung, auffällige Lagergeräusche, Erwärmung oder lockere Befestigung erfordern Stillstand und Ursachensuche. Erst nach Korrektur und erneuter Handprüfung fortfahren."),
    ])
    doc.add_heading("Ladeelektronik erst nach Messungen auswählen", 2)
    _paragraph(doc, "Den Generator nicht direkt an einen 48-V-Bleiakku anschließen, auch nicht versuchsweise. Nennspannung und Leerlaufmessung reichen für die Auswahl eines Ladesystems nicht aus. Batterietyp und Ladeprofil müssen zum konkreten Hersteller passen.")
    _paragraph(doc, "Ein späterer Anschlussplan muss Gleichrichtung, geeignete Laderegelung, Rückstromsperre, Leitungs- und Kurzschlussschutz, sichere Trennung und Energieabfuhr bei fehlender Last abdecken. Bauteile nach gemessener Spannung, Strom, Wärme und Fehlerfällen auswählen. Eine gegebenenfalls erforderliche Ersatzlast muss thermisch und elektrisch ausgelegt sein. Diese Anleitung enthält dafür keinen freigegebenen Schaltplan.")
    _paragraph(doc, "Die Entwicklung bleibt bis dahin am definierten Messaufbau. Freier Lauf im Wind, Ladebetrieb, Wassereintritt, UV, Frost, Dauerlast und unbeaufsichtigter Betrieb sind nicht validiert.")


def _service(doc):
    _page(doc, "12 Wartung und Fehlersuche", level=1)
    doc.add_heading("Spulenkassette entnehmen", 2)
    _steps(doc, [
        ("Stillsetzen und abstützen", "Rotor mechanisch gegen Bewegung sichern und elektrische Leitungen spannungsfrei trennen. Den Rotorstapel als Einheit abstützen. Magnetkräfte und Gewicht beim Ausbau kontrollieren."),
        ("Oberen Zugang freimachen", "Oberen Lagerhalter bei gesichertem Stapel lösen und Welle freiführen. Die untere rotierende Baugruppe mit einer Montagehilfe halten. Base und oberen Rotorstrang soweit entlasten und abheben, dass das 51105 und der Deckel zugänglich werden. Erforderliche M8-Verbindungen im Stillstand lösen, ohne die Stufenrastungen zu trennen."),
        ("Deckel abnehmen", "Lagerteile nach ihrer Orientierung getrennt ablegen. Sechs Deckelschrauben lösen, Deckel abheben und Kabelzugentlastung freigeben. Der untere Magnetrotor bleibt gesichert im Gehäuse."),
        ("Kassette nach oben herausheben", "Kabel vorsichtig nachführen, Schlüssel aus der Nut heben und Kassette nach oben über die freigegebene Welle entnehmen. Nicht am Draht ziehen. Der reale Serviceweg ist bei der Trockenmontage zu prüfen."),
        ("Wieder montieren", "Nach Kapitel 7 in Reihenfolge montieren, oberen Halter wieder ausrichten und alle Freigänge erneut messen. Ein Spulenwechsel kann Wicklungshöhe und Luftspalte verändern."),
    ])
    _paragraph(doc, "Vor jeder Versuchssitzung und nach Transport, Materialwechsel oder Spulenwechsel Risse, Verzug, Spiel, Schraubenmarkierungen, Magnetbefestigung und Isolation prüfen. Verschleiß oder gelöste Teile ersetzen und die betroffene Passprüfung wiederholen.")
    _table(doc, ["Beobachtung", "Prüfung bei Stillstand"], [
        ("Rotor schleift", "Magnetüberstand, Spulenhöhe, beide Luftspalte, Distanzhülse und axialen Versatz messen."),
        ("Schwergängiges Lager", "Scheibenorientierung, verkantete Sitze, obere Achsausrichtung und axiale Verspannung kontrollieren."),
        ("Kassette bewegt sich", "Schulter, Schlüssel, Passring und plan sitzenden Deckel auf Druckfehler prüfen."),
        ("Geringe oder keine Spannung", "Drehzahl, Drahtdurchgang, Lötstellen, Polfolge und additive Verschaltung des Serpentinenwegs prüfen."),
        ("Wicklung wird heiß", "Laststrom, Wicklungswiderstand, Isolation und Wärmeabfuhr prüfen; keine weitere Drehprobe bis zur Klärung."),
        ("Vibration oder lockere Muttern", "Rundlauf, Magnetverteilung, Rahmensteifigkeit und M8-Klemmung prüfen; nicht durch höhere Drehzahl übergehen."),
    ], [53, 121])


def _records(doc, data):
    _page(doc, "13 Versuche dokumentieren", level=1)
    _paragraph(doc, "Führe für jede Bauvariante ein eigenes Protokoll mit Datum, Material, Druckprofil und verwendeten Release-Dateien. Bewahre Fotos der Polfolge, der Drahtführung und der realen Montage auf. Ein erfolgreicher Einzelversuch ist keine Dauer- oder Außenfreigabe.")
    _table(doc, ["Prüfbereich", "Erforderlicher Nachweis"], [
        ("Druck und Passungen", "Couponvariante, reale Maße, Fügekräfte, Rissfreiheit und Materialprofil"),
        ("Mechanische Montage", "Muttereingriff, Lagerorientierung, Wellenlänge, Rahmenbefestigung und freie Handumdrehung"),
        ("Generator", "Magnetbefestigung, Polfolge, tatsächlicher Überstand und kleinste Luftspalte"),
        ("Spule", "Matrix aus Kapitel 6 und Messdaten aus Kapitel 10 einschließlich Temperatur"),
        ("Weiterer Versuch", "Begründung, offene Punkte, Abbruchkriterien und notwendige Korrekturen"),
    ], [54, 120])
    doc.add_heading("Zeichnungen finden", 2)
    _table(doc, ["ID", "Datei"], [(key, item["filename"]) for key, item in data["drawings"].items()], [16, 158], centered=(0,))
    doc.add_heading("Projektstand und Aussagegrenzen", 2)
    _paragraph(doc, "Release-Inventar und Maße: release/v5/manifest.json. Zeichnungen und Bildbeschreibungen: release/v5/drawings/figures.json. Die Anleitung gilt für den V5-Aufbau mit stationärem Generatorgehäuse und oberem Lagerhalter.")
    _paragraph(doc, "Physische Passung, Lagerhalt, Magnetrückhaltung, elektrische Funktion, Festigkeit, Dauerfestigkeit, Überdrehzahl und Wetterverhalten bleiben nachzuweisen. CAD-Freigänge und geschlossene STL-Körper ersetzen diese Versuche nicht. Erst bestätigte Messungen erlauben den nächsten Entwicklungsschritt.")


def _save_deterministic(doc, output_path: Path):
    buffer = BytesIO()
    doc.save(buffer)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(buffer) as source, ZipFile(output_path, "w", ZIP_DEFLATED) as target:
        for name in sorted(source.namelist()):
            info = ZipInfo(name, (2026, 9, 9, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            target.writestr(info, source.read(name))


def build_v5_manual(project_root: Path, output_path: Path) -> Path:
    """Create the complete manual only after validating its V5 input binding."""
    data = load_manual_data(project_root)
    doc = _setup_document()
    _scope(doc, data)
    _inventory(doc, data)
    _hardware(doc, data)
    _printing(doc, data)
    _fits(doc, data)
    _winding(doc, data)
    _generator(doc, data)
    _rotor(doc, data)
    _frame(doc, data)
    _measurements(doc)
    _commissioning(doc)
    _service(doc)
    _records(doc, data)
    output_path = Path(output_path)
    _save_deterministic(doc, output_path)
    return output_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.project_root / "release/v5/docs/Ugrinsky-Wind-Wall-V5-Bauanleitung.docx"
    print(build_v5_manual(args.project_root, output))


if __name__ == "__main__":
    main()
