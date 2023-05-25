#!/usr/bin/python

from __future__ import annotations
from typing import Callable, Dict, List
from beeprint import pp
import unittest


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

    def __eq__(self, o: T) -> bool:
        return self.node_id == o.node_id


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
    __match_args__ = ('ty', )

    def __init__(self, ty: Ty) -> None:
        super().__init__(-1)
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


class Binary(Expr):
    __match_args__ = ('left', 'right', )

    def __init__(self, left: Expr, right: Expr) -> None:
        super().__init__()
        self.left = left
        self.right = right


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
        self.paren_exprs: Dict[int, int] = {}

    def add_binding(self, name: str, ty: T):
        self.bindings[name] = ty

    def find_ty(self, name: str) -> T | None:
        if name in self.bindings:
            return self.bindings[name]

    def pop_unres(self, id: int):
        if id in self.unresolved:
            self.unresolved.pop(id)


def infer_types(fn: Fn, env: Env):
    for stmt in fn.stmts:
        match stmt:
            case Binding(name, ty, init):
                inf_ty: T = infer(env, init)
                if ty:
                    env.add_binding(name, Normal(ty))
                    unify(env, inf_ty, ty)
                else:
                    env.add_binding(name, inf_ty)
    if fn.last_expr:
        ty = infer(env, fn.last_expr)
        unify(env, ty, fn.ret_ty)


def infer(env: Env, expr: Expr) -> T:
    env.exprs[expr.node_id] = expr
    ty: T | None = None
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
        case Binary(left, right):
            env.paren_exprs[left.node_id] = expr.node_id
            env.paren_exprs[right.node_id] = expr.node_id
            t1 = infer(env, left)
            t2 = infer(env, right)
            if t1 != t2:
                match t1, t2:
                    case Normal(t01), Normal(t02):
                        assert t01 == t02, f"type-error: binary op `{t01}` and `{t02}`"
                        ty = t1
                    case Int(t01), Int(t02):
                        ty = Int(expr.node_id)
                    case Float(t01), Float(t02):
                        ty = Float(expr.node_id)
                    case(Normal(t01), (Int(_) | Float(_)) as e) | ((Int(_) | Float(_)) as e, Normal(t01)):
                        unify(env, e, t01)
                        ty = t1
                    case a, b:
                        assert False, f"{a}, {b}"
            else:
                ty = t1
        case _:
            assert False
    assert ty
    match ty:
        case Int() | Float():
            env.unresolved[expr.node_id] = ty
        case Normal(t):
            expr.ty = t
    return ty


def unify(env: Env, ty: T, expected: Ty):
    def f(_f: Callable):
        # expr = env.exprs[id]
        if _f(expected):
            for i, t in list(env.unresolved.items()):
                if t != ty:
                    continue
                iexpr = env.exprs[i]
                if i in env.paren_exprs:
                    p_id = env.paren_exprs[i]
                    pexpr = env.exprs[p_id]
                    pexpr.ty = expected
                    env.pop_unres(pexpr.node_id)
                    match pexpr:
                        case Binary(left, right):
                            left.ty = expected
                            env.pop_unres(left.node_id)
                            right.ty = expected
                            env.pop_unres(right.node_id)
                iexpr.ty = expected
                if i in env.binding_id:
                    env.bindings[env.binding_id[i]] = Normal(expected)
                    env.binding_id.pop(i)
                env.pop_unres(i)
            # expr.ty = expected
        else:
            assert False, f"type-error: expected `{expected}` but got `int`"

    match ty:
        case Int(id):
            f(Ty.is_int)
        case Float(id):
            f(Ty.is_float)
        case Normal(t):
            if t != expected:
                assert False, f"type-error: expected `{expected}` but got `{t}`"
            # if id in env.unresolved:
            #     unify(env, env.unresolved[id], expected)
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
        Binding("a", Ty("i32"), IntLit(20)),
        Binding("b", None, Ident("a")),
        Binding("c", None, Binary(IntLit(50), Ident("b"))),
    ], Ident("a"))

    env = Env()
    infer_types(fn, env)
    # for node_id, ty in env.unresolved.items():
    #     resolve(env, node_id, ty)
    # pp(fn)


class TestInfer(unittest.TestCase):
    def _recursive_check(self, expr: Expr, ty: Ty):
        self.assertEqual(expr.ty, ty)
        match expr:
            case Binary(left, right):
                self._recursive_check(left, ty)
                self._recursive_check(right, ty)

    def test_chained_infer(self):
        fn = Fn("test", Ty("i32"), [
            Binding("a", None, IntLit(20)),
            Binding("b", None, Ident("a")),
            Binding("c", None, Ident("b")),
            Binding("d", None, Binary(
                Binary(Ident("c"), IntLit(50)), Ident("a"))),
        ], Ident("a"))
        env = Env()
        infer_types(fn, env)
        assert fn.last_expr != None
        ty = Ty("i32")
        self._recursive_check(fn.last_expr, ty)
        stmts = fn.stmts
        for stmt in stmts:
            assert isinstance(stmt, Binding)
            self._recursive_check(stmt.init, ty)

    def test_shadow_binding(self):
        fn = Fn("test", Ty("i32"), [
            Binding("a", None, IntLit(20)),
            Binding("b", None, Ident("a")),
            Binding("b", None, Ident("b")),
        ], Ident("a"))
        env = Env()
        infer_types(fn, env)
        assert fn.last_expr != None
        ty = Ty("i32")
        self._recursive_check(fn.last_expr, ty)
        stmts = fn.stmts
        for stmt in stmts:
            assert isinstance(stmt, Binding)
            self._recursive_check(stmt.init, ty)

    def test_binary_exp(self):
        fn = Fn("test", Ty("i32"), [
            Binding("a", Ty("i32"), IntLit(20)),
            Binding("b", None, Ident("a")),
            Binding("c", None, Binary(IntLit(50), Ident("b"))),
        ], Ident("a"))
        env = Env()
        infer_types(fn, env)
        assert fn.last_expr != None
        ty = Ty("i32")
        self._recursive_check(fn.last_expr, ty)
        stmts = fn.stmts
        for stmt in stmts:
            assert isinstance(stmt, Binding)
            self._recursive_check(stmt.init, ty)

    def test_last_binding_return(self):
        fn = Fn("test", Ty("i32"), [
            Binding("a", None, IntLit(20)),
            Binding("b", None, Ident("a")),
            Binding("c", None, Binary(Ident("b"), IntLit(50))),
        ], Ident("c"))
        env = Env()
        infer_types(fn, env)
        assert fn.last_expr != None
        ty = Ty("i32")
        self._recursive_check(fn.last_expr, ty)
        stmts = fn.stmts
        for stmt in stmts:
            assert isinstance(stmt, Binding)
            self._recursive_check(stmt.init, ty)


if __name__ == "__main__":
    main()
    unittest.main()
