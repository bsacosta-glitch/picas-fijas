# Picas y Fijas distribuido

API REST en Python/Flask con front básico, desplegable en Kubernetes.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | /login | Registra un jugador |
| POST | /juego | Crea un juego con tu número |
| PUT | /juego/{id} | Se une a un juego |
| POST | /juego/{id}/jugar | Envía un intento (solo en tu turno) |
| GET | /juego/{id} | Estado de un juego |
| GET | /juego | Lista de juegos |

## Correr en local

    pip install -r requirements.txt
    python app.py

## Desplegar en Kubernetes (Killercoda)

    kubectl apply -f k8s/

Luego abrir el puerto 30080 en Traffic / Ports.

Imagen: brayan1239/picas-fijas:1.0 (Docker Hub)