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

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER  # 🔥 primero se define

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)  # 🔥 luego se usa
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

USUARIO_ADMIN = "admin"
CLAVE_ADMIN = "Yepes1504"

def conectar():
    DATABASE_URL = os.getenv("DATABASE_URL")

    if DATABASE_URL:
        import psycopg
        from psycopg.rows import dict_row  # 🔥 IMPORTANTE
        conn = psycopg.connect(DATABASE_URL)
        conn.row_factory = dict_row       # 🔥 ESTO ARREGLA TODO
        return conn
    else:
        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row
        return conn

def get_placeholder():
    return "%s" if os.getenv("DATABASE_URL") else "?"

def init_db():
    with conectar() as con:
        is_postgres = os.getenv("DATABASE_URL") is not None
        id_type = "SERIAL" if is_postgres else "INTEGER"
        pk_type = "PRIMARY KEY" if is_postgres else "PRIMARY KEY AUTOINCREMENT"

        # PRODUCTOS
        con.execute(f"""
        CREATE TABLE IF NOT EXISTS productos (
            id {id_type} {pk_type},
            nombre TEXT,
            categoria TEXT,
            precio_compra REAL,
            precio_venta REAL,
            precio_mayorista REAL,
            stock INTEGER,
            imagen TEXT
        )""")

        # VENTAS
        con.execute(f"""
        CREATE TABLE IF NOT EXISTS ventas (
            id {id_type} {pk_type},
            producto_id INTEGER,
            nombre TEXT,
            cantidad INTEGER,
            precio_compra REAL,
            precio_venta REAL,
            ganancia REAL,
            fecha TEXT
        )""")

        # INVERSIONES
        con.execute(f"""
        CREATE TABLE IF NOT EXISTS inversiones (
            id {id_type} {pk_type},
            monto REAL,
            descripcion TEXT,
            fecha TEXT
        )""")
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
        # Aseguramos el orden exacto de columnas para el HTML
        productos = con.execute("SELECT id, nombre, categoria, precio_compra, precio_venta, precio_mayorista, stock, imagen FROM productos ORDER BY id DESC").fetchall()
    return render_template("index.html", productos=productos)

@app.route("/ventas")
def ventas():
    if not esta_logeado(): return redirect(url_for('login'))
    with conectar() as con:
        productos = con.execute("SELECT id, nombre, categoria, precio_compra, precio_venta, precio_mayorista, stock, imagen FROM productos ORDER BY id DESC").fetchall()
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

            placeholder = get_placeholder()
            with conectar() as con:
                con.execute(f"INSERT INTO productos (nombre, categoria, precio_compra, precio_venta, precio_mayorista, stock, imagen) VALUES ({placeholder},{placeholder},{placeholder},{placeholder},{placeholder},{placeholder},{placeholder})", 
                            (nombre, categoria, p_compra, p_venta, p_mayorista, stock, n_img))
                if stock > 0 and p_compra > 0:
                    con.execute(f"INSERT INTO inversiones (monto, descripcion, fecha) VALUES ({placeholder},{placeholder},{placeholder})", 
                                (p_compra * stock, f"Compra inicial {nombre}", datetime.now().strftime("%Y-%m-%d")))
                con.commit()
            return redirect(url_for('index'))
        except Exception as e:
            return f"Error al agregar: {e}"
    return render_template("agregar.html")

@app.route("/editar/<int:id>", methods=["GET", "POST"])
if request.method == "POST":
    nombre = request.form.get("nombre") or p["nombre"]
    categoria = request.form.get("categoria") or p["categoria"]

    p_compra = request.form.get("precio_compra")
    p_venta = request.form.get("precio_venta")
    stock = request.form.get("stock")

    p_compra = float(p_compra) if p_compra else p["precio_compra"]
    p_venta = float(p_venta) if p_venta else p["precio_venta"]
    stock = int(stock) if stock else p["stock"]

    # ❌ quitamos mayorista (no lo usas aquí)
    p_mayorista = p["precio_mayorista"]

    n_img = p["imagen"] if p else ""
    if 'imagen' in request.files:
        img = request.files['imagen']
        if img and img.filename != "":
            n_img = str(int(time.time())) + "_" + secure_filename(img.filename)
            img.save(os.path.join(app.config["UPLOAD_FOLDER"], n_img))

    con.execute(f"""
        UPDATE productos SET 
        nombre={placeholder}, 
        categoria={placeholder}, 
        precio_compra={placeholder}, 
        precio_venta={placeholder}, 
        precio_mayorista={placeholder}, 
        stock={placeholder}, 
        imagen={placeholder} 
        WHERE id={placeholder}
    """, (nombre, categoria, p_compra, p_venta, p_mayorista, stock, n_img, id))

    con.commit()
    con.close()
    return redirect(url_for('index'))

@app.route("/eliminar/<int:id>")
def eliminar(id):
    if not esta_logeado(): return redirect(url_for('login'))
    placeholder = get_placeholder()
    with conectar() as con:
        con.execute(f"DELETE FROM productos WHERE id={placeholder}", (id,))
        con.commit()
    return redirect(url_for('index'))

