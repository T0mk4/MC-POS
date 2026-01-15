import flet as ft
import sqlite3
import shutil
import os
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
    page.title = "MC POS & Stock Management"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#1e1e1e"
    
    db = Database()
    cart = []
    temp_img = {"prod": "", "logo": ""}
    file_picker_mode = ft.Text("")

    # --- UI Komponenten Lager ---
    stock_product_dropdown = ft.Dropdown(label="Produkt wählen", width=400)
    stock_qty = ft.TextField(label="Menge", value="1", width=100)
    stock_serials = ft.TextField(label="Seriennummern", multiline=True, width=400)
    selected_date = ft.Text(datetime.now().strftime("%d.%m.%Y"))

    def change_date(e):
        selected_date.value = date_picker.value.strftime("%d.%m.%Y")
        page.update()

    date_picker = ft.DatePicker(
        on_change=change_date,
        first_date=datetime(2023, 1, 1),
        last_date=datetime(2030, 12, 31),
    )
    page.overlay.append(date_picker)

    stock_history_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Datum")),
            ft.DataColumn(ft.Text("Produkt")),
            ft.DataColumn(ft.Text("Menge")),
            ft.DataColumn(ft.Text("Seriennummern")),
        ],
        rows=[]
    )

    # --- UI Komponenten Kasse & Rest ---
    product_grid = ft.GridView(expand=True, runs_count=4, max_extent=200, spacing=10)
    cart_list = ft.ListView(expand=True, spacing=5)
    total_text = ft.Text("Summe: 0.00€", size=25, weight="bold", color="white")
    p_name, p_price = ft.TextField(label="Produktname", width=400), ft.TextField(label="Preis", width=400)
    p_list = ft.ListView(expand=True, spacing=5)
    s_name, s_addr, s_mail, s_web, s_taxid, s_taxrate = ft.TextField(label="Shop Name", width=400), ft.TextField(label="Anschrift", multiline=True, width=400), ft.TextField(label="Email", width=400), ft.TextField(label="Web", width=400), ft.TextField(label="St.-Nr", width=400), ft.TextField(label="MwSt %", width=400)

    def load_all():
        product_grid.controls.clear()
        p_list.controls.clear()
        stock_product_dropdown.options.clear()
        stock_history_table.rows.clear()
        
        # Produkte & Kasse
        for p in db.get_products():
            stock = db.get_stock(p[0])
            product_grid.controls.append(ft.Container(
                content=ft.Column([
                    ft.Image(src=p[3], width=60, height=60) if p[3] else ft.Icon(ft.Icons.FASTFOOD),
                    ft.Text(p[1], weight="bold"), ft.Text(f"Bestand: {stock}", size=10, color="grey")
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                on_click=lambda e, pid=p[0], n=p[1], pr=p[2]: add_to_cart(pid, n, pr),
                bgcolor="#333333", border_radius=10, padding=10
            ))
            stock_product_dropdown.options.append(ft.dropdown.Option(key=str(p[0]), text=p[1]))
            p_list.controls.append(ft.ListTile(title=ft.Text(p[1]), trailing=ft.IconButton(ft.Icons.DELETE, on_click=lambda e, pid=p[0]: (db.delete_product(pid), load_all()))))

        # Lagerhistorie
        for h in db.get_all_stock_history():
            stock_history_table.rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(h[3])), ft.DataCell(ft.Text(h[0])),
                ft.DataCell(ft.Text(str(h[1]))), ft.DataCell(ft.Text(h[2] if h[2] else "-")),
            ]))
        page.update()

    def add_to_cart(pid, name, price):
        cart.append({"id": pid, "name": name, "price": price})
        cart_list.controls.clear()
        for i in cart: cart_list.controls.append(ft.ListTile(title=ft.Text(i['name']), trailing=ft.Text(f"{i['price']:.2f}€")))
        total_text.value = f"Summe: {sum(i['price'] for i in cart):.2f}€"
        page.update()

    # --- Layouts ---
    kasse_view = ft.Row([
        ft.Container(product_grid, expand=3, padding=10),
        ft.Container(ft.Column([ft.Text("Warenkorb", size=22), cart_list, total_text, ft.FilledButton("Bezahlen", on_click=lambda _: (cart.clear(), load_all()))], expand=True), expand=1, bgcolor="#2c2c2c", padding=20)
    ], expand=True)

    artikel_content = ft.Container(ft.Column([ft.Text("Artikelverwaltung", size=20, weight="bold"), p_name, p_price, ft.FilledButton("Speichern", on_click=lambda _: (db.add_product(p_name.value, float(p_price.value), ""), load_all()))], horizontal_alignment=ft.CrossAxisAlignment.START), padding=20)

    stock_content = ft.Container(ft.Column([
        ft.Text("Wareneingang buchen", size=20, weight="bold"),
        ft.Row([stock_product_dropdown, stock_qty], spacing=10),
        ft.Row([ft.ElevatedButton("Datum wählen", icon=ft.Icons.CALENDAR_MONTH, on_click=lambda _: date_picker.pick_date()), selected_date], spacing=20),
        stock_serials,
        ft.FilledButton("Eingang buchen", icon=ft.Icons.ADD_BUSINESS, on_click=lambda _: (db.add_stock(int(stock_product_dropdown.value), int(stock_qty.value), stock_serials.value, selected_date.value), load_all())),
        ft.Divider(),
        ft.Text("Aktuelle Bestände / Historie", size=20, weight="bold"),
        ft.Column([stock_history_table], scroll=ft.ScrollMode.ALWAYS, expand=True)
    ], horizontal_alignment=ft.CrossAxisAlignment.START, spacing=15), padding=20, visible=False, expand=True)

    mandant_content = ft.Container(ft.Column([ft.Text("Mandant", size=20, weight="bold"), s_name, s_addr, s_mail, s_web, s_taxid, s_taxrate, ft.FilledButton("Speichern", on_click=lambda _: db.save_settings((s_name.value, s_addr.value, s_mail.value, s_web.value, s_taxid.value, float(s_taxrate.value), "")))], horizontal_alignment=ft.CrossAxisAlignment.START, spacing=15), padding=20, visible=False)

    admin_view = ft.Row([
        ft.NavigationRail(selected_index=0, destinations=[ft.NavigationRailDestination(icon=ft.Icons.INVENTORY_2, label="Artikel"), ft.NavigationRailDestination(icon=ft.Icons.ADD_SHOPPING_CART, label="Lager"), ft.NavigationRailDestination(icon=ft.Icons.BUSINESS, label="Mandant")],
            on_change=lambda e: (setattr(artikel_content, "visible", e.control.selected_index == 0), setattr(stock_content, "visible", e.control.selected_index == 1), setattr(mandant_content, "visible", e.control.selected_index == 2), page.update())),
        ft.VerticalDivider(width=1), artikel_content, stock_content, mandant_content
    ], expand=True, visible=False)

    page.add(ft.Tabs(on_change=lambda e: (setattr(kasse_view, "visible", e.control.selected_index == 0), setattr(admin_view, "visible", e.control.selected_index == 1), page.update()), tabs=[ft.Tab(text="Kasse", icon=ft.Icons.SHOPPING_CART), ft.Tab(text="Admin", icon=ft.Icons.SETTINGS)]), kasse_view, admin_view)
    load_all()

ft.app(target=main, assets_dir="assets")