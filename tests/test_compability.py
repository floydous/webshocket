import msgspec
import pytest_asyncio
import pytest

import webshocket
import websockets
import json

from webshocket.enum import PacketSource


@pytest_asyncio.fixture
async def server():
    server = webshocket.WebSocketServer("localhost", 5000)
    await server.start()
    yield server
    await server.close()


@pytest.mark.asyncio
async def test_custom_packet(server: webshocket.WebSocketServer):
    async with websockets.connect("ws://localhost:5000") as client:
        connected_client = await server.accept()

        for packetSource_index in range(1, 6):
            source = PacketSource._value2member_map_[packetSource_index].name

            if source.lower() == "channel":
                continue

            data = json.dumps({"data": f"hello from {source}", "source": packetSource_index})
            await client.send(data)

            packet = await connected_client.recv()
            assert packet.data == "hello from %s" % source
            assert packet.source == PacketSource._value2member_map_[packetSource_index]


@pytest.mark.asyncio
async def test_trigger_rpc(server: webshocket.WebSocketServer):
    # async def test_trigger_rpc():
    data = {
        "rpc": {
            "type": "request",
            "method": "say_hello",
            "args": (args := [1, "2"]),
            "kwargs": (kwargs := {"first": "hello", "second": "world"}),
        },
        "source": 5,
    }

    @webshocket.rpc_method(alias_name="say_hello")
    async def packet_request(_, *args, **kwargs):
        return (args, kwargs)

    server.register_rpc_method(packet_request)

    async with websockets.connect("ws://localhost:5000") as client:
        await client.send(json.dumps(data))

        response = await client.recv()
        packet = msgspec.convert(
            obj=msgspec.json.decode(response),
            type=webshocket.Packet,
        )

        if isinstance(packet.rpc, webshocket.RPCResponse):
            assert packet.rpc.response == [args, kwargs]
            assert packet.source == PacketSource._value2member_map_[5]
        else:
            assert True is False
