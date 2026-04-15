"""Tests for webshocket.connection — edge cases on ClientConnection."""


import pytest

from webshocket.connection import ClientConnection
from webshocket.enum import ClientType, ConnectionState, PacketSource
from webshocket.handler import DefaultWebSocketHandler, WebSocketHandler


class _FakeProtocol:
    """Minimal mock for WSTransport."""

    class underlying_transport:
        @staticmethod
        def get_extra_info(key):
            return ("127.0.0.1", 9999)

    def send(self, *a, **kw):
        pass

    def send_close(self, *a, **kw):
        pass

    def disconnect(self):
        pass


def _make_conn(handler=None, client_type=ClientType.FRAMEWORK):
    h = handler or DefaultWebSocketHandler()
    return ClientConnection(
        websocket_protocol=_FakeProtocol(),
        handler=h,
        client_type=client_type,
    )


@pytest.mark.asyncio
async def test_recv_disconnected_raises():
    """connection.py:210 — recv when DISCONNECTED and protocol is None raises ConnectionClosedError."""
    from webshocket.exceptions import ConnectionClosedError

    conn = _make_conn()
    object.__setattr__(conn, "connection_state", ConnectionState.DISCONNECTED)
    object.__setattr__(conn, "_protocol", None)
    with pytest.raises(ConnectionClosedError):
        await conn.recv()


@pytest.mark.asyncio
async def test_recv_non_default_handler_json_decode_error():
    """connection.py:223-227 — recv on non-default handler with GENERIC client falls back to UNKNOWN."""
    conn = _make_conn(handler=WebSocketHandler(), client_type=ClientType.GENERIC)
    await conn._payload_queue.put(b"not-valid-json!!!")

    pkt = await conn.recv(timeout=1.0)
    assert pkt.source == PacketSource.UNKNOWN
    assert pkt.data == b"not-valid-json!!!"


@pytest.mark.asyncio
async def test_recv_timeout_non_default_handler():
    """connection.py:235-236 — recv timeout on non-default handler raises ReceiveTimeoutError."""
    from webshocket.exceptions import ReceiveTimeoutError

    conn = _make_conn(handler=WebSocketHandler())
    with pytest.raises(ReceiveTimeoutError, match="timed out"):
        await conn.recv(timeout=0.05)


def test_subscribe_at_limit_returns_false():
    """connection.py:250 — subscribe returns False when at channel limit."""
    conn = _make_conn()
    object.__setattr__(conn, "max_subscribed_channels", 1)
    conn._handler.subscribe(conn, "ch1")
    assert conn.subscribe("ch2") is False


def test_getattr_protocol_fallthrough():
    """connection.py:299 — __getattr__ falls through to protocol attrs."""
    conn = _make_conn()
    assert conn.underlying_transport is not None


def test_delattr_session_state():
    """connection.py:306-309 — __delattr__ removes from session_state, or raises."""
    conn = _make_conn()
    conn.foo = "bar"
    assert conn.foo == "bar"
    del conn.foo

    with pytest.raises(AttributeError):
        _ = conn.foo

    with pytest.raises(AttributeError):
        del conn.nonexistent_key


def test_setitem_getitem():
    """connection.py:313, 322-326 — dict-style set/get access and KeyError."""
    conn = _make_conn()
    conn["mykey"] = 42
    assert conn["mykey"] == 42

    with pytest.raises(KeyError):
        _ = conn["no_such_key"]


def test_delitem():
    """connection.py:317 — dict-style deletion."""
    conn = _make_conn()
    conn["temp"] = "val"
    del conn["temp"]

    with pytest.raises(KeyError):
        _ = conn["temp"]


def test_repr():
    """connection.py:330 — __repr__."""
    conn = _make_conn()
    assert "ClientConnection" in repr(conn)


def test_eq_hash():
    """connection.py:338 — __eq__ with non-ClientConnection and __hash__."""
    conn = _make_conn()
    assert conn != "not-a-connection"
    assert hash(conn) == hash(conn._protocol)
