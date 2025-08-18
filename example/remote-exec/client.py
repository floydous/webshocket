import asyncio
import json
import logging

from webshocket.websocket import client
from webshocket.packets import Packet

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


async def on_receive_message(packet: Packet):
    """
    Callback function to handle messages received from the server.
    """

    message = packet.data

    try:
        if isinstance(message, bytes):
            message = message.decode("utf-8")

        data = json.loads(message)

        msg_type = data.get("type")

        if msg_type == "info":
            logging.info(f"Server Info: {data.get('message')}")
        elif msg_type == "command_output":
            logging.info(f"--- Command: {data.get('command')}")
            if data.get("stdout"):
                print(f"STDOUT:\n{data['stdout']}")
            if data.get("stderr"):
                print(f"STDERR:\n{data['stderr']}")
            print(f"Return Code: {data.get('return_code')}")
            print("---")
        elif msg_type == "error":
            logging.error(f"Server Error: {data.get('message')}")
        else:
            logging.warning(f"Unknown message type received: {message}")

    except json.JSONDecodeError:
        logging.warning(f"Received non-JSON message: {message}")
    except Exception as e:
        logging.error(f"Error processing received message: {e}")


async def main():
    URI = "ws://127.0.0.1:5000"

    logging.info(f"Connecting to Webshocket Remote Command Executor server at {URI}")
    remote_exec_client = client(URI, on_receive=on_receive_message)

    try:
        await remote_exec_client.connect()
        await asyncio.sleep(0.5)

        while remote_exec_client.state == remote_exec_client.state.CONNECTED:
            command = await asyncio.to_thread(input, "> ")

            if command.lower() == "exit":
                await remote_exec_client.send(command)
                break
            await remote_exec_client.send(command)

    except ConnectionRefusedError:
        logging.error("Connection refused. Is the server running?")
    except Exception as e:
        logging.critical(f"Client crashed: {e}")
    finally:
        if remote_exec_client.state != remote_exec_client.state.CLOSED:
            await remote_exec_client.close()
            logging.info("Client disconnected.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Client stopped by user.")
