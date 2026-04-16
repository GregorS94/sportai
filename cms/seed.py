"""Seed the CMS database with all Seelenmut pages.

Run once to populate the admin panel with editable pages:
    python3 seed.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

# Ensure imports work when run from the cms/ directory
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, get_db

NOW = datetime.utcnow().isoformat()

HOME_BLOCKS = json.dumps([
    {
        "type": "hero",
        "eyebrow": "Seelenmut · Julia",
        "title": "Trauma und Essstörung.",
        "subtitle": "Bindungs- und entwicklungsorientierte Innere Arbeit als Lösungsstrategie. Ein Leben ohne Essstörung ist möglich.",
        "cta_text": "Kostenloses Kennenlerngespräch",
        "cta_href": "/kontakt",
        "image": "",
    },
    {
        "type": "marquee",
        "items": "Recovery ist möglich. | Du darfst langsam sein. | Bindung vor Methode. | Der Körper erinnert sich. | Kein Schritt ist zu klein.",
    },
    {
        "type": "cards",
        "eyebrow": "So kann ich dich begleiten",
        "title": "Meine Angebote",
        "items": "1:1 Recovery Begleitung | Ein vertraulicher Raum für deinen Weg – in deinem Tempo. | /recovery-begleitung\n1:1 Trauma- & Nervensystem-Arbeit | Innere Arbeit, die an der Wurzel ansetzt. | /trauma-nervensystem\nFree Your Self | Online-Coaching für Frauen, die bereit sind, anzufangen. | /free-your-self",
    },
    {
        "type": "feature",
        "eyebrow": "Über mich",
        "title": "Ich bin Julia.",
        "text": "Diplomierte Lern-Pädagogin, Autorin, Psychologin und Ernährungstrainerin. Ich begleite Menschen aus der Essstörung – ehrlich, zugewandt, mit tiefem Verständnis für den Weg dahinter.",
        "bullets": "",
        "cta_text": "Meine Geschichte →",
        "cta_href": "/ueber-mich",
        "style": "light",
    },
    {
        "type": "cta",
        "eyebrow": "Nächster Schritt",
        "title": "Magst du schreiben?",
        "text": "Manchmal ist der erste Schritt ein einziger Satz. Er darf tastend sein, leise, unsicher. Ich lese ihn trotzdem.",
        "cta_text": "Kostenloses Kennenlerngespräch",
        "cta_href": "/kontakt",
        "style": "dark",
    },
])

PAGES = [
    {
        "slug": "home",
        "title": "Startseite",
        "excerpt": "Seelenmut – Julia. Recovery Begleitung, Trauma- & Nervensystem-Arbeit.",
        "meta_description": "Bindungs- und entwicklungsorientierte Innere Arbeit als Lösungsstrategie. Ein Leben ohne Essstörung ist möglich.",
        "sort_order": 0,
        "show_in_menu": 0,
        "content": "",
        "blocks": HOME_BLOCKS,
    },
    {
        "slug": "ueber-mich",
        "title": "Über mich",
        "excerpt": "Julia – Psychologin, Ernährungstrainerin, Autorin.",
        "meta_description": "Julia – Psychologin, Ernährungstrainerin, Autorin. Mein Weg und meine Arbeit bei Seelenmut.",
        "sort_order": 1,
        "show_in_menu": 1,
        "content": """## Hey, ich bin Julia.

Diplomierte Lern-Pädagogin, Autorin, Psychologin und Ernährungstrainerin.

Ich begleite Menschen aus der Essstörung – ehrlich, zugewandt, mit tiefem Verständnis für den Weg dahinter. Mein Ansatz ist bindungs- und entwicklungsorientiert, weil ich glaube, dass Heilung in Beziehung passiert.

Mein eigener Weg hat mich gelehrt, dass Recovery kein gerader Pfad ist. Es gibt Umwege, Rückschritte und Momente, in denen alles stillzustehen scheint. Aber jeder einzelne Schritt zählt.

> Ein Leben ohne Essstörung ist möglich.

## Meine Qualifikationen

- Diplomierte Lern-Pädagogin
- Psychologin
- Ernährungstrainerin
- Autorin

## Mein Ansatz

Ich arbeite bindungsorientiert und entwicklungsorientiert. Das bedeutet: Wir schauen gemeinsam, was unter der Oberfläche liegt – ohne zu urteilen, ohne zu bewerten. Dein Körper ist kein Problem. Er ist Kompass und Verbündeter.

