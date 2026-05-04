from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import time
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = "vapers_store_key_2024"

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

USUARIO_ADMIN = "admin"
CLAVE_ADMIN = "Yepes1504"


def conectar():
    import os
    DATABASE_URL = os.getenv("DATABASE_URL")

    if DATABASE_URL:
        import psycopg
        return psycopg.connect(DATABASE_URL)
    else:
        import sqlite3
        return sqlite3.connect("database.db")

def init_db():
    with conectar() as con:
               # PRODUCTOS ✅
        con.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY,
            nombre TEXT,
            categoria TEXT,
            precio_compra REAL,
            precio_venta REAL,
            precio_mayorista REAL,
            stock INTEGER,
            imagen TEXT
        )
        """)

        # VENTAS ✅ (CORREGIDO)
        con.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id SERIAL PRIMARY KEY,
            producto_id INTEGER,
            nombre TEXT,
            cantidad INTEGER,
            precio_compra REAL,
            precio_venta REAL,
            ganancia REAL,
            fecha TEXT
        )
        """)

        # INVERSIONES ✅ (CORREGIDO)
        con.execute("""
        CREATE TABLE IF NOT EXISTS inversiones (
            id SERIAL PRIMARY KEY,
            monto REAL,
            descripcion TEXT,
            fecha TEXT
        )
        """)
        # 🔥 PARCHE DE SEGURIDAD: Fuerza la columna si no existe
        try:
            con.execute("ALTER TABLE productos ADD COLUMN precio_mayorista REAL")
        except:
            pass
        con.commit()


init_db()


def esta_logeado():
    return "usuario" in session


# --- RUTAS DE ACCESO ---

@app.route("/", methods=["GET", "POST"])
def login():
    if esta_logeado(): return redirect(url_for('ventas'))
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


# --- GESTIÓN DE PRODUCTOS ---

@app.route("/index")
def index():
    if not esta_logeado(): return redirect(url_for('login'))
    with conectar() as con:
        productos = con.execute("""
        SELECT 
            id,
            nombre,
            categoria,
            precio_compra,
            precio_venta,
            precio_mayorista,
            stock,
            imagen
        FROM productos
        ORDER BY id DESC
        """).fetchall()
    return render_template("index.html", productos=productos)


@app.route("/ventas")
def ventas():
    if not esta_logeado(): return redirect(url_for('login'))
    with conectar() as con:
        productos = con.execute("""
        SELECT 
            id,
            nombre,
            categoria,
            precio_compra,
            precio_venta,
            precio_mayorista,
            stock,
            imagen
        FROM productos
        ORDER BY id DESC
        """).fetchall()
    return render_template("ventas.html", productos=productos)


