from __future__ import annotations

from typing import Any, Dict, Callable
import re
import ast
import operator as op
import os

from .builtins import BUILTINS


def _normalize_simple_tokens(text: str) -> str:
    """Expand bare $var tokens into ${var} for downstream evaluation."""

    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        return f"${{{name}}}"

    # Skip ${...} tokens by ensuring the dollar isn't followed by {
    return re.sub(r"\$(?!\{)([A-Za-z_][A-Za-z0-9_]*)", repl, text)


_ALLOWED_BINOPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Mod: op.mod,
}

_ALLOWED_CMPOPS = {
    ast.Eq: op.eq,
    ast.NotEq: op.ne,
    ast.Lt: op.lt,
    ast.LtE: op.le,
    ast.Gt: op.gt,
    ast.GtE: op.ge,
}


def _safe_eval(node: ast.AST, ctx: Dict[str, Any]) -> Any:
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body, ctx)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return ctx.get(node.id)
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        return _ALLOWED_BINOPS[type(node.op)](_safe_eval(node.left, ctx), _safe_eval(node.right, ctx))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd, ast.Not)):
        val = _safe_eval(node.operand, ctx)
        if isinstance(node.op, ast.USub):
            return -val
        if isinstance(node.op, ast.UAdd):
            return +val
        return not val
    if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
        vals = [_safe_eval(v, ctx) for v in node.values]
        return all(vals) if isinstance(node.op, ast.And) else any(vals)
    if isinstance(node, ast.Compare):
        left = _safe_eval(node.left, ctx)
        for op_node, comp in zip(node.ops, node.comparators):
            fn = _ALLOWED_CMPOPS.get(type(op_node))
            if not fn:
                raise ValueError("Unsupported comparator")
            right = _safe_eval(comp, ctx)
            if not fn(left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.Call):
        func = _safe_eval(node.func, ctx)
        # Special-case ENV(NAME) where NAME is an identifier not present in ctx -> treat as string literal
        args: list[Any] = []
        for idx, a in enumerate(node.args):
            if (
                isinstance(node.func, ast.Name)
                and node.func.id == "ENV"
                and idx == 0
                and isinstance(a, ast.Name)
                and a.id not in ctx
            ):
                args.append(a.id)
            else:
                args.append(_safe_eval(a, ctx))
        kwargs = {kw.arg: _safe_eval(kw.value, ctx) for kw in node.keywords if kw.arg}
        return func(*args, **kwargs)
    if isinstance(node, ast.Attribute):
        val = _safe_eval(node.value, ctx)
        return getattr(val, node.attr)
    if isinstance(node, ast.Subscript):
        val = _safe_eval(node.value, ctx)
        sl = _safe_eval(node.slice, ctx)
        return val[sl]
    if isinstance(node, ast.Slice):
        lower = _safe_eval(node.lower, ctx) if node.lower else None
        upper = _safe_eval(node.upper, ctx) if node.upper else None
        step = _safe_eval(node.step, ctx) if node.step else None
        return slice(lower, upper, step)
    if isinstance(node, ast.Dict):
        return {_safe_eval(k, ctx): _safe_eval(v, ctx) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.List):
        return [_safe_eval(elt, ctx) for elt in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_safe_eval(elt, ctx) for elt in node.elts)
    raise ValueError("Unsupported expression in template")


def _render_text_without_jinja(text: str, ctx: Dict[str, Any]) -> str:
    # Only process ${...} tokens; leave any other braces untouched
    out: list[str] = []
    last = 0
    for m in re.finditer(r"\$\{([^{}]+)\}", text):
        out.append(text[last:m.start()])
        expr = m.group(1).strip()
        try:
            node = ast.parse(expr, mode="eval")
            val = _safe_eval(node, ctx)
        except Exception:
            val = ""
        out.append("" if val is None else str(val))
        last = m.end()
    out.append(text[last:])
    return "".join(out)


class TemplateEngine:
    def __init__(self) -> None:
        # Only support ${...} / $var dollar-style expressions
        self.env = None

    def render_value(self, value: Any, variables: Dict[str, Any], functions: Dict[str, Any] | None = None, envmap: Dict[str, Any] | None = None) -> Any:
        if isinstance(value, str):
            try:
                text = _normalize_simple_tokens(value)
                # Inject ENV function that reads from provided envmap or OS
                def ENV(name: str, default: Any = None) -> Any:  # noqa: N802 - uppercase by design
                    if envmap is not None and name in envmap:
                        return envmap.get(name)
                    return os.environ.get(name, default)

                dyn_funcs: Dict[str, Callable[..., Any]] = {"ENV": ENV}
                ctx: Dict[str, Any] = {**BUILTINS, **dyn_funcs, **(functions or {}), **variables}

                # If the whole string is a single ${...} token, evaluate and return the value with its native type
                single_token_match = re.fullmatch(r"\$\{([^{}]+)\}", text)
                if single_token_match:
                    expr = single_token_match.group(1).strip()
                    try:
                        node = ast.parse(expr, mode="eval")
                        return _safe_eval(node, ctx)
                    except Exception:
                        # Fall through to string rendering if evaluation fails
                        pass

                # multi-pass to resolve nested tokens inside strings, always producing a string
                cur = text
                for _ in range(3):
                    nxt = _render_text_without_jinja(cur, ctx)
                    if nxt == cur or "${" not in nxt:
                        cur = nxt
                        break
                    cur = nxt
                return cur
            except Exception:
                return value
        elif isinstance(value, dict):
            return {k: self.render_value(v, variables, functions, envmap) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.render_value(v, variables, functions, envmap) for v in value]
        else:
            return value

    def eval_expr(self, expr: str, variables: Dict[str, Any], functions: Dict[str, Any] | None = None, envmap: Dict[str, Any] | None = None, extra_ctx: Dict[str, Any] | None = None) -> Any:
        text = expr.strip()
        if text.startswith("${") and text.endswith("}"):
            text = text[2:-1]
        # Replace $name tokens to name, e.g., $request -> request
        text = re.sub(r"\$([A-Za-z_][A-Za-z0-9_]*)", r"\1", text)

        def ENV(name: str, default: Any = None) -> Any:  # noqa: N802
            if envmap is not None and name in envmap:
                return envmap.get(name)
            return os.environ.get(name, default)

        ctx: Dict[str, Any] = {**BUILTINS, **(functions or {}), **(variables or {}), **(extra_ctx or {}), "ENV": ENV}
        try:
            node = ast.parse(text, mode="eval")
            return _safe_eval(node, ctx)
        except Exception:
            return None