In meiner Arbeit verbinde ich psychologisches Wissen mit Körperarbeit und Nervensystem-Regulierung. Jeder Mensch bringt seine eigene Geschichte mit – und genau dort setzen wir an.
""",
    },
    {
        "slug": "angebote",
        "title": "Meine Angebote",
        "excerpt": "Recovery Begleitung, Trauma- & Nervensystem-Arbeit, Free Your Self Gruppenprogramm.",
        "meta_description": "Recovery Begleitung, Trauma- & Nervensystem-Arbeit, Free Your Self Gruppenprogramm.",
        "sort_order": 2,
        "show_in_menu": 1,
        "content": """Jeder Weg ist anders. Deshalb gibt es verschiedene Möglichkeiten, wie ich dich begleiten kann.

## 1:1 Recovery Begleitung

Ein vertraulicher Raum für deinen Weg – in deinem Tempo, mit echtem Gegenüber. Gemeinsam schauen wir, was unter der Oberfläche liegt, und arbeiten daran, was dich wirklich bewegt.

- Bindungsorientierte Innere Arbeit
- Individuell auf dich abgestimmt
- Online oder vor Ort
- Vertraulich und wertfrei

## 1:1 Trauma- & Nervensystem-Arbeit

Innere Arbeit, die an der Wurzel ansetzt – dort wo Worte nicht mehr reichen. Wir arbeiten mit deinem Nervensystem, um alte Muster zu lösen und neue Wege zu bahnen.

- Trauma-sensitive Körperarbeit
- Nervensystem-Regulierung
- Somatische Ansätze
- In deinem Tempo

## Free Your Self – Gruppenprogramm

Online-Coaching für Frauen, die bereit sind, anzufangen. In Runden mit Begleitung – weil der Weg leichter wird, wenn du ihn nicht alleine gehst.

- Begleitete Gruppenrunden
- Online-Programm
- Gemeinschaft und Austausch
- Strukturierte Module

---

In einem kostenlosen Kennenlerngespräch finden wir gemeinsam heraus, welcher Weg zu dir passt.
""",
    },
    {
        "slug": "recovery-begleitung",
        "title": "1:1 Recovery Begleitung",
        "excerpt": "Lerne dich wieder in dir selbst zuhause zu fühlen.",
        "meta_description": "Individuelle Begleitung aus der Essstörung. Bindungsorientiert, in deinem Tempo.",
        "sort_order": 3,
        "show_in_menu": 0,
        "content": """## Lerne dich wieder in dir selbst zuhause zu fühlen.

Ich begleite dich persönlich und individuell auf deinem Weg zurück zu dir selbst. Deine Essstörung darf gehen – in deinem Tempo, mit echtem Gegenüber.

## Mein Motto: Ein Leben ohne Essstörung ist für jeden möglich!

Ich begleite dich als Expertin, aber auch als Mensch, der jeden Essanfall, jede Essstörung auch selbst erlebt hat. Mein Ziel ist es, dich zu verstehen und dir einen sicheren Raum zu geben.

## Woran du arbeiten wirst

### Das heile Wesen und Urvertrauen

Empathisch kehren wir zum originalen Teil deines Wesens zurück. Verschüttete, gute, noch nicht gelebte Gefühle und Bedürfnisse, die zuvor verdrängt worden sind. Nur durch den Kontakt mit den inneren Kindern kann Heilung und Genesung gelingen.

### Deinen Alltag und Hindernisse

Ich betrachte durch den täglichen WhatsApp-Kontakt die Hindernisse in deinem Alltag und helfe dir, Lösungen zu finden.

### Selbstregulation und Emotionsmanagement

Dein Nervensystem sorgt dafür, dass extreme Reaktionen entstehen. Diese Fähigkeiten hatten nie die Chance, sich Schritt für Schritt natürlich zu entwickeln. Gemeinsam lernen wir neue Wege.

### Nervensystem und Körperkompetenz

Mein Herzstück ist die Trauma- und Nervensystemarbeit. Alle Praktiken und Übungen sind darauf ausgelegt, dich wieder mit deinem Körper als Freund zu verbinden.

## Aufbau des 1:1 Coachings

- **1:1 Coachingstunden** – Regelmäßige Sessions
- **Tägliche Betreuung** – WhatsApp-Support zu jeder Zeit
- **Hunger natürliche Liebe** – Intuitive Ernährungsbegleitung
- **Lebenslauf & Co Paket** – Ganzheitliche Unterstützung

---

