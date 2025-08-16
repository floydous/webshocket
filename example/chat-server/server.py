from webshocket.packets import Packet
import asyncio
import webshocket
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class clientHandler(webshocket.WebSocketHandler):
    async def on_disconnect(self, websocket: webshocket.ClientConnection):
        if websocket.session_state.get("username"):
            logging.info(f"User '{websocket.session_state['username']}' has left the chat.")

            await self.broadcast(
                f"User '{websocket.session_state['username']}' has left the chat.",
                exclude=tuple(conn for conn in self.clients if websocket.session_state.get("username") is None),
            )

    async def on_receive(self, connection: webshocket.ClientConnection, packet: Packet):
        if connection.session_state.get("username") is None:
            return

        logging.info(f"Received message from {connection.username}: {packet.data}")

        message: str = f"{connection.username}: {packet.data}"
        await self.publish(channel=connection.subscribed_channel, data=message)

    @webshocket.rpc_method(
        alias_name="trigger_command",
        requires=lambda connection: getattr(connection, "username") is not None,
    )
    async def trigger_command(self, connection: webshocket.ClientConnection, command_name: str, *args):
        logging.info(f"Received command from {connection.username}: {command_name} {args}")

        if command_name == "help":
            help_message = (
                "Available commands:\n"
                "  /join <room_name> - Join or switch to a chat room.\n"
                "  /msg <username> <message> - Send a private message to a user.\n"
                "  /users - List all connected users.\n"
                "  /rooms - List all active chat rooms.\n"
                "  /help - Display this help message."
            )

            return help_message

        elif command_name == "msg":
            if not len(args) >= 2:
                return "Usage: /msg <username> <message>"

            target_username = args[0]
            message = " ".join(args[1:])

            for client in self.clients:
                if (_username := client.session_state.get("username")) == target_username and _username != connection.username:
                    await client.send(message)
                    return f"Private message to {target_username}: {message}"

            return f"User '{target_username}' not found."

        elif command_name == "rooms":
            active_rooms: str = ", ".join([name for name in self.channels.keys()])
            return "Active rooms: " + active_rooms

        elif command_name == "join":
            if not len(args) >= 1:
                return "Usage: /join <room_name>"

            room_name = args[0]

            if room_name in connection.subscribed_channel:
                return "You are already in this room."

            for room in list(connection.subscribed_channel):
                connection.unsubscribe(room)

            connection.subscribe(room_name)
            return f"You joined room '{room_name}'."

        elif command_name == "users":
            return f"Connected users: {', '.join([conn.username for conn in self.clients if getattr(conn, 'username') is not None])}"

        elif command_name == "msg":
            if not len(args) >= 2:
                return "Usage: /msg <username> <message>"

            target_username = args[0]
            message = " ".join(args[1:])

            for client in self.clients:
                if (_username := client.session_state.get("username")) == target_username and _username != connection.username:
                    # await client.send(f"Private message from {connection.username}: {message}")
                    return f"Private message to {target_username}: {message}"

            return f"User '{target_username}' not found."

        else:
            return f"Unknown command: {command_name}. Type /help for commands."

    @webshocket.rpc_method(alias_name="register_user")
    async def register(self, connection: webshocket.ClientConnection, username: str) -> bool:
        if username in [conn.session_state.get("username") for conn in self.clients]:
            return False

        logging.info(f"User '{username}' has joined the chat.")

        await self.broadcast(
            f"User '{username}' has joined the chat.",
            exclude=tuple(conn for conn in self.clients if conn.session_state.get("username") is None),
        )

        connection.username = username
        connection.subscribe("lobby")
        return True


async def main() -> None:
    server = webshocket.websocket.server("127.0.0.1", 5000, clientHandler=clientHandler)
    await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
