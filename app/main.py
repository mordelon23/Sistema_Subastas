# Punto de entrada del sistema de subastas
# Arranca FastAPI y registra todos los routers y WebSockets

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import usuarios, subastas, ofertas, productos, pagos, calificaciones, notificaciones
from app.websockets import manejador_salas

# ─── Instancia principal de FastAPI ──────────────────────────────────────────

app = FastAPI(
    title="Sistema de Subastas",
    description="API REST + WebSocket para sistema de subastas multi-agente",
    version="1.0.0"
)

# ─── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Registrar todos los routers ──────────────────────────────────────────────

app.include_router(usuarios.router)
app.include_router(subastas.router)
app.include_router(ofertas.router)
app.include_router(productos.router)
app.include_router(pagos.router)
app.include_router(calificaciones.router)
app.include_router(notificaciones.router)

# ─── Archivos estáticos del frontend ─────────────────────────────────────────

app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# ─── WebSocket: sala en tiempo real por subasta ───────────────────────────────

@app.websocket("/ws/subasta/{id_subasta}")
async def websocket_subasta(websocket: WebSocket, id_subasta: int):
    """
    Sala WebSocket de una subasta.
    Cada postor se conecta aquí y recibe en tiempo real
    las nuevas ofertas de los demás participantes.
    URL: ws://localhost:8000/ws/subasta/42
    """
    await manejador_salas.conectar(websocket, id_subasta)
    try:
        while True:
            datos = await websocket.receive_text()
            await manejador_salas.broadcast(id_subasta, {
                "tipo": "nueva_oferta",
                "datos": datos
            })
    except WebSocketDisconnect:
        manejador_salas.desconectar(websocket, id_subasta)

# ─── Endpoint de raíz ────────────────────────────────────────────────────────

@app.get("/")
async def raiz():
    """Redirige al frontend"""
    return FileResponse("frontend/index.html")

@app.get("/app")
async def frontend():
    """Endpoint alternativo al frontend"""
    return FileResponse("frontend/index.html")