Betrachte DICH als den wichtigsten Menschen in deinem Leben. Du bist nicht zu klein, zu ruhelos – du verdienst es, dein Leben zu leben.

## Das sagen Seelenmut Klienten

> Julia, ich muss dir schnell kurz was berichten, weil es einfach gerade so eine krasse Erfahrung für mich ist. Ich höre plötzlich Dinge. Also alltägliche Dinge. Das Auto auf der Straße. Meine Schritte, wenn ich über den Teppich laufe. Diese Geräusche habe ich NIE wahrgenommen. Aber seit unserer Session heute Morgen ist eine derartige Ruhe in meinem Kopf. Wow. Das fühlt sich einfach nur toll an.

> Danke dir nochmal sehr für all deine Unterstützung auch jetzt in dieser schweren Zeit die letzten Monate. Du warst eine riesen Stütze für mich, ohne die es sicher nicht so leicht gewesen wäre. Ehrlich gesagt weiß ich nicht mal, ob ich ohne deine ganze gemeinsame Arbeit den Mut gehabt hätte mich zu trennen. Deshalb wirklich vielen Dank von ganzem Herzen.

> Ich hatte das große Glück, über mehrere Monate an einem 1:1 Coaching bei Julia teilnehmen zu dürfen. Mit ihrer liebevollen und empathischen Art hat sie mich begleitet, unterstützt und in schwierigen Momenten aufgefangen. Besonders war auch die 24/7-Begleitung über WhatsApp, die mir das Gefühl von Sicherheit und Geborgenheit gab. Ich kann Julia von Herzen weiterempfehlen!
""",
    },
    {
        "slug": "trauma-nervensystem",
        "title": "1:1 Trauma- & Nervensystem-Arbeit",
        "excerpt": "Alte Wunden schließen und dein inneres Kind nach Hause holen.",
        "meta_description": "Körperbasierte, traumasensible Arbeit. Alte Wunden schließen und dein inneres Kind nach Hause holen.",
        "sort_order": 4,
        "show_in_menu": 0,
        "content": """## Alte Wunden schließen und dein inneres Kind nach Hause holen.

Entwicklungsorientierte Arbeit betrifft uns alle. Trauma muss nicht groß und schlimm sein. Als kleines Kind reichen kleine Dinge aus, um das Nervensystem überfluten zu lassen.

## Warum ein Nervensystem in Balance dich Frieden fühlen lässt

### Fühlst du dich hier angesprochen?

**Kennst du das wirklich noch,** oder schmerzt dein Körper schon lange nach Ruhe? Lebst du an den Tagen wo es „dir gut geht" normalerweise über deinen Kapazitäten, kann dein Nervensystem nur von einem Extrem ins andere – nämlich die totale Erschöpfung – fallen.

Stelle dir einmal vor: Aus dem Gefühl der Rastlosigkeit, egal ständig unter Strom stehen und einem Nervensystem der Überzeugung, dass nur Extreme wie Kampf oder Flucht „klappen".

Du kennst Ruhe, dieses Gefühl von „es ist alles gut". Es gibt keine Gefahr, wenn ich mich ausruhe. Dein Nervensystem ist endlich in Balance, sogar beim Gedanken an Meinungen und den To-Dos entwickelt kein Druckgefühl mehr.

Entdecke in einer körperbasierten und traumasensiblen Arbeit, wie du dich aus den Spiralen der Angst löst und dadurch innere Sicherheit sowie Freiheit in dem Leben spürst.

In meiner 1:1 gehe ich zusammen mit meinen Klienten immer wieder auf die Baustellen, die du brauchst, um nachhaltig inneren Frieden herzustellen:

- Erlaubnisraum für deinen Körper schaffen. Dein Körper erinnert sich, auch wenn du es vielleicht mit deinem Verstand nicht mehr kannst.
- Innere Sicherheit neu verankern
- Aufbau deiner neuen inneren Teamarbeit

## Wie ich traumasensibel arbeite

### Verständnis von Trauma
Insbesondere Entwicklungstrauma und dessen Wirkung auf Körper und Nervensystem.

### Wer bin ich nach Trauma
Die eigene Identität jenseits der Verletzungen wiederfinden und stärken.

### Erlernen von Techniken
Selbstfürsorge sowie Regulation deines Nervensystems – praktisch und alltagstauglich.

---

- Praktiken zur Stressreduzierung
- Ressourcenaufbau und Stärkung deiner Resilienz
- Innere Sicherheit in deinem Körper

