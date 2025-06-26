import asyncio
import subprocess
import json
import logging

from webshocket.websocket import server
from webshocket.handler import WebSocketHandler
from webshocket.connection import ClientConnection
from webshocket.packets import Packet

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class RemoteExecHandler(WebSocketHandler):
    """
    Handles incoming WebSocket messages by executing them as shell commands
    and sending the output back to the client.
    """

    async def on_connect(self, websocket: ClientConnection):
        logging.info(f"Client connected: {websocket.id}")
        await websocket.send(
            json.dumps(
                {
                    "type": "info",
                    "message": "Connected to Remote Command Executor. Type 'exit' to disconnect.",
                }
            )
        )

    async def on_disconnect(self, websocket: ClientConnection):
        logging.info(f"Client disconnected: {websocket.id}")

    async def on_receive(self, websocket: ClientConnection, packet: Packet):
        """
        Receives a command, executes it, and sends the output back.
        """
        data = packet.data

        try:
            if isinstance(data, bytes):
                command = data.decode("utf-8")
            else:
                command = str(data)  # Ensure it's a string
            command = command.strip()
            logging.info(f"Received command from {websocket.id}: '{command}'")

            if command.lower() == "exit":
                logging.info(f"Client {websocket.id} requested disconnect.")
                await websocket.send(
                    json.dumps({"type": "info", "message": "Disconnecting..."})
                )
                await websocket.close()
                return

            # Execute the command
            process = await asyncio.create_subprocess_shell(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )

            stdout, stderr = await process.communicate()

            output = stdout.decode("utf-8", errors="ignore").strip()
            error = stderr.decode("utf-8", errors="ignore").strip()

            response = {
                "type": "command_output",
                "command": command,
                "return_code": process.returncode,
                "stdout": output,
                "stderr": error,
            }
            await websocket.send(json.dumps(response))
            logging.info(f"Sent response for command '{command}' to {websocket.id}")

        except Exception as e:
            error_message = f"Error processing command: {e}"
            logging.error(error_message)
            await websocket.send(
                json.dumps({"type": "error", "message": error_message})
            )


async def main():
    HOST = "127.0.0.1"
    PORT = 5000

    logging.info(
        f"Starting Webshocket Remote Command Executor server on ws://{HOST}:{PORT}"
    )
    remote_exec_server = server(HOST, PORT, clientHandler=RemoteExecHandler)
    await remote_exec_server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server stopped by user.")
    except Exception as e:
        logging.critical(f"Server crashed: {e}")
