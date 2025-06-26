import asyncio
import utils
import webshocket
import json  # Added json import

WEBSOCKET_URL = "ws://localhost:5000"
Terminal = utils.Terminal()


async def on_receive(packet: webshocket.packets.Packet) -> None:
    try:
        data = packet.data

        if isinstance(data, bytes):
            data = data.decode("utf-8")

        message = json.loads(data)
        msg_type = message.get("type")

        if msg_type == "chat":
            sender = message.get("sender", "Unknown")
            chat_message = message.get("message", "")
            Terminal.console_log(f"[{sender}]: {chat_message}", level="CHAT")
        elif msg_type == "private_chat":
            sender = message.get("sender", "Unknown")
            chat_message = message.get("message", "")
            Terminal.console_log(
                f"[PRIVATE from {sender}]: {chat_message}", level="CHAT"
            )  # Using MAGENTA for private messages
        elif msg_type == "info":
            info_message = message.get("message", "")
            if info_message.startswith("Connected users:"):
                users_list = info_message.replace("Connected users: ", "").split(", ")
                Terminal.console_log("Server Info: Connected users:", level="INFO")
                for user in users_list:
                    Terminal.console_log(f"  - {user}", level="PLAIN")
            elif info_message.startswith("Active rooms:"):
                rooms_list = info_message.replace("Active rooms: ", "").split(", ")
                Terminal.console_log("Server Info: Active rooms:", level="INFO")
                for room in rooms_list:
                    Terminal.console_log(f"  - {room}", level="PLAIN")
            elif info_message.startswith("Available commands:"):
                commands_list = info_message.split("\n")
                Terminal.console_log("Server Info: Available commands:", level="INFO")
                for cmd_line in commands_list[
                    1:
                ]:  # Skip the "Available commands:" line itself
                    Terminal.console_log(f"  {cmd_line.strip()}", level="PLAIN")
            else:
                Terminal.console_log(f"Server Info: {info_message}", level="INFO")
        elif msg_type == "error":
            error_message = message.get("message", "")
            Terminal.console_log(f"Server Error: {error_message}", level="ERROR")
        else:
            Terminal.console_log(
                f"Received unknown message type: {data}", level="WARNING"
            )
    except json.JSONDecodeError:
        Terminal.console_log(f"Received non-JSON message: {data}", level="WARNING")
    except Exception as e:
        Terminal.console_log(f"Error processing received message: {e}", level="ERROR")


async def main() -> None:
    Terminal.console_log("Connecting to WebSocket server...")

    websocketClient = webshocket.websocket.client(WEBSOCKET_URL, on_receive=on_receive)

    try:
        await websocketClient.connect()
        Terminal.console_log("Connected to WebSocket. Please enter your username:")

        username = await asyncio.to_thread(Terminal.input, "Username: ")
        if not username:
            Terminal.console_log(
                "Username cannot be empty. Disconnecting.", level="ERROR"
            )
            await websocketClient.close()
            return

        await websocketClient.send(username)

        while websocketClient.state == websocketClient.state.CONNECTED:
            user_input = await asyncio.to_thread(
                Terminal.input,
                "Enter message or command (e.g., /help): ",
            )

            if user_input.lower() == "exit":
                Terminal.console_log("Disconnecting...", level="INFO")
                break

            if user_input:  # Only send if input is not empty
                await websocketClient.send(user_input)

    except ConnectionRefusedError:
        Terminal.console_log(
            "Connection refused. Is the server running?", level="ERROR"
        )
    except Exception as e:
        Terminal.console_log(f"Client crashed: {e}", level="CRITICAL")
    finally:
        if websocketClient.state != websocketClient.state.CLOSED:
            await websocketClient.close()
            Terminal.console_log("Client disconnected.", level="INFO")


if __name__ == "__main__":
    asyncio.run(main())
