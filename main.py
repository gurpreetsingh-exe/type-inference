#!/usr/bin/python

from __future__ import annotations
from typing import Callable, Dict, List
from beeprint import pp


class Ty:
    def __init__(self, ty: str) -> None:
        self.ty = ty

    def is_int(self) -> bool:
        match self.ty:
            case "i32" | "i64": return True
            case _: return False

    def is_float(self) -> bool:
        match self.ty:
            case "f32" | "f64": return True
            case _: return False

    def __repr__(self) -> str:
        return f"\033[1;32m{self.ty}\033[0m"

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

######################################################


node_id = 0


def gen_node_id() -> int:
    global node_id
    node_id += 1
    return node_id


class Stmt:
    pass


class Expr(Stmt):
    def __init__(self) -> None:
        self.node_id = gen_node_id()
        self.ty: Ty | None = None


class IntLit(Expr):
    def __init__(self, value: int):
        super().__init__()
        self.value = value


class FloatLit(Expr):
    def __init__(self, value: float):
        super().__init__()
        self.value = value


class Ident(Expr):
    __match_args__ = ('name', )

    def __init__(self, name: str):
        super().__init__()
        self.name = name


class Binding(Stmt):
    __match_args__ = ('name', 'ty', 'init')

    def __init__(self, name: str, ty: Ty | None, init: Expr) -> None:
        self.name = name
        self.init = init
        self.ty = ty


class Fn:
    __match_args__ = ('name', 'ret_ty', 'stmts', 'last_expr')

    def __init__(self, name: str, ret_ty: Ty, stmts: List[Stmt], last_expr: Expr | None):
        self.name = name
        self.ret_ty = ret_ty
        self.stmts = stmts
        self.last_expr = last_expr


class Env:
    def __init__(self, parent: Env | None = None) -> None:
        self.parent = parent
        self.bindings: Dict[str, T] = {}
        self.binding_id: Dict[int, str] = {}
        self.unresolved: Dict[int, T] = {}
        self.exprs: Dict[int, Expr] = {}

    def add_binding(self, name: str, ty: T):
        self.bindings[name] = ty

    def find_ty(self, name: str) -> T | None:
        if name in self.bindings:
            return self.bindings[name]


def infer_types(fn: Fn, env: Env):
    for stmt in fn.stmts:
        match stmt:
            case Binding(name, ty, init):
                inf_ty: T = infer(env, init)
                if ty:
                    env.add_binding(name, Normal(init.node_id, ty))
                    unify(env, inf_ty, ty)
                else:
                    env.add_binding(name, inf_ty)
    if fn.last_expr:
        ty = infer(env, fn.last_expr)
        unify(env, ty, fn.ret_ty)


def infer(env: Env, expr: Expr) -> T:
    env.exprs[expr.node_id] = expr
    ty = None
    match expr:
        case IntLit():
            ty = Int(expr.node_id)
        case FloatLit():
            ty = Float(expr.node_id)
        case Ident(name):
            env.binding_id[expr.node_id] = name
            ty = env.find_ty(name)
            if not ty:
                assert False, f"`{name}` not found in this scope"
        case _:
            assert False
    assert ty != None
    match ty:
        case Int() | Float():
            env.unresolved[expr.node_id] = ty
        case Normal(_, t):
            expr.ty = t
    return ty


def unify(env: Env, ty: T, expected: Ty):
    def f(id: int, _f: Callable):
        # expr = env.exprs[id]
        if _f(expected):
            for i, t in list(env.unresolved.items()):
                if t != ty:
                    continue
                iexpr = env.exprs[i]
                iexpr.ty = expected
                if i in env.binding_id:
                    env.bindings[env.binding_id[i]] = Normal(id, expected)
                    env.binding_id.pop(i)
                env.unresolved.pop(i)
            # expr.ty = expected
        else:
            assert False, f"type-error: expected `{expected}` but got `int`"

    match ty:
        case Int(id):
            f(id, Ty.is_int)
        case Float(id):
            f(id, Ty.is_float)
        case Normal(id, t):
            if t != expected:
                assert False, f"type-error: expected `{expected}` but got `{t}`"
            if id in env.unresolved:
                unify(env, env.unresolved[id], expected)
        case _:
            assert False, "unreachable"


def resolve(env: Env, id: int, ty: T):
    def f(t):
        expr = env.exprs[id]
        expr.ty = t
    match ty:
        case Int(_):
            f(Ty("i64"))
        case Float(_):
            f(Ty("f64"))
        case Normal(): assert False


def main():
    fn = Fn("test", Ty("i32"), [
        Binding("a", None, IntLit(20)),
        Binding("b", None, Ident("a")),
        Binding("c", None, Ident("b")),
        Binding("e", None, Ident("c")),
        Binding("d", None, FloatLit(20.20)),
    ], Ident("a"))
    env = Env()
    infer_types(fn, env)
    for node_id, ty in env.unresolved.items():
        resolve(env, node_id, ty)
    pp(fn)


if __name__ == "__main__":
    main()