@app.route("/agregar", methods=["GET", "POST"])
def agregar():
    if not esta_logeado(): return redirect(url_for('login'))
    if request.method == "POST":
        try:
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

            with conectar() as con:
                con.execute("""
                    INSERT INTO productos (nombre, categoria, precio_compra, precio_venta, precio_mayorista, stock, imagen)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (nombre, categoria, p_compra, p_venta, p_mayorista, stock, n_img))

                if stock > 0 and p_compra > 0:
                    con.execute("INSERT INTO inversiones (monto, descripcion, fecha) VALUES (?, ?, ?)",
                                (p_compra * stock, f"Compra inicial {nombre}", datetime.now().strftime("%Y-%m-%d")))
                con.commit()
            return redirect(url_for('index'))
        except Exception as e:
            return f"Error al agregar: {e}"
    return render_template("agregar.html")


@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    if not esta_logeado(): return redirect(url_for('login'))
    con = conectar()
    producto = con.execute("SELECT * FROM productos WHERE id=?", (id,)).fetchone()
    if request.method == "POST":
        nombre = request.form.get("nombre")
        categoria = request.form.get("categoria")
        p_compra = float(request.form.get("precio_compra") or 0)
        p_venta = float(request.form.get("precio_venta") or 0)
        p_mayorista = float(request.form.get("precio_mayorista") or 0)
        stock = int(request.form.get("stock") or 0)
        n_img = producto["imagen"]
        if 'imagen' in request.files:
            img = request.files['imagen']
            if img and img.filename != "":
                n_img = str(int(time.time())) + "_" + secure_filename(img.filename)
                img.save(os.path.join(app.config["UPLOAD_FOLDER"], n_img))

        con.execute("""
            UPDATE productos SET nombre=?, categoria=?, precio_compra=?, precio_venta=?, precio_mayorista=?, stock=?, imagen=?
            WHERE id=?
        """, (nombre, categoria, p_compra, p_venta, p_mayorista, stock, n_img, id))
        con.commit()
        con.close()
        return redirect(url_for('index'))
    con.close()
    return render_template("editar.html", producto=producto)


@app.route("/eliminar/<int:id>")
def eliminar(id):
    if not esta_logeado(): return redirect(url_for('login'))
    with conectar() as con:
        con.execute("DELETE FROM productos WHERE id=?", (id,))
        con.commit()
    return redirect(url_for('index'))


# --- VENTAS Y TICKETS ---

@app.route("/venta/<int:id>", methods=["POST"])
def venta(id):
    if not esta_logeado(): return redirect(url_for('login'))
    con = conectar()
    p = con.execute("SELECT * FROM productos WHERE id=?", (id,)).fetchone()
    cantidad = int(request.form.get("cantidad") or 1)

    if p and p["stock"] >= cantidad:
        # Lógica mayorista: si es vape y lleva 15+ usa p_mayorista
        precio_f = p["precio_mayorista"] if (
                    p["categoria"].lower() == "vape" and cantidad >= 15 and p["precio_mayorista"] > 0) else p[
            "precio_venta"]
        ganancia = (precio_f - p["precio_compra"]) * cantidad
        fecha = datetime.now().strftime("%Y-%m-%d")

        con.execute("UPDATE productos SET stock = stock - ? WHERE id=?", (cantidad, id))
        con.execute("""INSERT INTO ventas (producto_id, nombre, cantidad, precio_compra, precio_venta, ganancia, fecha) 
                    VALUES (?,?,?,?,?,?,?)""",
                    (id, p["nombre"], cantidad, p["precio_compra"], precio_f, ganancia, fecha))
        con.commit()

        session["ticket"] = {"nombre": p["nombre"], "cantidad": cantidad, "total": precio_f * cantidad,
                             "ganancia": ganancia}
        flash(f"✅ Vendido: {p['nombre']}")
    else:
        flash("❌ Error en stock")
    con.close()
    return redirect(url_for('ticket'))


@app.route("/ticket")
def ticket():
    if not esta_logeado(): return redirect(url_for('login'))
    t = session.get("ticket")
    return render_template("ticket.html", t=t)


# --- CAJA E INVERSIONES ---

@app.route("/dashboard")
def dashboard():
    if not esta_logeado(): return redirect(url_for('login'))
    con = conectar()
    hoy_f = datetime.now().strftime("%Y-%m-%d")
    total_g = con.execute("SELECT SUM(ganancia) FROM ventas").fetchone()[0] or 0
    inv_t = con.execute("SELECT SUM(monto) FROM inversiones").fetchone()[0] or 0
    hoy_g = con.execute("SELECT SUM(ganancia) FROM ventas WHERE fecha=?", (hoy_f,)).fetchone()[0] or 0
    ventas_hoy = con.execute("SELECT SUM(precio_venta * cantidad) FROM ventas WHERE fecha=?", (hoy_f,)).fetchone()[
                     0] or 0
    ventas_list = con.execute("SELECT * FROM ventas ORDER BY id DESC LIMIT 10").fetchall()
    con.close()
    return render_template("dashboard.html", total=total_g, inversion=inv_t, hoy=hoy_g, ventas_hoy=ventas_hoy,
                           ventas=ventas_list)


@app.route("/caja")
def caja():
    if not esta_logeado(): return redirect(url_for('login'))
    con = conectar()
    hoy = datetime.now().strftime("%Y-%m-%d")
    v_total = con.execute("SELECT SUM(precio_venta * cantidad) FROM ventas WHERE fecha=?", (hoy,)).fetchone()[0] or 0
    inv_total = con.execute("SELECT SUM(monto) FROM inversiones WHERE fecha=?", (hoy,)).fetchone()[0] or 0
    con.close()
    return render_template("caja.html", ventas=v_total, inversion=inv_total, ganancia=v_total - inv_total)


@app.route("/inversion", methods=["GET", "POST"])
def inversion():
    if not esta_logeado(): return redirect(url_for('login'))
    con = conectar()
    if request.method == "POST":
        tipo = request.form.get("tipo")
        monto = float(request.form.get("monto") or 0)
        fecha = datetime.now().strftime("%Y-%m-%d")
        if tipo == "producto":
            p_id = int(request.form.get("producto_id"))
            cant = int(request.form.get("cantidad") or 1)
            p = con.execute("SELECT * FROM productos WHERE id=?", (p_id,)).fetchone()
            con.execute("UPDATE productos SET stock = stock + ? WHERE id=?", (cant, p_id))
            desc = f"Resurtido {p['nombre']} x{cant}"
        else:
            desc = request.form.get("descripcion") or "Gasto general"
        con.execute("INSERT INTO inversiones (monto, descripcion, fecha) VALUES (?, ?, ?)", (monto, desc, fecha))
        con.commit()
        con.close()
        return redirect(url_for('dashboard'))

    productos = con.execute("SELECT id, nombre FROM productos").fetchall()
    con.close()
    return render_template("inversion.html", productos=productos)


@app.route("/historial_caja")
def historial_caja():
    if not esta_logeado(): return redirect(url_for('login'))
    con = conectar()
    datos = con.execute("""
        SELECT v.fecha, SUM(v.precio_venta * v.cantidad) as ventas, SUM(v.ganancia) as ganancia,
        (SELECT SUM(monto) FROM inversiones i WHERE i.fecha = v.fecha) as inversion
        FROM ventas v GROUP BY v.fecha ORDER BY v.fecha DESC
    """).fetchall()
    con.close()
    return render_template("historial_caja.html", historial=datos)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
