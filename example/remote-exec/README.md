# Webshocket Remote Command Executor

This example demonstrates how to use the `webshocket` library to create a simple remote command execution system. A client sends commands to a server over a WebSocket connection, and the server executes these commands and sends the output back to the client.

## Setup

1.  **Ensure `webshocket` is installed:**
    This example assumes you have the `webshocket` library installed and accessible in your Python environment. If not, you might need to install it or ensure your `PYTHONPATH` includes the `src` directory of this project.

2.  **Navigate to the example directory:**
    ```bash
    cd example/webshocket-remote-exec
    ```

## How to Run

### 1. Start the Server

Open a terminal and run the server:

```bash
python server.py
```

The server will start listening on `ws://127.0.0.1:5000`. You should see a log message indicating that the server has started.

### 2. Start the Client

Open a **new** terminal and run the client:

```bash
python client.py
```

The client will attempt to connect to the server. Once connected, you will see a prompt `> ` where you can type commands.

### 3. Interact

Type any shell command (e.g., `ls`, `dir`, `echo Hello World`, `whoami`) at the `> ` prompt and press Enter. The command will be sent to the server, executed, and its output will be displayed in the client terminal.

To disconnect the client, type `exit` and press Enter.

**Example Interaction:**

```
# In server terminal:
INFO - Starting Webshocket Remote Command Executor server on ws://127.0.0.1:5000
INFO - Client connected: <client_id>
INFO - Received command from <client_id>: 'ls'
INFO - Sent response for command 'ls' to <client_id>

# In client terminal:
INFO - Connecting to Webshocket Remote Command Executor server at ws://127.0.0.1:5000
INFO - Connected to server. Type commands and press Enter. Type 'exit' to quit.
> ls
--- Command: ls
STDOUT:
client.py
README.md
server.py
Return Code: 0
---
> echo Hello from Webshocket!
--- Command: echo Hello from Webshocket!
STDOUT:
Hello from Webshocket!
Return Code: 0
---
> exit
INFO - Client disconnected.
```

## Security Note

This example demonstrates remote command execution for educational purposes. In a real-world application, exposing a server that executes arbitrary commands received from clients is a significant security risk and should be avoided unless robust authentication, authorization, and command sanitization mechanisms are in place.
