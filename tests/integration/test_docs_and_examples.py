"""Documentation must not lie: examples, README/docs code blocks and docstring examples all run."""

import doctest
import importlib
import os
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
ENV = dict(os.environ, PYTHONPATH=str(ROOT / "src") + os.pathsep + os.environ.get("PYTHONPATH", ""))


def run(code_or_path, *, is_file=False, cwd=None):
    args = [sys.executable, str(code_or_path)] if is_file else [sys.executable, "-c", code_or_path]
    return subprocess.run(args, capture_output=True, text=True, env=ENV, cwd=cwd, timeout=120)


@pytest.mark.parametrize("example", sorted((ROOT / "examples").glob("*.py")), ids=lambda p: p.name)
def test_example_runs(example):
    out = run(example, is_file=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip()


def _blocks():
    files = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]
    for path in files:
        if path.name == "api-reference.md":
            continue
        text = path.read_text(encoding="utf-8")
        for index, match in enumerate(re.finditer(r"```python\n(.*?)```", text, re.S)):
            yield pytest.param(match.group(1), id="%s#%d" % (path.name, index + 1))


@pytest.mark.parametrize("code", _blocks())
def test_documentation_code_block_runs(code, tmp_path):
    out = run(code, cwd=tmp_path)
    assert out.returncode == 0, out.stderr + "\n" + code


# Output shown in comments of the README quick-start must be what the code really prints.
README_EXPECTATIONS = [
    ("from atica.units import convert\nprint(convert(25, 'kg', 'g'))", "25000 g"),
    ("from atica.units import convert\nprint(convert('212', 'F', 'C'))", "100 C"),
    (
        "from atica.packaging import *\n"
        "p = Product('P', 'A', levels=[PackagingLevel('piece'), PackagingLevel('box', 12, 'piece'), PackagingLevel('carton', 20, 'box')])\n"
        "print(breakdown(p, 250, 'piece', 'carton'))",
        "250 piece = 1 full carton + 10 piece remaining (2 carton required)",
    ),
    (
        "from atica.materials import *\n"
        "bom = Bom([BomItem('steel', '0.25', 'kg'), BomItem('paint', '40', 'mL', wastage_percent=10)])\n"
        "print(calculate_bom_requirements(bom=bom, production_quantity=1000, scrap_percent=5)['steel'])",
        "263.1578947368 kg",
    ),
    (
        "from atica.quality import calculate_required_input\nprint(calculate_required_input(950, scrap_percent=5))",
        "1000",
    ),
]


@pytest.mark.parametrize("code, expected", README_EXPECTATIONS)
def test_readme_outputs_are_accurate(code, expected):
    out = run(code)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == expected
    published = "\n".join(
        p.read_text(encoding="utf-8") for p in [ROOT / "README.md", *(ROOT / "docs").glob("*.md")]
    )
    assert expected in published  # the documented output is exactly what the code prints


DOCTEST_MODULES = [
    "atica",
    "atica.core.precision",
    "atica.core.rounding",
    "atica.units",
    "atica.units.registry",
    "atica.packaging",
    "atica.packaging.breakdown",
    "atica.materials",
    "atica.materials.bom",
    "atica.materials.material",
    "atica.production",
    "atica.production.batches",
    "atica.production.time",
    "atica.production.capacity",
    "atica.quality",
    "atica.quality.scrap",
    "atica.quality.yields",
    "atica.quality.wastage",
    "atica.purchasing",
    "atica.purchasing.calculations",
]


@pytest.mark.parametrize("name", DOCTEST_MODULES)
def test_docstring_examples(name):
    module = importlib.import_module(name)
    result = doctest.testmod(module, optionflags=doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE)
    assert result.failed == 0


def test_api_reference_is_current():
    """docs/api-reference.md is generated; regenerating must not change it."""
    if sys.version_info[:2] != (3, 12):
        pytest.skip(
            "the reference is generated with Python 3.12 (signature rendering differs slightly by version)"
        )
    before = (ROOT / "docs" / "api-reference.md").read_text(encoding="utf-8")
    out = run(str(ROOT / "docs" / "_generate_api.py"), is_file=True)
    assert out.returncode == 0, out.stderr
    assert (ROOT / "docs" / "api-reference.md").read_text(encoding="utf-8") == before


def test_every_public_function_is_documented():
    """Each exported callable has a docstring, and appears in the narrative docs."""
    import inspect

    docs = "\n".join(
        p.read_text(encoding="utf-8") for p in (ROOT / "docs").glob("*.md") if p.name != "api-reference.md"
    )
    missing = []
    for module_name in (
        "atica.units",
        "atica.packaging",
        "atica.materials",
        "atica.production",
        "atica.quality",
        "atica.purchasing",
    ):
        module = importlib.import_module(module_name)
        for name in module.__all__:
            obj = getattr(module, name)
            if not (inspect.isfunction(obj) or inspect.isclass(obj)):
                continue
            if not inspect.getdoc(obj):
                missing.append(module_name + "." + name + " (docstring)")
            if inspect.isfunction(obj) and name not in docs:
                missing.append(module_name + "." + name + " (docs)")
    assert not missing, missing
