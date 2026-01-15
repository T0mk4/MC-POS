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
        cursor.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL, image_path TEXT, has_serials INTEGER DEFAULT 1, article_number TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, shop_name TEXT, street TEXT, zip_city TEXT, email TEXT, web TEXT, tax_id TEXT, tax_rate REAL, logo_path TEXT, theme_mode TEXT DEFAULT 'system')")
        cursor.execute("CREATE TABLE IF NOT EXISTS stock_entries (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, quantity INTEGER, serials TEXT, entry_date TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS payment_methods (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY AUTOINCREMENT, sale_date TEXT, total_amount REAL, payment_method TEXT, items_text TEXT, tax_amount REAL)")
        try: cursor.execute("ALTER TABLE products ADD COLUMN article_number TEXT")
        except: pass
        try: cursor.execute("ALTER TABLE settings ADD COLUMN street TEXT")
        except: pass
        try: cursor.execute("ALTER TABLE settings ADD COLUMN zip_city TEXT")
        except: pass
        cursor.execute("INSERT OR IGNORE INTO settings (id, shop_name, tax_rate, theme_mode) VALUES (1, 'Mein Shop', 19.0, 'system')")
        self.conn.commit()

    def get_settings(self):
        return self.conn.execute("SELECT shop_name, street, zip_city, email, web, tax_id, tax_rate, logo_path, theme_mode FROM settings WHERE id=1").fetchone()

    def update_settings(self, fields):
        self.conn.execute("UPDATE settings SET shop_name=?, street=?, zip_city=?, email=?, web=?, tax_id=?, tax_rate=? WHERE id=1", fields)
        self.conn.commit()

    def update_logo(self, path):
        self.conn.execute("UPDATE settings SET logo_path=? WHERE id=1", (path,))
        self.conn.commit()

    def get_products(self): return self.conn.execute("SELECT * FROM products").fetchall()
    def get_stock(self, pid): return self.conn.execute("SELECT SUM(quantity) FROM stock_entries WHERE product_id = ?", (pid,)).fetchone()[0] or 0
    def get_payments(self): return self.conn.execute("SELECT * FROM payment_methods").fetchall()
    def get_stock_history(self, q=None):
        if q: return self.conn.execute("SELECT p.name, s.quantity, s.serials, s.entry_date FROM stock_entries s JOIN products p ON s.product_id = p.id WHERE s.serials LIKE ? OR p.name LIKE ? OR s.entry_date LIKE ? ORDER BY s.id DESC", (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
        return self.conn.execute("SELECT p.name, s.quantity, s.serials, s.entry_date FROM stock_entries s JOIN products p ON s.product_id = p.id ORDER BY s.id DESC").fetchall()
    def add_sale(self, total, method, items, tax):
        self.conn.execute("INSERT INTO sales (sale_date, total_amount, payment_method, items_text, tax_amount) VALUES (?,?,?,?,?)", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), total, method, items, tax))
        self.conn.commit()
    def add_stock(self, pid, qty, sn, date):
        self.conn.execute("INSERT INTO stock_entries (product_id, quantity, serials, entry_date) VALUES (?,?,?,?)", (pid, qty, sn, date))
        self.conn.commit()

