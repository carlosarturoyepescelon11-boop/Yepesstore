from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import time
from werkzeug.utils import secure_filename
from datetime import datetime
import psycopg2

app = Flask(__name__)
app.secret_key = "vapers_store_key_2024"

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

USUARIO_ADMIN = "admin"
CLAVE_ADMIN = "1234"


def conectar():
    import os

    DATABASE_URL = os.getenv("DATABASE_URL")

    if DATABASE_URL:
        import psycopg2
        return psycopg2.connect(DATABASE_URL)
    else:
        return sqlite3.connect("database.db", timeout=10)


def init_db():
    with conectar() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            categoria TEXT,
            precio_compra REAL,
            precio_venta REAL,
            precio_mayorista REAL,
            stock INTEGER,
            imagen TEXT
        )
        """)

        columnas = [col[1] for col in con.execute("PRAGMA table_info(productos)")]
        if "precio_mayorista" not in columnas:
            con.execute("ALTER TABLE productos ADD COLUMN precio_mayorista REAL")

        con.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            nombre TEXT,
            cantidad INTEGER,
            precio_compra REAL,
            precio_venta REAL,
            ganancia REAL,
            fecha TEXT
        )
        """)

        con.execute("""
        CREATE TABLE IF NOT EXISTS inversiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            monto REAL,
            descripcion TEXT,
            fecha TEXT
        )
        """)

        con.commit()


init_db()


def esta_logeado():
    return "usuario" in session


# --- LOGIN ---
@app.route("/", methods=["GET", "POST"])
def login():
    if esta_logeado():
        return redirect(url_for('ventas'))

    error = None
    if request.method == "POST":
        if request.form.get("usuario") == USUARIO_ADMIN and request.form.get("clave") == CLAVE_ADMIN:
            session["usuario"] = USUARIO_ADMIN
            return redirect(url_for('ventas'))
        error = "Usuario o clave incorrectos"

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))


# --- INVENTARIO ---
@app.route("/index")
def index():
    if not esta_logeado():
        return redirect(url_for('login'))

    with conectar() as con:
        productos = con.execute("""
            SELECT id, nombre, categoria, precio_compra, precio_venta, precio_mayorista, stock, imagen
            FROM productos
            ORDER BY id DESC
        """).fetchall()

    return render_template("index.html", productos=productos)


# --- VENTAS (INICIO) ---
@app.route("/ventas")
def ventas():
    if not esta_logeado():
        return redirect(url_for('login'))

    with conectar() as con:
        productos = con.execute("""
            SELECT id, nombre, categoria, precio_compra, precio_venta, precio_mayorista, stock, imagen
            FROM productos
            ORDER BY id DESC
        """).fetchall()

    return render_template("ventas.html", productos=productos)