# --- VENTAS Y TICKETS ---

@app.route("/venta/<int:id>", methods=["POST"])
def venta(id):
    if not esta_logeado(): return redirect(url_for('login'))
    placeholder = get_placeholder()
    con = conectar()
    p = con.execute(f"SELECT * FROM productos WHERE id={placeholder}", (id,)).fetchone()
    cantidad = int(request.form.get("cantidad") or 1)

    if p and p["stock"] >= cantidad:
        precio_f = p["precio_mayorista"] if (p["categoria"] and p["categoria"].lower() == "vape" and cantidad >= 15 and p["precio_mayorista"] > 0) else p["precio_venta"]
        ganancia = (precio_f - p["precio_compra"]) * cantidad
        fecha = datetime.now().strftime("%Y-%m-%d")

        con.execute(f"UPDATE productos SET stock = stock - {placeholder} WHERE id={placeholder}", (cantidad, id))
        con.execute(f"INSERT INTO ventas (producto_id, nombre, cantidad, precio_compra, precio_venta, ganancia, fecha) VALUES ({placeholder},{placeholder},{placeholder},{placeholder},{placeholder},{placeholder},{placeholder})",
                    (id, p["nombre"], cantidad, p["precio_compra"], precio_f, ganancia, fecha))
        con.commit()
        session["ticket"] = {"nombre": p["nombre"], "cantidad": cantidad, "total": precio_f * cantidad, "ganancia": ganancia}
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
    if not esta_logeado():
        return redirect(url_for('login'))

    placeholder = get_placeholder()
    con = conectar()

    hoy_f = datetime.now().strftime("%Y-%m-%d")

    total_g = con.execute("SELECT SUM(ganancia) AS total FROM ventas").fetchone()
    inv_t = con.execute("SELECT SUM(monto) AS total FROM inversiones").fetchone()

    hoy_g = con.execute(
        f"SELECT SUM(ganancia) AS total FROM ventas WHERE fecha={placeholder}",
        (hoy_f,)
    ).fetchone()

    ventas_hoy = con.execute(
        f"SELECT SUM(precio_venta * cantidad) AS total FROM ventas WHERE fecha={placeholder}",
        (hoy_f,)
    ).fetchone()

    ventas_list = con.execute(
        "SELECT * FROM ventas ORDER BY id DESC LIMIT 10"
    ).fetchall()

    con.close()

    return render_template(
        "dashboard.html",
        total=total_g["total"] or 0,
        inversion=inv_t["total"] or 0,
        hoy=hoy_g["total"] or 0,
        ventas_hoy=ventas_hoy["total"] or 0,
        ventas=ventas_list
    )
@app.route("/caja")
def caja():
    if not esta_logeado():
        return redirect(url_for('login'))

    placeholder = get_placeholder()
    con = conectar()

    hoy = datetime.now().strftime("%Y-%m-%d")

    # 💰 TOTAL VENTAS DEL DÍA
    v_total = con.execute(
        f"SELECT SUM(precio_venta * cantidad) AS total FROM ventas WHERE fecha={placeholder}",
        (hoy,)
    ).fetchone()

    # 📈 GANANCIA REAL (SOLO DE VENTAS)
    ganancia = con.execute(
        f"SELECT SUM(ganancia) AS total FROM ventas WHERE fecha={placeholder}",
        (hoy,)
    ).fetchone()

    # 💸 INVERSIÓN  (solo informativo)
    inv_total = con.execute(
        f"SELECT SUM(monto) AS total FROM inversiones WHERE fecha={placeholder}",
        (hoy,)
    ).fetchone()

    con.close()

    return render_template(
        "caja.html",
        ventas=v_total["total"] or 0,
        inversion=inv_total["total"] or 0,
        gastos=0,  # por ahora
        ganancia=ganancia["total"] or 0
    )

@app.route("/inversion", methods=["GET", "POST"])
def inversion():
    if not esta_logeado(): return redirect(url_for('login'))
    placeholder = get_placeholder()
    con = conectar()
    if request.method == "POST":
        tipo = request.form.get("tipo")
        monto = float(request.form.get("monto") or 0)
        fecha = datetime.now().strftime("%Y-%m-%d")
        if tipo == "producto":
            p_id = int(request.form.get("producto_id"))
            cant = int(request.form.get("cantidad") or 1)
            p = con.execute(f"SELECT * FROM productos WHERE id={placeholder}", (p_id,)).fetchone()
            con.execute(f"UPDATE productos SET stock = stock + {placeholder} WHERE id={placeholder}", (cant, p_id))
            desc = f"Resurtido {p['nombre']} x{cant}"
        else:
            desc = request.form.get("descripcion") or "Gasto general"
        con.execute(f"INSERT INTO inversiones (monto, descripcion, fecha) VALUES ({placeholder}, {placeholder}, {placeholder})", (monto, desc, fecha))
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
    app.run(host="0.0.0.0", port=5000)
