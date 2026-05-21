# WebSocket: sala en tiempo real por subasta
# Cada subasta tiene su propia sala donde los postores ven las ofertas al instante

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import json


class SalaSubasta:
    """
    Administra las conexiones WebSocket de una subasta.
    Equivale a un chat grupal donde todos ven las mismas ofertas.
    """

    def __init__(self):
        # Diccionario: id_subasta → lista de conexiones activas
        self.salas: Dict[int, List[WebSocket]] = {}

    async def conectar(self, websocket: WebSocket, id_subasta: int):
        """Agrega un postor a la sala de una subasta."""
        await websocket.accept()

        # Crear sala si no existe
        if id_subasta not in self.salas:
            self.salas[id_subasta] = []

        self.salas[id_subasta].append(websocket)

    def desconectar(self, websocket: WebSocket, id_subasta: int):
        """Elimina un postor de la sala cuando se desconecta."""
        if id_subasta in self.salas:
            self.salas[id_subasta].remove(websocket)

            # Limpiar sala vacía
            if not self.salas[id_subasta]:
                del self.salas[id_subasta]

    async def broadcast(self, id_subasta: int, mensaje: dict):
        """
        Envía un mensaje a TODOS los postores en la sala.
        Se llama cuando alguien hace una oferta nueva.
        """
        if id_subasta not in self.salas:
            return

        # Notificar a cada conexión activa
        conexiones_caidas = []
        for conexion in self.salas[id_subasta]:
            try:
                await conexion.send_text(json.dumps(mensaje))
            except Exception:
                # Marcar conexiones caídas para limpiar
                conexiones_caidas.append(conexion)

        # Limpiar conexiones caídas
        for conexion in conexiones_caidas:
            self.salas[id_subasta].remove(conexion)


# Instancia global del manejador de salas
manejador_salas = SalaSubasta()
