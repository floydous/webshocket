import pytest
from webshocket import WebSocketHandler, ClientConnection, rpc_method
from webshocket.predicate import Has, Is, IsEqual, Any, All
from typing import cast


class MockConnection:
    def __init__(self, state=None):
        self.session_state = state or {}
        self.connection_state = "CONNECTED"
        self.uid = "123"


def test_helpers():
    conn = MockConnection({"admin": True, "role": "editor", "active": False})
    conn = cast(ClientConnection, conn)  # type: ignore

    # IsEqual checks value
    assert IsEqual("admin", True)(conn)
    assert not IsEqual("admin", False)(conn)
    assert not IsEqual("missing", True)(conn)

    # Has checks existence
    assert Has("admin")(conn)
    assert not Has("missing")(conn)

    # Is checks truthiness
    assert Is("admin")(conn)
    assert not Is("active")(conn)
    assert not Is("missing")(conn)

    # Any (logical OR)
    assert Any(IsEqual("role", "admin"), IsEqual("role", "editor"))(conn)
    assert not Any(IsEqual("role", "admin"), IsEqual("role", "viewer"))(conn)

    # All (logical AND)
    assert All(Is("admin"), IsEqual("role", "editor"))(conn)
    assert not All(Is("admin"), Is("active"))(conn)


class MyHandler(WebSocketHandler):
    # Using IsEqual for value check
    @rpc_method(requires=IsEqual("admin", True))
    async def admin_only(self, _: ClientConnection):
        return "allowed"

    @rpc_method(requires=All(Is("login"), IsEqual("role", "user")))
    async def user_only(self, _: ClientConnection):
        return "allowed"


@pytest.mark.asyncio
async def test_rpc_requires_check():
    handler = MyHandler()

    assert getattr(handler.admin_only, "_is_rpc_method")
    requirement = getattr(handler.admin_only, "_restricted")

    conn_allowed = MockConnection({"admin": True})
    conn_denied = MockConnection({"admin": False})

    assert requirement(conn_allowed) is True
    assert requirement(conn_denied) is False
