from webshocket.handler import WebSocketHandler
from webshocket.packets import Packet
import asyncio  # Re-added asyncio
import webshocket
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class clientHandler(WebSocketHandler):
    async def on_connect(self, websocket: webshocket.ClientConnection):
        username_data = await websocket.recv()
        username = str(username_data.data).strip()

        if not username:
            await websocket.send(
                json.dumps({"type": "error", "message": "Username cannot be empty."})
            )
            await websocket.close()
            logging.info(f"Client {websocket.id} disconnected due to empty username.")
            return

        # Check for duplicate usernames
        for client_conn in self.clients:
            if client_conn.session_state.get("_username") == username:
                await websocket.send(
                    json.dumps(
                        {
                            "type": "error",
                            "message": f"Username '{username}' is already taken. Please choose another.",
                        }
                    )
                )
                await websocket.close()
                logging.info(
                    f"Client {websocket.id} disconnected due to duplicate username: {username}."
                )
                return

        websocket["_username"] = username
        websocket.subscribe(channel="lobby")  # Default channel

        logging.info(f"Client connected: {websocket.id} with username: {username}")
        await self.broadcast(
            json.dumps(
                {
                    "type": "chat",
                    "sender": "Server",
                    "message": f"{username} just joined the chat!",
                }
            )
        )
        await websocket.send(
            json.dumps(
                {
                    "type": "info",
                    "message": f"Welcome, {username}! You are in 'lobby'. Type /help for commands.",
                }
            )
        )

    async def on_disconnect(self, websocket: webshocket.ClientConnection):
        username = websocket.session_state.get("_username", "UnknownUser")
        logging.info(f"Client disconnected: {websocket.id} (username: {username})")
        await self.broadcast(
            json.dumps(
                {
                    "type": "chat",
                    "sender": "Server",
                    "message": f"{username} just left the chat!",
                }
            ),
            exclude=(websocket,),
        )

    async def on_receive(self, websocket: webshocket.ClientConnection, packet: Packet):
        username = websocket.session_state.get("_username", "Anonymous")
        message = str(packet.data).strip()  # Ensure it's a string before stripping
        logging.info(f"Received from {username}: {message}")

        if str(message).startswith("/"):  # Ensure message is string before startswith
            parts = str(message).split(" ", 2)  # Ensure message is string before split
            command = parts[0].lower()

            if command == "/join":
                if len(parts) == 2:
                    room_name = parts[1].lower()
                    if not room_name:
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "error",
                                    "message": "Room name cannot be empty.",
                                }
                            )
                        )
                        return

                    # Unsubscribe from all current channels
                    for subscribed_channel in list(websocket.subscribed_channel):
                        websocket.unsubscribe(channel=subscribed_channel)
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "info",
                                    "message": f"Leaving room '{subscribed_channel}'.",
                                }
                            )
                        )

                    websocket.subscribe(room_name)
                    await websocket.send(
                        json.dumps(
                            {"type": "info", "message": f"Joined room: '{room_name}'."}
                        )
                    )
                    logging.info(f"{username} joined room: {room_name}")
                else:
                    await websocket.send(
                        json.dumps(
                            {"type": "error", "message": "Usage: /join <room_name>"}
                        )
                    )

            elif command == "/msg":
                if len(parts) == 3:
                    target_username = parts[1]
                    private_message = parts[2]

                    target_websocket = None
                    for client_conn in self.clients:
                        if (
                            client_conn.session_state.get("_username")
                            == target_username
                        ):
                            target_websocket = client_conn
                            break

                    if target_websocket and target_websocket != websocket:
                        await target_websocket.send(
                            json.dumps(
                                {
                                    "type": "private_chat",
                                    "sender": username,
                                    "message": private_message,
                                }
                            )
                        )
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "info",
                                    "message": f"Message sent to {target_username}.",
                                }
                            )
                        )
                        logging.info(
                            f"Private message from {username} to {target_username}."
                        )
                    else:
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "error",
                                    "message": f"User '{target_username}' not found or cannot message self.",
                                }
                            )
                        )
                else:
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "error",
                                "message": "Usage: /msg <username> <message>",
                            }
                        )
                    )

            elif command == "/users":
                users = sorted(
                    [
                        client_conn.session_state["_username"]
                        for client_conn in self.clients
                        if "_username" in client_conn.session_state
                    ]
                )
                await websocket.send(
                    json.dumps(
                        {
                            "type": "info",
                            "message": f"Connected users: {', '.join(users)}",
                        }
                    )
                )
                logging.info(f"{username} requested user list.")

            elif command == "/rooms":
                active_rooms = sorted(
                    [room for room, clients in self.channels.items() if clients]
                )
                await websocket.send(
                    json.dumps(
                        {
                            "type": "info",
                            "message": f"Active rooms: {', '.join(active_rooms) if active_rooms else 'None'}",
                        }
                    )
                )
                logging.info(f"{username} requested room list.")

            elif command == "/help":
                help_message = (
                    "Available commands:\n"
                    "  /join <room_name> - Join or switch to a chat room.\n"
                    "  /msg <username> <message> - Send a private message to a user.\n"
                    "  /users - List all connected users.\n"
                    "  /rooms - List all active chat rooms.\n"
                    "  /help - Display this help message."
                )
                await websocket.send(
                    json.dumps({"type": "info", "message": help_message})
                )

            else:
                await websocket.send(
                    json.dumps(
                        {
                            "type": "error",
                            "message": f"Unknown command: {command}. Type /help for commands.",
                        }
                    )
                )
        else:
            # Regular chat message
            if websocket.subscribed_channel:
                channel = list(websocket.subscribed_channel)[
                    0
                ]  # Assuming one channel at a time for simplicity
                await self.publish(
                    channel=channel,
                    data=json.dumps(
                        {"type": "chat", "sender": username, "message": message}
                    ),
                    exclude=(
                        websocket,
                    ),  # Exclude sender from broadcast to avoid echo if client handles it
                )
                await websocket.send(
                    json.dumps({"type": "chat", "sender": username, "message": message})
                )  # Send back to sender for confirmation
                logging.info(f"Message from {username} in room '{channel}': {message}")
            else:
                # If not subscribed to any channel, broadcast to lobby or send error
                await self.broadcast(
                    json.dumps({"type": "chat", "sender": username, "message": message})
                )
                logging.info(f"Message from {username} (no room): {message}")


async def main() -> None:
    server = webshocket.websocket.server("127.0.0.1", 5000, clientHandler=clientHandler)
    await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