# --- AGREGAR ---
@app.route("/agregar", methods=["GET", "POST"])
def agregar():
    if not esta_logeado():
        return redirect(url_for('login'))

    if request.method == "POST":
        nombre = request.form.get("nombre")
        categoria = request.form.get("categoria")
        p_compra = float(request.form.get("precio_compra") or 0)
        p_venta = float(request.form.get("precio_venta") or 0)
        p_mayorista = float(request.form.get("precio_mayorista") or 0)
        stock = int(request.form.get("stock") or 0)

        n_img = ""
        if 'imagen' in request.files:
            img = request.files['imagen']
            if img and img.filename != "":
                n_img = str(int(time.time())) + "_" + secure_filename(img.filename)
                img.save(os.path.join(app.config["UPLOAD_FOLDER"], n_img))

        con = conectar()

        con.execute("""
            INSERT INTO productos (nombre, categoria, precio_compra, precio_venta, precio_mayorista, stock, imagen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (nombre, categoria, p_compra, p_venta, p_mayorista, stock, n_img))

        # 🔥 INVERSIÓN AUTOMÁTICA
        if stock > 0 and p_compra > 0:
            inversion_total = p_compra * stock
            fecha = datetime.now().strftime("%Y-%m-%d")

            con.execute("""
                INSERT INTO inversiones (monto, descripcion, fecha)
                VALUES (?, ?, ?)
            """, (
                inversion_total,
                f"Compra inicial de {nombre} x{stock}",
                fecha
            ))

        con.commit()
        con.close()

        return redirect(url_for('index'))

    return render_template("agregar.html")


# --- EDITAR ---
@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    if not esta_logeado():
        return redirect(url_for('login'))

    con = conectar()
    producto = con.execute("SELECT * FROM productos WHERE id=?", (id,)).fetchone()

    if request.method == "POST":
        nombre = request.form.get("nombre")
        categoria = request.form.get("categoria")
        p_compra = float(request.form.get("precio_compra") or 0)
        p_venta = float(request.form.get("precio_venta") or 0)
        p_mayorista = float(request.form.get("precio_mayorista") or 0)
        stock = int(request.form.get("stock") or 0)

        n_img = producto[7]

        if 'imagen' in request.files:
            img = request.files['imagen']
            if img and img.filename != "":
                n_img = str(int(time.time())) + "_" + secure_filename(img.filename)
                img.save(os.path.join(app.config["UPLOAD_FOLDER"], n_img))

        con.execute("""
            UPDATE productos
            SET nombre=?, categoria=?, precio_compra=?, precio_venta=?, precio_mayorista=?, stock=?, imagen=?
            WHERE id=?
        """, (nombre, categoria, p_compra, p_venta, p_mayorista, stock, n_img, id))

        con.commit()
        con.close()

        return redirect(url_for('index'))

    con.close()
    return render_template("editar.html", producto=producto)


# --- ELIMINAR ---
@app.route("/eliminar/<int:id>")
def eliminar(id):
    if not esta_logeado():
        return redirect(url_for('login'))

    with conectar() as con:
        con.execute("DELETE FROM productos WHERE id=?", (id,))
        con.commit()

    return redirect(url_for('index'))


# --- VENTA ---
@app.route("/venta/<int:id>", methods=["POST"])
def venta(id):
    if not esta_logeado():
        return redirect(url_for('login'))

    con = conectar()
    con.row_factory = sqlite3.Row

    p = con.execute("SELECT * FROM productos WHERE id=?", (id,)).fetchone()

    # 🔥 VALIDAR CANTIDAD
    try:
        cantidad = int(request.form.get("cantidad") or 1)
        if cantidad <= 0:
            cantidad = 1
    except:
        cantidad = 1

    if p:
        stock_actual = int(p["stock"] or 0)

        if stock_actual >= cantidad:
            p_compra = float(p["precio_compra"] or 0)
            p_venta = float(p["precio_venta"] or 0)

            ganancia = (p_venta - p_compra) * cantidad
            fecha = datetime.now().strftime("%Y-%m-%d")

            # 🔥 ACTUALIZAR STOCK
            con.execute(
                "UPDATE productos SET stock = stock - ? WHERE id=?",
                (cantidad, id)
            )

            # 🔥 REGISTRAR VENTA
            con.execute("""
                INSERT INTO ventas (producto_id, nombre, cantidad, precio_compra, precio_venta, ganancia, fecha)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                id,
                p["nombre"],
                cantidad,
                p_compra,
                p_venta,
                ganancia,
                fecha
            ))

            con.commit()

            # 🔥 GUARDAR TICKET (SIN ROMPER NADA)
            session["ticket"] = {
                "nombre": p["nombre"],
                "cantidad": cantidad,
                "total": p_venta * cantidad,
                "ganancia": ganancia
            }

            # 🔥 MENSAJE PRO
            flash(f"✅ Vendido: {p['nombre']} x{cantidad}")

        else:
            flash("❌ No hay suficiente stock")

    else:
        flash("❌ Producto no encontrado")

    con.close()
    return redirect(url_for('ticket'))

# --- TICKET ---
@app.route("/ticket")
def ticket():
    if not esta_logeado():
        return redirect(url_for('login'))

    t = session.get("ticket")
    return render_template("ticket.html", t=t)

