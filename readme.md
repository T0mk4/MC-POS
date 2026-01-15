MC POS - Modular Checkout System
Version: Alpha 0.1.9.4

Status: In Entwicklung (Alpha)

MC POS ist ein leichtgewichtiges, Python-basiertes Kassensystem mit integrierter Lagerverwaltung und automatischer Beleg-Erstellung. Es wurde speziell für eine einfache Handhabung und schnelle Bestandsführung entwickelt.

🚀 Features
Touch-Kasse: Intuitive Benutzeroberfläche mit Produktkacheln und Bild-Support.

Lagerverwaltung: Dynamischer Wareneingang mit optionaler Erfassung von Seriennummern pro Stück.

Bestandsschutz: Automatischer Abgleich der Bestände beim Verkauf; Verkauf bei Nullbestand wird blockiert.

Beleg-System: Automatische Generierung von PDF-Kassenbelegen inklusive Firmenlogo, MwSt.-Berechnung und Stammdaten.

Mandantenfähig: Einfache Einrichtung von Shop-Daten (Name, Anschrift, Steuernummer, etc.) direkt in der App.

Datenbank: Lokale Datenspeicherung mittels SQLite (kein externer Server nötig).

🛠 Installation
Repository klonen:

Bash

git clone https://github.com/DEIN_USERNAME/mc-pos.git
cd mc-pos
Virtuelle Umgebung erstellen:

Bash

python -m venv .venv
source .venv/bin/activate  # Unter Windows: .venv\Scripts\activate
Abhängigkeiten installieren:

Bash

pip install flet fpdf2
Assets vorbereiten: Stelle sicher, dass ein Ordner namens assets im Projektverzeichnis existiert, um Artikelbilder und Logos zu speichern.

💻 Starten
Starte die Anwendung einfach über Python:

Bash

python main.py
📂 Projektstruktur
main.py: Die Hauptanwendung (Logik & UI).

pos_data.db: SQLite-Datenbank (wird beim ersten Start automatisch erstellt).

assets/: Verzeichnis für Produktbilder und das Shop-Logo.

requirements.txt: Liste der benötigten Python-Module.

📝 Geplante Funktionen (Roadmap)
[ ] Umsatz-Statistiken und Tagesabschluss-Reports.

[ ] Barcode-Scanner-Integration.

[ ] Suchfunktion für Seriennummern in der Historie.

[ ] Rabatt-System und verschiedene Zahlungsmethoden.

Entwickelt von: [T0mk4]

Lizenz: MIT