## Wem eignet sich die körperbasierte und traumasensible Arbeit?

**Wenn Du...**

- das Gefühl hast, getrieben zu sein, vor etwas fernzubleiben, zu gar nicht deinen Willen hin entfliehst
- unter Verspannungen, Schmerzen, Schlauuch und Magen-Darm-Beschwerden leidest für die es keine physische Ursache gibt
- deine Bedürfnisse immer wieder runter anstößt
- fühlst, dass dein Nervensystem sich anfühlt, als würdest du auf einem Vulkan leben, in Hochspannung
- unter Erschöpfung und Müdigkeit leidest
- im Kopf bereits alles verstanden hast, aber es trotz Umstellung scheitert
- mit deinem Körper einfach ein Team werden möchtest
- spürst, dass alte Themen und Glaubenssätze immer noch ansetzen

## Das sagen Seelenmut Klienten

> Julia, ich muss dir schnell kurz was berichten, weil es einfach gerade so eine krasse Erfahrung für mich ist. Ich höre plötzlich Dinge. Also alltägliche Dinge. Wow. Das fühlt sich einfach nur toll an.

> Danke dir nochmal sehr für all deine Unterstützung. Du warst eine riesen Stütze für mich. Deshalb wirklich vielen Dank von ganzem Herzen.

> Ich hatte das große Glück, über mehrere Monate an einem 1:1 Coaching bei Julia teilnehmen zu dürfen. Mit ihrer liebevollen und empathischen Art hat sie mich begleitet, unterstützt und in schwierigen Momenten aufgefangen. Ich kann Julia von Herzen weiterempfehlen!
""",
    },
    {
        "slug": "free-your-self",
        "title": "Free Your Self",
        "excerpt": "Online-Gruppenprogramm für Frauen auf dem Weg aus der Essstörung.",
        "meta_description": "Online-Gruppenprogramm für Frauen auf dem Weg aus der Essstörung. Begleitet, strukturiert, gemeinsam.",
        "sort_order": 5,
        "show_in_menu": 1,
        "content": """## Free Your Self.

Online-Coaching für Frauen, die bereit sind, anzufangen. In begleiteten Runden – weil der Weg leichter wird, wenn du ihn nicht alleine gehst.

## Was ist Free Your Self?

Free Your Self ist ein strukturiertes Online-Gruppenprogramm, das dich über mehrere Wochen begleitet. In einer kleinen, geschützten Gruppe arbeiten wir gemeinsam an den Themen, die hinter der Essstörung liegen.

- **Format:** Online-Gruppencoaching
- **Gruppengröße:** Kleine, geschützte Runde
- **Dauer:** Mehrere Wochen, begleitet
- **Für wen:** Frauen auf dem Weg aus der Essstörung

## Die Module

### 01 – Ankommen
Den eigenen Standpunkt finden. Verstehen, wo du stehst – ohne Bewertung.

### 02 – Verstehen
Die Muster hinter der Essstörung erkennen. Was dein Körper dir sagen will.

### 03 – Fühlen
Emotionen zulassen lernen. Dein Nervensystem als Verbündeten entdecken.

### 04 – Lösen
Alte Bindungsmuster erkennen und neue Wege bahnen – Schritt für Schritt.

### 05 – Leben
Recovery in den Alltag integrieren. Ein Leben ohne Essstörung leben.

---

Schreib mir, wenn du Interesse hast oder Fragen zum Programm hast. Unverbindlich, vertraulich.
""",
    },
    {
        "slug": "impressum",
        "title": "Impressum",
        "excerpt": "Angaben gemäß § 5 TMG.",
        "meta_description": "Impressum und Angaben gemäß § 5 TMG.",
        "sort_order": 10,
        "show_in_menu": 0,
        "content": """## Angaben gemäß § 5 TMG

Julia [Nachname]
Seelenmut
[Straße Nr.]
[PLZ Ort]
Österreich

## Kontakt

E-Mail: kontakt@seelenmut.net

## Berufsbezeichnung

Diplomierte Lern-Pädagogin, Psychologin, Ernährungstrainerin

## Haftungsausschluss

### Haftung für Inhalte

Die Inhalte dieser Seiten wurden mit größter Sorgfalt erstellt. Für die Richtigkeit, Vollständigkeit und Aktualität der Inhalte kann jedoch keine Gewähr übernommen werden.

### Haftung für Links

Diese Website enthält Links zu externen Webseiten Dritter, auf deren Inhalte kein Einfluss besteht. Für die Inhalte der verlinkten Seiten ist stets der jeweilige Anbieter verantwortlich.

