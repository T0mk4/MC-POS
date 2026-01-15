import flet as ft
import sqlite3
import shutil
import os
import webbrowser
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = sqlite3.connect("pos_data.db", check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL, price REAL NOT NULL, image_path TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY,
                shop_name TEXT, address TEXT, email TEXT, web TEXT, 
                tax_id TEXT, tax_rate REAL, logo_path TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER, quantity INTEGER, serials TEXT, entry_date TEXT,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        """)
        cursor.execute("INSERT OR IGNORE INTO settings (id, shop_name, tax_rate) VALUES (1, 'Mein Shop', 19.0)")
        self.conn.commit()

    def get_products(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM products")
        return cursor.fetchall()

    def get_stock(self, product_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT SUM(quantity) FROM stock_entries WHERE product_id = ?", (product_id,))
        result = cursor.fetchone()[0]
        return result if result else 0

    def get_all_stock_history(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT p.name, s.quantity, s.serials, s.entry_date 
            FROM stock_entries s 
            JOIN products p ON s.product_id = p.id 
            ORDER BY s.id DESC
        """)
        return cursor.fetchall()

    def add_product(self, name, price, image_path):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO products (name, price, image_path) VALUES (?, ?, ?)", (name, price, image_path))
        self.conn.commit()

    def add_stock(self, product_id, qty, serials, date_str):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO stock_entries (product_id, quantity, serials, entry_date) VALUES (?, ?, ?, ?)", 
                       (product_id, qty, serials, date_str))
        self.conn.commit()

    def delete_product(self, product_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM stock_entries WHERE product_id = ?", (product_id,))
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        self.conn.commit()

    def save_settings(self, data):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE settings SET shop_name=?, address=?, email=?, web=?, tax_id=?, tax_rate=?, logo_path=? WHERE id=1", data)
        self.conn.commit()

    def get_settings(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM settings WHERE id=1")
        return cursor.fetchone()

def main(page: ft.Page):
    page.title = "MC POS - Alpha 0.1.9.4"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#1e1e1e"
    
    db = Database()
    cart = []
    temp_img = {"prod": "", "logo": ""}
    file_picker_mode = ft.Text("")

    def show_msg(text, color="green"):
        page.snack_bar = ft.SnackBar(content=ft.Text(text, color="white"), bgcolor=color)
        page.snack_bar.open = True
        page.update()

    def generate_receipt():
        s = db.get_settings()
        pdf = FPDF()
        pdf.add_page()
        if s[7] and os.path.exists(f"assets/{s[7]}"):
            pdf.image(f"assets/{s[7]}", x=10, y=8, w=35)
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 10, str(s[1]), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(0, 5, f"{s[2]}\nEmail: {s[3]}\nWeb: {s[4]}\nSt.-Nr: {s[5]}", align="R")
        pdf.ln(15)
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 10, f"KASSENBELEG - {datetime.now().strftime('%d.%m.%Y %H:%M')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        total = 0
        pdf.set_font("helvetica", "", 11)
        for item in cart:
            pdf.cell(140, 8, item['name'], border=0)
            pdf.cell(50, 8, f"{item['price']:.2f} EUR", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")
            total += item['price']
        pdf.ln(5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(140, 10, "GESAMTSUMME", border=0)
        pdf.cell(50, 10, f"{total:.2f} EUR", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")
        tax_rate = s[6] or 19.0
        netto = total / (1 + tax_rate/100)
        pdf.set_font("helvetica", "I", 9)
        pdf.cell(0, 10, f"Enthaltene MwSt ({tax_rate}%): {total - netto:.2f} EUR", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")
        fname = f"Beleg_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf.output(fname)
        webbrowser.open(fname)

    # --- UI Elemente ---
    product_grid = ft.GridView(expand=True, runs_count=4, max_extent=200, spacing=10)
    cart_list = ft.ListView(expand=True, spacing=5)
    total_text = ft.Text("Summe: 0.00€", size=25, weight="bold")
    
    p_name, p_price = ft.TextField(label="Produktname", width=350), ft.TextField(label="Preis", width=350)
    p_status = ft.Text("", italic=True, color="grey")
    p_list = ft.ListView(expand=True, spacing=5)

    stock_product_dropdown = ft.Dropdown(label="Produkt wählen", width=350)
    sn_container = ft.Column(spacing=5)
    
    def on_qty_change(e):
        sn_container.controls.clear()
        try:
            val = int(e.control.value)
            for i in range(val):
                sn_container.controls.append(ft.TextField(label=f"SN {i+1}", width=350, dense=True))
        except: pass
        page.update()

    stock_qty = ft.TextField(label="Menge", value="1", width=100, on_change=on_qty_change)
    selected_date = ft.Text(datetime.now().strftime("%d.%m.%Y"), size=16, weight="bold")
    stock_history_table = ft.DataTable(columns=[ft.DataColumn(ft.Text("Datum")), ft.DataColumn(ft.Text("Produkt")), ft.DataColumn(ft.Text("Menge")), ft.DataColumn(ft.Text("SN"))])

    s_fields = [ft.TextField(label=l, width=350) for l in ["Shop Name", "Anschrift", "Email", "Web", "St.-Nr", "MwSt %"]]
    s_fields[1].multiline = True
    logo_status = ft.Text("Kein Logo", italic=True, color="grey")

    def on_file_result(e: ft.FilePickerResultEvent):
        if e.files:
            fname = e.files[0].name
            if not os.path.exists("assets"): os.makedirs("assets")
            shutil.copy(e.files[0].path, f"assets/{fname}")
            if file_picker_mode.value == "logo":
                temp_img["logo"] = fname
                logo_status.value = f"Logo: {fname}"
            else:
                temp_img["prod"] = fname
                p_status.value = f"Bild: {fname}"
            page.update()

    picker = ft.FilePicker(on_result=on_file_result); page.overlay.append(picker)
    date_picker = ft.DatePicker(on_change=lambda _: (setattr(selected_date, "value", date_picker.value.strftime("%d.%m.%Y")), page.update()))
    page.overlay.append(date_picker)

    def load_all():
        product_grid.controls.clear(); p_list.controls.clear(); stock_product_dropdown.options.clear(); stock_history_table.rows.clear()
        for p in db.get_products():
            stock = db.get_stock(p[0])
            img = f"assets/{p[3]}" if p[3] and os.path.exists(f"assets/{p[3]}") else None
            product_grid.controls.append(ft.Container(
                content=ft.Column([
                    ft.Image(src=img, width=50, height=50) if img else ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED),
                    ft.Text(p[1], size=12, weight="bold"), ft.Text(f"Lager: {stock}", size=10)
                ], horizontal_alignment="center"),
                on_click=lambda e, pid=p[0], n=p[1], pr=p[2]: add_to_cart(pid, n, pr), bgcolor="#333333", padding=10, border_radius=10
            ))
            stock_product_dropdown.options.append(ft.dropdown.Option(key=str(p[0]), text=p[1]))
            p_list.controls.append(ft.ListTile(title=ft.Text(p[1]), trailing=ft.IconButton(ft.Icons.DELETE, on_click=lambda e, pid=p[0]: (db.delete_product(pid), load_all()))))
        for h in db.get_all_stock_history():
            stock_history_table.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(h[3])), ft.DataCell(ft.Text(h[0])), ft.DataCell(ft.Text(str(h[1]))), ft.DataCell(ft.Text(h[2] or "-"))]))
        s = db.get_settings()
        if s:
            for i, v in enumerate(s[1:7]): s_fields[i].value = str(v) if v else ""
            temp_img["logo"] = s[7] or ""
        page.update()

    def add_to_cart(pid, name, price):
        if db.get_stock(pid) <= 0:
            show_msg(f"Lager leer: {name}", "red")
            return
        cart.append({"id": pid, "name": name, "price": price})
        cart_list.controls.clear()
        for i in cart: cart_list.controls.append(ft.ListTile(title=ft.Text(i['name']), trailing=ft.Text(f"{i['price']:.2f}€")))
        total_text.value = f"Summe: {sum(i['price'] for i in cart):.2f}€"
        page.update()

    # --- Layouts (Radikale Linksausrichtung) ---
    kasse_view = ft.Row([
        ft.Container(product_grid, expand=3),
        ft.Container(ft.Column([ft.Text("Warenkorb", size=20, weight="bold"), cart_list, total_text, ft.FilledButton("Bezahlen", on_click=lambda _: (generate_receipt(), [db.add_stock(i['id'], -1, "Verkauf", datetime.now().strftime("%d.%m.%Y")) for i in cart], cart.clear(), load_all(), show_msg("Erfolg")))], expand=True), expand=1, bgcolor="#2c2c2c", padding=20)
    ], expand=True)

    # Admin Inhalt
    artikel_view = ft.Column([
        ft.Text("Artikelverwaltung", size=20, weight="bold"), p_name, p_price,
        ft.ElevatedButton("Bild", icon=ft.Icons.IMAGE, on_click=lambda _: (setattr(file_picker_mode, "value", "prod"), picker.pick_files())),
        p_status, ft.FilledButton("Speichern", on_click=lambda _: (db.add_product(p_name.value, float(p_price.value.replace(",", ".")), temp_img["prod"]), load_all(), show_msg("Gespeichert"))),
        ft.Divider(), ft.Text("Löschen"), p_list
    ], scroll=ft.ScrollMode.AUTO, expand=True, visible=True)

    stock_view = ft.Column([
        ft.Text("Wareneingang", size=20, weight="bold"),
        ft.Row([stock_product_dropdown, stock_qty]),
        ft.Row([ft.ElevatedButton("Datum", on_click=lambda _: date_picker.pick_date()), selected_date]),
        ft.Text("Seriennummern:"),
        sn_container,
        ft.FilledButton("Buchen", on_click=lambda _: (db.add_stock(int(stock_product_dropdown.value), int(stock_qty.value), ", ".join([f.value for f in sn_container.controls if f.value]), selected_date.value), load_all(), show_msg("Gebucht"))),
        ft.Divider(), ft.Text("Historie"), stock_history_table
    ], scroll=ft.ScrollMode.AUTO, expand=True, visible=False)

    mandant_view = ft.Column([
        ft.Text("Mandant", size=20, weight="bold"),
        *s_fields,
        ft.ElevatedButton("Logo", on_click=lambda _: (setattr(file_picker_mode, "value", "logo"), picker.pick_files())),
        logo_status, ft.FilledButton("Speichern", on_click=lambda _: (db.save_settings([f.value for f in s_fields] + [temp_img["logo"]]), show_msg("Gespeichert")))
    ], scroll=ft.ScrollMode.AUTO, expand=True, visible=False)

    admin_view = ft.Row([
        ft.NavigationRail(selected_index=0, label_type="all", destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.INVENTORY, label="Artikel"),
            ft.NavigationRailDestination(icon=ft.Icons.PRECISION_MANUFACTURING, label="Lager"),
            ft.NavigationRailDestination(icon=ft.Icons.BUSINESS, label="Mandant")
        ], on_change=lambda e: (
            setattr(artikel_view, "visible", e.control.selected_index == 0),
            setattr(stock_view, "visible", e.control.selected_index == 1),
            setattr(mandant_view, "visible", e.control.selected_index == 2),
            page.update()
        )),
        ft.VerticalDivider(width=1),
        artikel_view, stock_view, mandant_view
    ], expand=True, visible=False)

    page.add(
        ft.Tabs(on_change=lambda e: (setattr(kasse_view, "visible", e.control.selected_index == 0), setattr(admin_view, "visible", e.control.selected_index == 1), page.update()), 
                tabs=[ft.Tab(text="Kasse", icon=ft.Icons.SHOPPING_CART), ft.Tab(text="Admin", icon=ft.Icons.SETTINGS)]),
        kasse_view, admin_view
    )
    load_all()

ft.app(target=main, assets_dir="assets")