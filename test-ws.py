import asyncio
import websockets

async def test_websocket():
    uri = "ws://localhost:8080"
    async with websockets.connect(uri) as websocket:
        # Envoyer un message au serveur
        message = "Hello, server!"
        print(f"Sending message to server: {message}")
        await websocket.send(message)

        # Recevoir la réponse du serveur
        response = await websocket.recv()
        print(f"Received response from server: {response}")

# Exécuter le test WebSocket
asyncio.get_event_loop().run_until_complete(test_websocket())

