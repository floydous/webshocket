"""Tests for webshocket.predicate — __repr__ on all predicate classes."""

from webshocket.predicate import Has, Is, IsEqual, Any as AnyPred, All as AllPred


def test_has_repr():
    assert repr(Has("admin")) == "Has('admin')"


def test_is_repr():
    assert repr(Is("vip")) == "Is('vip')"


def test_is_equal_repr():
    assert repr(IsEqual("role", "mod")) == "IsEqual('role', 'mod')"


def test_any_repr():
    assert repr(AnyPred(Has("a"), Is("b"))) == "Any(Has('a'), Is('b'))"


def test_all_repr():
    assert repr(AllPred(Has("x"), Is("y"))) == "All(Has('x'), Is('y'))"