# --- DASHBOARD ---
@app.route("/dashboard")
def dashboard():
    if not esta_logeado():
        return redirect(url_for('login'))

    con = conectar()

    hoy_fecha = datetime.now().strftime("%Y-%m-%d")

    # 💰 GANANCIA TOTAL
    total = con.execute(
        "SELECT SUM(ganancia) FROM ventas"
    ).fetchone()[0] or 0

    # 💸 INVERSIÓN TOTAL
    inversion = con.execute(
        "SELECT SUM(monto) FROM inversiones"
    ).fetchone()[0] or 0

    # 💰 GANANCIA HOY
    hoy = con.execute(
        "SELECT SUM(ganancia) FROM ventas WHERE fecha=?",
        (hoy_fecha,)
    ).fetchone()[0] or 0

    # 💵 VENTAS HOY (NUEVO 🔥)
    ventas_hoy = con.execute(
        "SELECT SUM(precio_venta * cantidad) FROM ventas WHERE fecha=?",
        (hoy_fecha,)
    ).fetchone()[0] or 0

    # 📊 DATOS PARA GRÁFICA
    datos = con.execute("""
        SELECT fecha, SUM(ganancia)
        FROM ventas
        GROUP BY fecha
        ORDER BY fecha ASC
    """).fetchall()

    fechas = [d[0] for d in datos] if datos else []
    ganancias = [d[1] for d in datos] if datos else []

    # 🧾 ÚLTIMAS VENTAS
    ventas_list = con.execute("""
        SELECT * FROM ventas
        ORDER BY id DESC
        LIMIT 10
    """).fetchall()

    con.close()

    return render_template(
        "dashboard.html",
        total=total,
        inversion=inversion,
        hoy=hoy,
        ventas_hoy=ventas_hoy,  # 🔥 NUEVO
        fechas=fechas,
        ganancias=ganancias,
        ventas=ventas_list
    )


# --- CAJA DIARIA (CORREGIDA) ---
@app.route("/caja")
def caja():
    if not esta_logeado():
        return redirect(url_for('login'))

    con = conectar()
    hoy = datetime.now().strftime("%Y-%m-%d")

    ventas = con.execute("""
        SELECT SUM(precio_venta * cantidad) FROM ventas
        WHERE fecha = ?
    """, (hoy,)).fetchone()[0] or 0

    inversion = con.execute("""
        SELECT SUM(monto) FROM inversiones
        WHERE fecha = ?
    """, (hoy,)).fetchone()[0] or 0

    gastos = 0

    con.close()

    ganancia = ventas - inversion

    return render_template(
        "caja.html",
        ventas=ventas,
        inversion=inversion,
        gastos=gastos,
        ganancia=ganancia
    )


# --- INVERSIÓN ---
@app.route("/inversion", methods=["GET", "POST"])
def inversion():
    if not esta_logeado():
        return redirect(url_for('login'))

    con = conectar()

    if request.method == "POST":
        tipo = request.form.get("tipo")
        monto = float(request.form.get("monto") or 0)
        fecha = datetime.now().strftime("%Y-%m-%d")

        if tipo == "producto":
            producto_id = int(request.form.get("producto_id"))
            cantidad = int(request.form.get("cantidad") or 1)

            p = con.execute("SELECT * FROM productos WHERE id=?", (producto_id,)).fetchone()

            if p:
                con.execute("UPDATE productos SET stock = stock + ? WHERE id=?",
                            (cantidad, producto_id))

                descripcion = f"Compra de {p[1]} x{cantidad}"
            else:
                descripcion = "Compra producto (error)"

        else:
            descripcion = request.form.get("descripcion") or "Gasto"

        con.execute("""
            INSERT INTO inversiones (monto, descripcion, fecha)
            VALUES (?, ?, ?)
        """, (monto, descripcion, fecha))

        con.commit()
        con.close()

        return redirect(url_for('dashboard'))

    productos = con.execute("SELECT id, nombre FROM productos").fetchall()
    con.close()

    return render_template("inversion.html", productos=productos)

@app.route("/historial_caja")
def historial_caja():
    if not esta_logeado():
        return redirect(url_for('login'))

    con = conectar()

    datos = con.execute("""
        SELECT 
            v.fecha,
            SUM(v.precio_venta * v.cantidad) as ventas,
            SUM(v.ganancia) as ganancia,
            (SELECT SUM(monto) FROM inversiones i WHERE i.fecha = v.fecha) as inversion
        FROM ventas v
        GROUP BY v.fecha
        ORDER BY v.fecha DESC
    """).fetchall()

    con.close()

    historial = []
    for d in datos:
        fecha = d[0]
        ventas = d[1] or 0
        ganancia = d[2] or 0   # 🔥 AHORA CORRECTO
        inversion = d[3] or 0

        historial.append({
            "fecha": fecha,
            "ventas": ventas,
            "inversion": inversion,
            "ganancia": ganancia
        })

    return render_template("historial_caja.html", historial=historial)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
