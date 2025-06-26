# Webshocket Chat Server Example

This example demonstrates a simple chat application using the `webshocket` library. It features a server that manages chat rooms and private messages, and a client that connects to the server, sends messages, and receives updates in real-time.

## Features

- **Public Chat:** Send messages to the current room.
- **Private Messaging:** Send direct messages to specific users.
- **Room Management:** Join and switch between different chat rooms.
- **User Listing:** View a list of all connected users.
- **Room Listing:** View a list of all active chat rooms.
- **Username Handling:** Clients provide a username upon connection, with checks for uniqueness.

## Setup

1.  **Ensure `webshocket` is installed:**
    This example assumes you have the `webshocket` library installed and accessible in your Python environment. If not, you might need to install it or ensure your `PYTHONPATH` includes the `src` directory of this project.

2.  **Navigate to the example directory:**
    ```bash
    cd example/chat-server
    ```

## How to Run

### 1. Start the Server

Open a terminal and run the server:

```bash
python server.py
```

The server will start listening on `ws://127.0.0.1:5000`. You should see log messages indicating server activity.

### 2. Start the Client(s)

Open one or more **new** terminals and run the client in each:

```bash
python client.py
```

Each client will prompt you to enter a unique username.

### 3. Interact

Once connected, you can use the following commands:

- **Send a public message:** Just type your message and press Enter. It will be sent to the room you are currently in.
- **Join a room:** `/join <room_name>` (e.g., `/join general`, `/join python-dev`)
- **Send a private message:** `/msg <username> <your_message>` (e.g., `/msg Alice Hello Alice!`)
- **List connected users:** `/users`
- **List active rooms:** `/rooms`
- **Get help:** `/help`
- **Exit:** Type `exit` and press Enter to disconnect.

**Example Interaction Flow:**

**Terminal 1 (Server):**

```
INFO - Starting Webshocket Chat Server on ws://127.0.0.1:5000
INFO - Client connected: <client_id_1> with username: Alice
INFO - Client connected: <client_id_2> with username: Bob
INFO - Received from Alice: /join dev
INFO - Alice joined room: dev
INFO - Message from Alice in room 'dev': Hello everyone!
INFO - Received from Bob: /users
INFO - Bob requested user list.
INFO - Received from Bob: /msg Alice Hi Alice!
INFO - Private message from Bob to Alice.
```

**Terminal 2 (Client - Alice):**

```
INFO - Connecting to WebSocket server...
INFO - Connected to WebSocket. Please enter your username:
Username: Alice
Server Info: Welcome, Alice! You are in 'lobby'. Type /help for commands.
[Server]: Alice just joined the chat!
Enter message or command (e.g., /help): /join dev
Server Info: Leaving room 'lobby'.
Server Info: Joined room: 'dev'.
Enter message or command (e.g., /help): Hello everyone!
[Alice]: Hello everyone!
[PRIVATE from Bob]: Hi Alice!
Enter message or command (e.g., /help):
```

**Terminal 3 (Client - Bob):**

```
INFO - Connecting to WebSocket server...
INFO - Connected to WebSocket. Please enter your username:
Username: Bob
Server Info: Welcome, Bob! You are in 'lobby'. Type /help for commands.
[Server]: Bob just joined the chat!
[Server]: Alice just joined the chat!
Enter message or command (e.g., /help): /users
Server Info: Connected users: Alice, Bob
Enter message or command (e.g., /help): /msg Alice Hi Alice!
Server Info: Message sent to Alice.
Enter message or command (e.g., /help):
```