## Urheberrecht

Die durch die Seitenbetreiberin erstellten Inhalte und Werke auf diesen Seiten unterliegen dem Urheberrecht. Die Vervielfältigung, Bearbeitung, Verbreitung und jede Art der Verwertung außerhalb der Grenzen des Urheberrechtes bedürfen der schriftlichen Zustimmung.

---

*Bitte ergänze dieses Impressum mit deinen vollständigen Angaben, bevor die Seite öffentlich geht.*
""",
    },
    {
        "slug": "datenschutz",
        "title": "Datenschutz",
        "excerpt": "Datenschutzerklärung von Seelenmut.",
        "meta_description": "Datenschutzerklärung von Seelenmut.",
        "sort_order": 11,
        "show_in_menu": 0,
        "content": """## 1. Datenschutz auf einen Blick

### Allgemeine Hinweise

Die folgenden Hinweise geben einen einfachen Überblick darüber, was mit deinen personenbezogenen Daten passiert, wenn du diese Website besuchst.

### Datenerfassung auf dieser Website

Die Datenverarbeitung auf dieser Website erfolgt durch die Websitebetreiberin. Die Kontaktdaten findest du im [Impressum](/impressum).

## 2. Hosting

Diese Website wird bei einem externen Dienstleister gehostet. Die personenbezogenen Daten, die auf dieser Website erfasst werden, werden auf den Servern des Hosters gespeichert.

## 3. Allgemeine Hinweise und Pflichtinformationen

### Datenschutz

Die Betreiberin dieser Seiten nimmt den Schutz deiner persönlichen Daten sehr ernst. Deine personenbezogenen Daten werden vertraulich und entsprechend der gesetzlichen Datenschutzvorschriften behandelt.

### Verantwortliche Stelle

Julia [Nachname]
Seelenmut
[Straße Nr.]
[PLZ Ort]
Österreich
E-Mail: kontakt@seelenmut.net

## 4. Datenerfassung auf dieser Website

### Server-Log-Dateien

Der Provider der Seiten erhebt automatisch Informationen in Server-Log-Dateien:

- Browsertyp und Browserversion
- Verwendetes Betriebssystem
- Referrer URL
- Hostname des zugreifenden Rechners
- Uhrzeit der Serveranfrage
- IP-Adresse

### Kontaktaufnahme per E-Mail

Wenn du per E-Mail Kontakt aufnimmst, wird deine Anfrage inklusive aller personenbezogenen Daten zum Zwecke der Bearbeitung gespeichert.

## 5. Externe Dienste

### Google Fonts

Diese Seite nutzt Google Fonts. Beim Aufruf einer Seite lädt dein Browser die benötigten Fonts in deinen Browsercache.

## 6. Deine Rechte

Du hast jederzeit das Recht auf:

- Auskunft über deine gespeicherten personenbezogenen Daten
- Berichtigung unrichtiger Daten
- Löschung deiner Daten
- Einschränkung der Datenverarbeitung
- Widerspruch gegen die Verarbeitung
- Datenübertragbarkeit

Hierzu kannst du dich jederzeit unter der im [Impressum](/impressum) angegebenen Adresse an mich wenden.

---

*Bitte ergänze diese Datenschutzerklärung mit deinen vollständigen Angaben und lass sie ggf. rechtlich prüfen, bevor die Seite öffentlich geht.*
""",
    },
]


def seed():
    init_db()
    with get_db() as db:
        for page in PAGES:
            existing = db.execute(
                "SELECT id FROM pages WHERE slug = ?", (page["slug"],)
            ).fetchone()
            if existing:
                print(f"  Seite '{page['slug']}' existiert bereits – übersprungen.")
                continue
            db.execute(
                "INSERT INTO pages (slug, title, content, excerpt, meta_title, "
                "meta_description, blocks, status, sort_order, show_in_menu, created_at, "
                "updated_at, published_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    page["slug"],
                    page["title"],
                    page.get("content", ""),
                    page["excerpt"],
                    page["title"],
                    page["meta_description"],
                    page.get("blocks", "[]"),
                    "published",
                    page["sort_order"],
                    page["show_in_menu"],
                    NOW,
                    NOW,
                    NOW,
                ),
            )
            print(f"  + Seite '{page['slug']}' angelegt.")
        db.commit()
    print("\nFertig! Alle Seiten sind im CMS.")


if __name__ == "__main__":
    seed()
