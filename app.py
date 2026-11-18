import random
import socket
import threading
import uuid
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="static")

# Datos en memoria (se pierden si el programa se reinicia)
jugadores = set()
juegos = {}
candado = threading.Lock()  # evita que dos peticiones cambien datos a la vez


def validar_numero(numero):
    """Devuelve un mensaje de error, o None si el número es válido."""
    if not isinstance(numero, str):
        return 'El número debe ser texto, por ejemplo "1234"'
    if len(numero) != 4:
        return "El número debe tener 4 dígitos"
    if not numero.isdigit():
        return "El número solo puede tener dígitos"
    if len(set(numero)) != 4:
        return "Los 4 dígitos no pueden repetirse"
    return None


def picas_y_fijas(secreto, intento):
    fijas = sum(1 for s, i in zip(secreto, intento) if s == i)
    comunes = len(set(secreto) & set(intento))
    picas = comunes - fijas
    return picas, fijas


def leer_datos():
    return request.get_json(silent=True) or {}


def vista_publica(juego):
    """Nunca mostramos los números secretos."""
    return {
        "id": juego["id"],
        "creador": juego["creador"],
        "jugadores": juego["jugadores"],
        "estado": juego["estado"],
        "turno": juego["turno"],
        "ganador": juego["ganador"],
        "intentos": juego["intentos"],
    }


@app.post("/login")
def login():
    nombre = str(leer_datos().get("nombre", "")).strip()
    if not nombre:
        return jsonify(error="Debes enviar un nombre"), 400
    with candado:
        jugadores.add(nombre)
    return jsonify(nombre=nombre, mensaje="Sesión iniciada"), 200


@app.post("/juego")
def crear_juego():
    datos = leer_datos()
    nombre = str(datos.get("nombre", "")).strip()
    numero = datos.get("numero")

    if nombre not in jugadores:
        return jsonify(error="Primero haz /login"), 401
    problema = validar_numero(numero)
    if problema:
        return jsonify(error=problema), 400

    with candado:
        id_juego = uuid.uuid4().hex[:6]
        juegos[id_juego] = {
            "id": id_juego,
            "creador": nombre,
            "jugadores": [nombre],
            "secretos": {nombre: numero},
            "estado": "esperando",
            "turno": None,
            "ganador": None,
            "intentos": [],
        }
        return jsonify(vista_publica(juegos[id_juego])), 201


@app.put("/juego/<id_juego>")
def unirse(id_juego):
    datos = leer_datos()
    nombre = str(datos.get("nombre", "")).strip()
    numero = datos.get("numero")

    if nombre not in jugadores:
        return jsonify(error="Primero haz /login"), 401
    problema = validar_numero(numero)
    if problema:
        return jsonify(error=problema), 400

    with candado:
        juego = juegos.get(id_juego)
        if juego is None:
            return jsonify(error="Ese juego no existe"), 404
        if juego["estado"] != "esperando":
            return jsonify(error="El juego ya tiene 2 jugadores"), 409
        if nombre in juego["jugadores"]:
            return jsonify(error="No puedes unirte a tu propio juego"), 409

        juego["jugadores"].append(nombre)
        juego["secretos"][nombre] = numero
        juego["estado"] = "en_juego"
        juego["turno"] = random.choice(juego["jugadores"])  # sorteo del primer turno
        return jsonify(vista_publica(juego)), 200


@app.post("/juego/<id_juego>/jugar")
def jugar(id_juego):
    datos = leer_datos()
    nombre = str(datos.get("nombre", "")).strip()
    intento = datos.get("numero")

    with candado:
        juego = juegos.get(id_juego)
        if juego is None:
            return jsonify(error="Ese juego no existe"), 404
        if juego["estado"] != "en_juego":
            return jsonify(error="El juego no está en curso"), 409
        if nombre not in juego["jugadores"]:
            return jsonify(error="No eres jugador de este juego"), 403
        if juego["turno"] != nombre:
            return jsonify(error=f"No es tu turno, le toca a {juego['turno']}"), 409
        problema = validar_numero(intento)
        if problema:
            return jsonify(error=problema), 400

        rival = [j for j in juego["jugadores"] if j != nombre][0]
        picas, fijas = picas_y_fijas(juego["secretos"][rival], intento)
        juego["intentos"].append(
            {"jugador": nombre, "numero": intento, "picas": picas, "fijas": fijas}
        )

        if fijas == 4:
            juego["estado"] = "terminado"
            juego["ganador"] = nombre
            juego["turno"] = None
        else:
            juego["turno"] = rival  # cambia el turno

        return jsonify(
            picas=picas, fijas=fijas, gano=(fijas == 4), turno_siguiente=juego["turno"]
        ), 200


@app.get("/juego/<id_juego>")
def ver_juego(id_juego):
    with candado:
        juego = juegos.get(id_juego)
        if juego is None:
            return jsonify(error="Ese juego no existe"), 404
        return jsonify(vista_publica(juego)), 200


@app.get("/juego")
def listar_juegos():
    with candado:
        lista = [
            {"id": j["id"], "creador": j["creador"], "jugadores": j["jugadores"],
             "estado": j["estado"], "ganador": j["ganador"]}
            for j in juegos.values()
        ]
    return jsonify(lista), 200


@app.get("/salud")
def salud():
    # Kubernetes usa esta ruta para saber si el pod está bien
    return jsonify(ok=True, pod=socket.gethostname()), 200


@app.get("/")
def inicio():
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)