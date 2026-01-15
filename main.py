import flet as ft
import sqlite3

class Database:
    def __init__(self):
        self.conn = sqlite3.connect("pos_data.db", check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                color TEXT DEFAULT 'blue'
            )
        """)
        cursor.execute("SELECT count(*) FROM products")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO products (name, price, color) VALUES (?, ?, ?)", ("Kaffee", 2.50, "brown"))
            cursor.execute("INSERT INTO products (name, price, color) VALUES (?, ?, ?)", ("Kuchen", 4.00, "orange"))
            cursor.execute("INSERT INTO products (name, price, color) VALUES (?, ?, ?)", ("Cola", 3.00, "red"))
            self.conn.commit()

    def get_products(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM products")
        return cursor.fetchall()

def main(page: ft.Page):
    page.title = "MC POS"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 10
    
    db = Database()
    cart = []
    
    cart_list = ft.ListView(expand=True, spacing=10)
    total_text = ft.Text("Summe: 0.00€", size=20, weight=ft.FontWeight.BOLD)
    
    def update_cart_ui():
        cart_list.controls.clear()
        total = 0
        for item in cart:
            cart_list.controls.append(
                ft.ListTile(
                    title=ft.Text(item['name']),
                    trailing=ft.Text(f"{item['price']:.2f}€")
                )
            )
            total += item['price']
        total_text.value = f"Summe: {total:.2f}€"
        page.update()

    def add_to_cart(e):
        product = e.control.data
        cart.append(product)
        update_cart_ui()

    def checkout(e):
        if not cart:
            page.snack_bar = ft.SnackBar(ft.Text("Warenkorb leer!"))
            page.snack_bar.open = True
            page.update()
            return

        def close_dialog(e):
            checkout_dialog.open = False
            page.update()

        def confirm_pay(e):
            cart.clear()
            update_cart_ui()
            checkout_dialog.open = False
            page.snack_bar = ft.SnackBar(ft.Text("Zahlung erfolgreich!"))
            page.snack_bar.open = True
            page.update()

        checkout_dialog = ft.AlertDialog(
            title=ft.Text("Bezahlen"),
            content=ft.Text(f"Betrag fällig: {total_text.value}"),
            actions=[
                ft.TextButton("Bar", on_click=confirm_pay),
                ft.TextButton("Karte", on_click=confirm_pay),
                ft.TextButton("Abbrechen", on_click=close_dialog),
            ],
        )
        page.dialog = checkout_dialog
        checkout_dialog.open = True
        page.update()

    products = db.get_products()
    product_grid = ft.GridView(
        expand=True,
        runs_count=5,
        max_extent=150,
        child_aspect_ratio=1.0,
        spacing=10,
        run_spacing=10,
    )

    for p in products:
        p_data = {"name": p[1], "price": p[2]}
        container = ft.Container(
            content=ft.Column([
                ft.Icon("shopping_cart", size=40, color="white"),
                ft.Text(p[1], size=16, weight="bold", color="white"),
                ft.Text(f"{p[2]:.2f}€", color="white70")
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=p[3],
            border_radius=10,
            ink=True,
            on_click=add_to_cart,
            data=p_data
        )
        product_grid.controls.append(container)

    layout = ft.Row(
        [
            ft.Container(product_grid, expand=2),
            ft.VerticalDivider(width=1),
            ft.Container(
                ft.Column([
                    ft.Text("Warenkorb", size=20, weight="bold"),
                    cart_list,
                    ft.Divider(),
                    total_text,
                    ft.FilledButton("Bezahlen", on_click=checkout, height=50, width=float("inf"))
                ]),
                expand=1,
                padding=10,
                bgcolor="#E0E0E0",
                border_radius=10
            )
        ],
        expand=True
    )

    page.add(layout)

ft.app(target=main)