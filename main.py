#!/usr/bin/python

from __future__ import annotations
from typing import Dict


class Ty:
    def __init__(self, ty: str) -> None:
        self.ty = ty

    def is_int(self) -> bool:
        match self.ty:
            case "i32" | "i64": return True
            case _: return False

    def __repr__(self) -> str:
        return self.ty

    def __eq__(self, o: Ty) -> bool:
        return o.ty == self.ty


class T:
    __match_args__ = ('node_id', )

    def __init__(self, node_id: int) -> None:
        self.node_id = node_id


class Int(T):
    __match_args__ = ('node_id', )

    def __init__(self, node_id: int) -> None:
        super().__init__(node_id)

    def __repr__(self) -> str:
        return f"int_{self.node_id}"


class Float(T):
    __match_args__ = ('node_id', )

    def __init__(self, node_id: int) -> None:
        super().__init__(node_id)

    def __repr__(self) -> str:
        return f"float_{self.node_id}"


class Normal(T):
    __match_args__ = ('node_id', 'ty', )

    def __init__(self, node_id: int, ty: Ty) -> None:
        super().__init__(node_id)
        self.ty = ty

    def __repr__(self) -> str:
        return f"{repr(self.ty)}"


bindings: Dict[str, T] = {
    "a": Int(0),
}

binding_id: Dict[int, str] = {
    1: "a"
}

unresolved: Dict[int, T] = {
    0: Int(0),  # lit: 20
    1: Int(1)  # ident: a
}


def unify(ty: T, expected: Ty):
    match ty:
        case Int(id):
            if expected.is_int():
                ty = Normal(id, expected)
                unresolved.pop(id)
                if id in binding_id:
                    unify(bindings[binding_id[id]], expected)
                    bindings[binding_id[id]] = ty
            else:
                assert False, f"type-error: expected `{expected}` but got `int`"
        case Normal(id, t):
            if t != expected:
                assert False, f"type-error: expected `{expected}` but got `{t}`"
            if id in unresolved:
                unify(unresolved[id], expected)
            else:
                assert False
        case _:
            assert False, "unreachable"


def main():
    unify(unresolved[1], Ty("i32"))
    print(unresolved, bindings)


if __name__ == "__main__":
    main()
