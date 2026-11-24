"""Generate docs/api-reference.md from the public API's signatures and docstrings.

Run from the repository root:  python docs/_generate_api.py
The reference is generated (not hand-written) so it always matches the code.
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
import pathlib
import sys

MODULES = [
    ("Units", "atica.units"),
    ("Packaging", "atica.packaging"),
    ("Materials and BOM", "atica.materials"),
    ("Production", "atica.production"),
    ("Quality", "atica.quality"),
    ("Purchasing", "atica.purchasing"),
    ("Core", "atica.core"),
    ("Integrations (CSV)", "atica.integrations.csv"),
    ("Integrations (Excel, optional)", "atica.integrations.excel"),
    ("Integrations (shared)", "atica.integrations"),
    ("Top-level shortcuts", "atica"),
]
EXTRA_MEMBERS = {
    "atica.integrations.csv": ["read_csv", "write_csv", "convert_csv", "read_bom_csv"],
    "atica.integrations.excel": ["read_xlsx", "write_xlsx", "convert_xlsx", "read_bom_xlsx"],
}


def signature(obj: object) -> str:
    try:
        return str(inspect.signature(obj))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "(...)"


def doc(obj: object) -> str:
    return inspect.cleandoc(inspect.getdoc(obj) or "").strip()


def public_names(module) -> list:  # type: ignore[no-untyped-def]
    names = list(getattr(module, "__all__", []))
    names += [n for n in EXTRA_MEMBERS.get(module.__name__, []) if n not in names]
    return [n for n in names if not n.startswith("_") and n != "validation"]


def render_function(name: str, fn: object, level: str = "###") -> str:
    return "%s `%s%s`\n\n%s\n" % (level, name, signature(fn), doc(fn) or "*(no description)*")


def render_class(name: str, cls: type) -> str:
    out = ["### class `%s%s`\n" % (name, signature(cls)), (doc(cls) + "\n") if doc(cls) else ""]
    if dataclasses.is_dataclass(cls):
        fields = [f for f in dataclasses.fields(cls) if not f.name.startswith("_")]
        if fields:
            out.append("Fields: " + ", ".join("`%s`" % f.name for f in fields) + "\n")
    methods = []
    for member_name, member in inspect.getmembers(cls):
        if member_name.startswith("_"):
            continue
        if inspect.isfunction(member) or isinstance(
            inspect.getattr_static(cls, member_name), (classmethod, staticmethod)
        ):
            if getattr(member, "__qualname__", "").split(".")[0] != cls.__name__:
                continue
            methods.append(member_name)
    for m in methods:
        out.append(
            "#### `%s.%s%s`\n\n%s\n"
            % (name, m, signature(getattr(cls, m)), doc(getattr(cls, m)) or "*(no description)*")
        )
    return "\n".join(out)


def main() -> None:
    root = pathlib.Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "src"))
    lines = [
        "# API reference\n",
        "*Generated from the source by `docs/_generate_api.py` - do not edit by hand.*\n",
        "Narrative guides with formulas and assumptions: [units](units.md), [packaging](packaging.md), [materials](materials.md), "
        "[production](production.md), [quality](quality.md), [purchasing](purchasing.md), [integrations](integrations.md), [core](core.md).\n",
    ]
    for title, module_name in MODULES:
        module = importlib.import_module(module_name)
        lines.append("\n## %s - `%s`\n" % (title, module_name))
        for name in public_names(module):
            obj = getattr(module, name)
            if inspect.isclass(obj):
                lines.append(render_class(name, obj))
            elif callable(obj):
                lines.append(render_function(name, obj))
    (root / "docs" / "api-reference.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote docs/api-reference.md")


if __name__ == "__main__":
    main()
