# MC POS - Modular Checkout System

**Version:** Alpha 0.1.9.4  
**Entwickler:** [T0mk4](https://github.com/T0mk4)  
**Status:** Alpha-Entwicklungsphase

MC POS ist ein modernes, Python-basiertes Point-of-Sale-System (POS), das speziell für kleine Unternehmen entwickelt wurde, die eine einfache Lagerverwaltung mit Seriennummern-Erfassung und automatischer Beleg-Erstellung benötigen.

---

## 🚀 Kernfunktionen

### 🛒 Kassen-Modul
* **Visuelles Interface:** Produktkacheln mit Bild-Vorschau und aktueller Lageranzeige.
* **Warenkorb-Logik:** Schnelles Hinzufügen von Artikeln per Klick.
* **Bestandsschutz:** Automatischer Check vor dem Hinzufügen. Artikel ohne Bestand können nicht verkauft werden.
* **Automatisierter Warenausgang:** Bei jedem Verkauf wird der Bestand in der Datenbank automatisch reduziert.

### 📦 Lager & Logistik
* **Wareneingang:** Einbuchen von Beständen mit frei wählbarem Datum (DatePicker).
* **Seriennummern-Tracking:** Dynamische Generierung von Eingabefeldern basierend auf der Menge. Wenn 5 Artikel eingebucht werden, erscheinen exakt 5 SN-Felder.
* **Historie:** Vollständige tabellarische Übersicht aller Lagerbewegungen.

### 📄 Belegwesen & Mandanten
* **PDF-Generierung:** Erstellung professioneller Kassenbelege mit Logo, Shop-Daten und automatischer MwSt-Berechnung.
* **Mandantenverwaltung:** Zentrale Pflege von Anschrift, Email, Website und Steuernummer direkt in der App.
* **Auto-Open:** Der Beleg wird sofort nach dem Verkauf im Standard-PDF-Viewer geöffnet.

---

## 🛠 Installation

### Voraussetzungen
* Python 3.10 oder höher
* pip (Python Package Installer)

### Setup

1. **Repository klonen:**
   ```bash
   git clone [https://github.com/T0mk4/mc-pos.git](https://github.com/T0mk4/mc-pos.git)
   cd mc-pos