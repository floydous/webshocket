import asyncio
import utils
import webshocket

WEBSOCKET_URL = "ws://localhost:5000"
Terminal = utils.Terminal()


async def on_receive(packet: webshocket.Packet):
    try:
        data = packet.data

        for index, line in enumerate(data.splitlines()):
            Terminal.console_log(line, level=("CHAT" if index == 0 else "PLAIN"))

    except Exception as err:
        Terminal.console_log(f"Error processing received message: {err}", level="ERROR")


async def main() -> None:
    Terminal.console_log("Connecting to WebSocket server...")
    websocketClient = webshocket.WebSocketClient(WEBSOCKET_URL, on_receive=on_receive)

    try:
        await websocketClient.connect()
        Terminal.console_log("Connected to WebSocket. Please enter your username:")

        while True:
            username = await asyncio.to_thread(Terminal.input, "Username: ")

            if not username:
                Terminal.console_log("Username cannot be empty. Disconnecting.", level="ERROR")
                await websocketClient.close()
                return

            response = await websocketClient.send_rpc("register_user", username)

            if response.data is True:
                Terminal.console_log(f"Connected as {username}.", level="INFO")
                break

            else:
                Terminal.logs.clear()
                Terminal.console_log(
                    "Username already taken. Please choose another.",
                    level="ERROR",
                )

        while websocketClient.state == websocketClient.state.CONNECTED:
            user_input = await asyncio.to_thread(Terminal.input, "Enter message or command (e.g., /help): ")

            if user_input.startswith("/"):
                splited_input = user_input.split(" ")
                response = await websocketClient.send_rpc(
                    "trigger_command",
                    splited_input[0][1:],
                    *splited_input[1:],
                )

                if response.data:
                    lines = response.data.splitlines()
                    Terminal.console_log(lines[0], level="INFO")

                    for line in lines[1:]:
                        Terminal.console_log(line, level="PLAIN")

                continue

            elif user_input.lower() == "exit":
                Terminal.console_log("Disconnecting...", level="INFO")
                break

            else:
                await websocketClient.send(user_input)

    except ConnectionRefusedError:
        Terminal.console_log("Connection refused. Is the server running?", level="ERROR")
    except Exception as e:
        Terminal.console_log(f"Client crashed: {e}", level="CRITICAL")
    finally:
        if websocketClient.state != websocketClient.state.CLOSED:
            await websocketClient.close()
            Terminal.console_log("Client disconnected.", level="INFO")


if __name__ == "__main__":
    asyncio.run(main())
    # __import__("time").sleep(5)