def main(page: ft.Page):
    db = Database()
    settings_data = db.get_settings()
    if settings_data and settings_data[8]:
        if settings_data[8] == "hell": page.theme_mode = ft.ThemeMode.LIGHT
        elif settings_data[8] == "dunkel": page.theme_mode = ft.ThemeMode.DARK
        else: page.theme_mode = ft.ThemeMode.SYSTEM

    page.title = "MC POS - Alpha 0.3.0.1"
    page.window.width, page.window.height = 1280, 850
    page.window.resizable = False
    cart, temp_img = [], {"prod": "", "logo": ""}
    file_picker_mode = ft.Text("")

    product_grid = ft.GridView(expand=True, runs_count=4, max_extent=210, spacing=15)
    cart_list = ft.ListView(expand=True)
    total_sum_label = ft.Text("0.00 EUR", size=32, weight="bold", color="white")
    cart_title = ft.Text("Warenkorb", size=22, weight="bold")
    p_admin_list = ft.ListView(expand=True, spacing=5)
    pm_list = ft.ListView(expand=True)
    stock_history_table = ft.DataTable(columns=[ft.DataColumn(ft.Text("Datum")), ft.DataColumn(ft.Text("Produkt")), ft.DataColumn(ft.Text("Menge")), ft.DataColumn(ft.Text("SN"))])
    current_stock_info = ft.Text("", size=16, weight="bold", color="#448AFF")
    sn_container = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)

    def show_msg(text, color="green"):
        sb = ft.SnackBar(content=ft.Text(text, color="white"), bgcolor=color); page.overlay.append(sb); sb.open = True; page.update()

    def pdf_safe(text):
        if not text: return ""
        return str(text).encode('latin-1', 'replace').decode('latin-1')

    def generate_receipt(payment_info, tax_amount):
        s = db.get_settings(); total = sum(i['price'] for i in cart)
        pdf = FPDF()
        pdf.add_page()
        if s[7] and os.path.exists(f"assets/{s[7]}"):
            pdf.image(f"assets/{s[7]}", x=10, y=10, w=25)
        pdf.set_font("helvetica", "B", 11)
        addr_y = 10
        for i, val in enumerate(s[:6]):
            if val:
                pdf.set_xy(105, addr_y)
                txt = pdf_safe(str(val)) if i != 5 else pdf_safe(f"St-Nr: {val}")
                pdf.cell(95, 5, txt, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_font("helvetica", "", 9)
                addr_y += 5
        pdf.set_xy(10, 45); pdf.set_font("helvetica", "B", 14); pdf.cell(0, 10, "KASSENBELEG", align="C", ln=True)
        pdf.ln(5); pdf.set_font("helvetica", "B", 10); pdf.cell(140, 8, " Artikel", border="TB"); pdf.cell(50, 8, "Preis", border="TB", align="R", ln=True)
        pdf.set_font("helvetica", "", 10)
        for item in cart: 
            pdf.cell(140, 7, f" {pdf_safe(item['name'])}", border="B")
            pdf.cell(50, 7, f"{item['price']:.2f} EUR ", border="B", align="R", ln=True)
        pdf.ln(5); pdf.set_font("helvetica", "B", 12); pdf.cell(140, 10, " GESAMTSUMME"); pdf.cell(50, 10, f"{total:.2f} EUR", align="R", ln=True)
        pdf.set_font("helvetica", "I", 9); pdf.cell(0, 8, pdf_safe(f"Gesamtpreis inkl. {tax_amount:.2f} EUR MwSt."), align="R", ln=True)
        pdf.ln(5); pdf.set_font("helvetica", "", 9); pdf.cell(0, 5, f"Zahlart: {pdf_safe(payment_info)}", ln=True)
        pdf.cell(0, 5, f"Datum: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}", ln=True)
        fname = f"Beleg_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"; pdf.output(fname); webbrowser.open(fname)

    def load_all():
        is_dark = page.theme_mode == ft.ThemeMode.DARK or (page.theme_mode == ft.ThemeMode.SYSTEM and page.platform_brightness == ft.Brightness.DARK)
        card_bg, text_color = ("#2a2a2a", "#ffffff") if is_dark else ("#ffffff", "#000000")
        cart_container.bgcolor = card_bg; cart_container.border = ft.border.all(2, "#444444"); cart_title.color = text_color
        product_grid.controls.clear(); pm_list.controls.clear(); p_admin_list.controls.clear()
        prods = db.get_products(); stock_product_dropdown.options = [ft.dropdown.Option(key=str(x[0]), text=x[1]) for x in prods]
        for p in prods:
            stock = db.get_stock(p[0])
            img_c = ft.Image(src=f"assets/{p[3]}", fit=ft.ImageFit.CONTAIN) if p[3] and os.path.exists(f"assets/{p[3]}") else ft.Icon(ft.Icons.IMAGE, size=70, color="#888888")
            product_grid.controls.append(ft.Container(content=ft.Column([ft.Container(content=img_c, width=100, height=100, alignment=ft.alignment.center), ft.Text(p[1], weight="bold", size=13, text_align="center", color=text_color), ft.Text(f"{p[2]:.2f} EUR", size=12, weight="w900", color="#448AFF"), ft.Text(f"Lager: {stock}", size=11, weight="bold", color="#D84315" if stock <= 0 else "#2E7D32")], horizontal_alignment="center", spacing=3), on_click=lambda e, pid=p[0], n=p[1], pr=p[2]: add_to_cart(pid, n, pr), bgcolor=card_bg, padding=12, border_radius=15, width=200, border=ft.border.all(2, "#444444")))
            p_admin_list.controls.append(ft.ListTile(title=ft.Text(f"{p[1]}", color=text_color), subtitle=ft.Text(f"Art: {p[5]}", color="#448AFF"), trailing=ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="#ef5350", on_click=lambda e, pid=p[0]: (db.conn.execute("DELETE FROM products WHERE id=?", (pid,)), db.conn.commit(), load_all()))))
        for m in db.get_payments(): pm_list.controls.append(ft.ListTile(title=ft.Text(m[1], color=text_color), trailing=ft.IconButton(ft.Icons.DELETE, on_click=lambda e, mid=m[0]: (db.conn.execute("DELETE FROM payment_methods WHERE id=?", (mid,)), db.conn.commit(), load_all()))))
        update_stock_history(); s = db.get_settings()
        if s: 
            for i in range(7): s_fields[i].value = str(s[i])
            theme_dropdown.value = s[8]
        page.update()

    def on_file_result(e: ft.FilePickerResultEvent):
        if e.files:
            if not os.path.exists("assets"): os.makedirs("assets")
            fname = e.files[0].name
            shutil.copy(e.files[0].path, f"assets/{fname}")
            if file_picker_mode.value == "logo": db.update_logo(fname)
            else: temp_img["prod"] = fname
            load_all()

    picker = ft.FilePicker(on_result=on_file_result); page.overlay.append(picker)

    def handle_payment_change(e):
        is_cash = pay_method_dropdown.value == "Bar"
        pay_given.visible = is_cash
        pay_change_text.visible = is_cash
        page.update()

    def update_change():
        try:
            total = sum(i['price'] for i in cart)
            given = float(pay_given.value.replace(",", "."))
            pay_change_text.value = f"Wechselgeld: {max(0, given - total):.2f} EUR"
        except: pay_change_text.value = "Wechselgeld: 0.00 EUR"
        page.update()

    def finalize_payment():
        s = db.get_settings(); total = sum(i['price'] for i in cart)
        tax_str = str(s[6]).replace(",", ".").replace("%", "").strip()
        try: tax_rate = float(tax_str) if tax_str else 19.0
        except: tax_rate = 19.0
        tax_amount = total * (tax_rate / (100 + tax_rate))
        generate_receipt(pay_method_dropdown.value, tax_amount)
        for i in cart: db.add_stock(i['id'], -1, "Verkauf", datetime.now().strftime("%d.%m.%Y"))
        db.add_sale(total, pay_method_dropdown.value, ", ".join([i['name'] for i in cart]), tax_amount)
        cart.clear(); pay_given.value = ""; pay_change_text.value = "Wechselgeld: 0.00 EUR"; pay_dialog.open = False
        load_all(); page.update()

    pay_method_dropdown = ft.Dropdown(label="Zahlart", width=300, on_change=handle_payment_change)
    pay_given = ft.TextField(label="Gegeben", width=300, on_change=lambda _: update_change(), visible=False)
    pay_change_text = ft.Text("Wechselgeld: 0.00 EUR", size=20, weight="bold", color="#448AFF", visible=False)
    pay_dialog = ft.AlertDialog(title=ft.Text("Zahlung"), content=ft.Column([pay_method_dropdown, pay_given, pay_change_text], tight=True), actions=[ft.ElevatedButton("Abschluss", on_click=lambda _: finalize_payment())])
    page.overlay.append(pay_dialog)

    def update_stock_history(query=None):
        stock_history_table.rows.clear()
        for h in db.get_stock_history(query): stock_history_table.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(h[3])), ft.DataCell(ft.Text(h[0])), ft.DataCell(ft.Text(str(h[1]))), ft.DataCell(ft.Text(h[2] or "-"))]))
        page.update()

    def update_sn_fields():
        sn_container.controls.clear()
        if not stock_product_dropdown.value: current_stock_info.value = ""; return
        p = next((x for x in db.get_products() if str(x[0]) == stock_product_dropdown.value), None)
        if p:
            stock = db.get_stock(p[0]); current_stock_info.value = f"Art-Nr: {p[5] if p[5] else 'N/A'} | Bestand: {stock}"
            if p[4] == 1:
                try: 
                    for i in range(int(stock_qty.value)): sn_container.controls.append(ft.TextField(label=f"SN {i+1}", width=300, dense=True))
                except: pass
        page.update()

    def add_to_cart(pid, name, price):
        if db.get_stock(pid) <= 0: return show_msg("Lager leer!", "red")
        cart.append({"id": pid, "name": name, "price": price}); cart_list.controls.clear()
        is_dark = page.theme_mode == ft.ThemeMode.DARK or (page.theme_mode == ft.ThemeMode.SYSTEM and page.platform_brightness == ft.Brightness.DARK)
        t_color = "#ffffff" if is_dark else "#000000"
        for i in cart: cart_list.controls.append(ft.ListTile(title=ft.Text(i['name'], color=t_color), trailing=ft.Text(f"{i['price']:.2f} EUR", color=t_color)))
        total_sum_label.value = f"{sum(i['price'] for i in cart):.2f} EUR"; page.update()

    def update_theme_ui():
        if theme_dropdown.value == "hell": page.theme_mode = ft.ThemeMode.LIGHT
        elif theme_dropdown.value == "dunkel": page.theme_mode = ft.ThemeMode.DARK
        else: page.theme_mode = ft.ThemeMode.SYSTEM
        db.conn.execute("UPDATE settings SET theme_mode=? WHERE id=1", (theme_dropdown.value,))
        db.conn.commit()
        load_all()

    p_name, p_price, p_art_num = ft.TextField(label="Produktname", width=350), ft.TextField(label="Preis", width=350), ft.TextField(label="Artikelnummer", width=350)
    p_serials_check = ft.Checkbox(label="Seriennummern-Pflicht", value=True)
    stock_product_dropdown = ft.Dropdown(label="Produkt wählen", width=350, on_change=lambda _: update_sn_fields())
    stock_qty = ft.TextField(label="Menge", value="1", width=100, on_change=lambda _: update_sn_fields())
    s_fields = [ft.TextField(label=l, width=400) for l in ["Shop Name", "Straße & Hausnummer", "PLZ & Ort", "Email", "Web", "St-Nr", "MwSt %"]]
    pm_name = ft.TextField(label="Zahlart Name", width=350)
    theme_dropdown = ft.Dropdown(label="Theme", width=350, options=[ft.dropdown.Option("system"), ft.dropdown.Option("hell"), ft.dropdown.Option("dunkel")])
    stock_search = ft.TextField(label="Suche...", prefix_icon=ft.Icons.SEARCH, width=300, on_change=lambda e: update_stock_history(e.control.value))

    def get_admin_content(index):
        if index == 0: return ft.Column([ft.Text("Artikelverwaltung", size=24, weight="bold"), p_name, p_price, p_art_num, p_serials_check, ft.Row([ft.ElevatedButton("Bild", icon=ft.Icons.IMAGE, on_click=lambda _: (setattr(file_picker_mode, "value", "prod"), picker.pick_files())), ft.FilledButton("Speichern", on_click=lambda _: (db.conn.execute("INSERT INTO products (name, price, image_path, has_serials, article_number) VALUES (?,?,?,?,?)", (p_name.value, float(p_price.value.replace(",", ".")), temp_img["prod"], 1 if p_serials_check.value else 0, p_art_num.value)), db.conn.commit(), load_all(), show_msg("Gespeichert")))]), ft.Divider(), ft.Container(p_admin_list, height=250, border=ft.border.all(1, "#444444"), border_radius=10)], scroll=ft.ScrollMode.AUTO, spacing=10)
        elif index == 1: return ft.Column([ft.Text("Lagerverwaltung", size=24, weight="bold"), ft.Text("Hier können Sie neue Bestände einbuchen. Wählen Sie das Produkt und geben Sie die Menge an.", color="#888888"), ft.Row([ft.Column([stock_product_dropdown, current_stock_info, stock_qty, ft.FilledButton("Einbuchen", on_click=lambda _: (db.add_stock(int(stock_product_dropdown.value), int(stock_qty.value), ", ".join([f.value for f in sn_container.controls if hasattr(f, 'value')]), datetime.now().strftime("%d.%m.%Y")), load_all(), show_msg("Gebucht")))], width=350), ft.Container(sn_container, width=380, height=200, border=ft.border.all(1, "#444444"), padding=10, border_radius=10)]), ft.Divider(), ft.Row([ft.Text("Historie", size=18, weight="bold"), ft.Row([stock_search, ft.IconButton(ft.Icons.CLEAR, on_click=lambda _: (setattr(stock_search, "value", ""), update_stock_history()))])], alignment="spaceBetween"), ft.Container(ft.Column([stock_history_table], scroll="always"), expand=True, border=ft.border.all(1, "#444444"), border_radius=10)], expand=True, spacing=10)
        elif index == 2: return ft.Column([ft.Text("Zahlarten", size=24, weight="bold"), pm_name, ft.FilledButton("Hinzufügen", on_click=lambda _: (db.conn.execute("INSERT INTO payment_methods (name) VALUES (?)", (pm_name.value,)), db.conn.commit(), load_all())), ft.Divider(), ft.Container(pm_list, height=300, border=ft.border.all(1, "#444444"), border_radius=10)], spacing=10)
        elif index == 3: s = db.get_settings(); lp = f"assets/{s[7]}" if s and s[7] else ""; logo_prev = ft.Image(src=lp, height=100) if lp and os.path.exists(lp) else ft.Icon(ft.Icons.IMAGE, size=50); return ft.Column([ft.Text("Mandantendaten", size=24, weight="bold"), logo_prev, ft.ElevatedButton("Logo", icon=ft.Icons.IMAGE, on_click=lambda _: (setattr(file_picker_mode, "value", "logo"), picker.pick_files())), *s_fields, ft.FilledButton("Speichern", on_click=lambda _: (db.update_settings([f.value for f in s_fields]), show_msg("Mandant gespeichert"), load_all()))], scroll=ft.ScrollMode.AUTO, spacing=10)
        elif index == 4: return ft.Column([ft.Text("Einstellungen", size=24, weight="bold"), theme_dropdown, ft.FilledButton("Speichern", on_click=lambda _: update_theme_ui())], spacing=10)

    total_container = ft.Container(content=ft.Column([ft.Text("GESAMTSUMME", size=10, color="#AAAAAA"), total_sum_label], spacing=0), bgcolor="#000000", padding=15, border_radius=10, alignment=ft.alignment.center)
    cart_container = ft.Container(content=ft.Column([cart_title, cart_list, ft.Divider(), total_container, ft.FilledButton("Bezahlen", width=float("inf"), height=50, bgcolor="#2e7d32", color="white", on_click=lambda _: (setattr(pay_method_dropdown, "options", [ft.dropdown.Option(m[1]) for m in db.get_payments()]), setattr(pay_method_dropdown, "value", db.get_payments()[0][1] if db.get_payments() else None), handle_payment_change(None), setattr(pay_dialog, "open", True), page.update()))], expand=True), expand=1, padding=20, border_radius=20, margin=10)
    kasse_view = ft.Row([ft.Container(product_grid, expand=3, padding=10), cart_container], expand=True)
    admin_container = ft.Container(expand=True, padding=ft.padding.only(top=0, left=20, right=20, bottom=20))
    admin_view = ft.Row([ft.NavigationRail(selected_index=0, destinations=[ft.NavigationRailDestination(icon=ft.Icons.INVENTORY, label="Artikel"), ft.NavigationRailDestination(icon=ft.Icons.STORAGE, label="Lager"), ft.NavigationRailDestination(icon=ft.Icons.PAYMENT, label="Zahlarten"), ft.NavigationRailDestination(icon=ft.Icons.BUSINESS, label="Mandant"), ft.NavigationRailDestination(icon=ft.Icons.SETTINGS, label="Einstellungen")], on_change=lambda e: (setattr(admin_container, "content", get_admin_content(e.control.selected_index)), page.update())), ft.VerticalDivider(width=1), admin_container], expand=True, visible=False, vertical_alignment=ft.CrossAxisAlignment.START)
    exit_btn = ft.TextButton(content=ft.Row([ft.Text("App beenden", color="#ef5350", weight="bold"), ft.Icon(ft.Icons.POWER_SETTINGS_NEW, color="#ef5350")], spacing=5), on_click=lambda _: page.window.close())
    page.add(ft.Row([ft.Tabs(expand=True, on_change=lambda e: (setattr(kasse_view, "visible", e.control.selected_index == 0), setattr(admin_view, "visible", e.control.selected_index == 1), page.update()), tabs=[ft.Tab(text="Kasse", icon=ft.Icons.SHOPPING_CART), ft.Tab(text="Admin", icon=ft.Icons.SETTINGS)]), exit_btn], alignment="spaceBetween"), kasse_view, admin_view)
    admin_container.content = get_admin_content(0); load_all()

ft.app(target=main, assets_dir="assets")