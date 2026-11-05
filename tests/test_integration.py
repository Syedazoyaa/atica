"""Cross-module workflows (A-E) and configuration persistence."""
import os
import subprocess
import sys
from decimal import Decimal

import pytest

import atica
from atica import AticaConfig, Product
from atica.exceptions import ConfigurationError, UnknownProductError
from atica.inventory import PurchasingConfig, calculate_purchase_order
from atica.io import export_results, process_file
from atica.manufacturing import Material, calculate_material_requirement
from atica.packaging import breakdown
from atica.units import convert, register_unit


def test_workflow_a_physical_conversion():
    assert str(convert("2.5", "kg", "g")) == "2500 g"


def test_workflow_b_packaging(product_a):
    r = breakdown(product_a, 850, "carton", "pallet")
    assert (r.full_packages, r.remaining_quantity, r.packages_required) == (21, 10, 22)


def test_workflow_c_manufacturing_with_scrap_and_units():
    # target -> scrap-adjusted start quantity -> material -> converted to the purchasing unit
    register_unit("bag", "mass", "kg", 25)
    r = calculate_material_requirement(
        "0.5", 1000, "kg", scrap_rate="0.05", units_rounding="up", output_unit="bag", rounding="up"
    )
    assert r.metadata["units_to_process"] == 1053
    assert r.quantity == 22  # 526.5 kg = 21.06 bags


def test_workflow_d_purchasing_end_to_end(product_a):
    mat = Material("RESIN", "Resin", "kg", "0.5")
    need = mat.requirement(1000, scrap_rate="0.05", units_rounding="up")  # 526.5 kg
    register_unit("bag", "mass", "kg", 25)
    cfg = PurchasingConfig("SUP-1", "RESIN", "bag", "kg", minimum_order_quantity=10, order_multiple=5)
    order = calculate_purchase_order(cfg, need.quantity)
    assert order.quantity == 25 and order.unit == "bag"  # 21.06 -> 22 -> multiple of 5 -> 25
    assert order.metadata["stock_quantity"] == 625


def test_workflow_e_bulk(tmp_path, product_b):
    src = tmp_path / "in.csv"
    src.write_text("Product,Quantity,From Unit,To Unit\nProduct B,120,carton,pallet\nX,5,kg,g\nX,5,kg,m\n")
    bulk = process_file(src, products=[product_b])
    out = export_results(bulk, tmp_path / "out.csv")
    text = open(out, encoding="utf-8-sig").read()
    assert "2" in text and "5000" in text
    assert bulk.summary["failed"] == 1


def test_configuration_persistence_round_trip(tmp_path, product_a, product_b):
    cfg = AticaConfig()
    cfg.registry.register_unit("bag", "mass", "kg", 25)
    cfg.add_product(product_a)
    cfg.add_product(product_b)
    cfg.add_material(Material("RESIN", "Resin", "kg", "0.5", "0.02"))
    cfg.add_purchasing(PurchasingConfig("SUP", "PROD-A", "carton", "box", 2, 2))
    path = tmp_path / "config.json"
    cfg.save(path)
    loaded = AticaConfig.load(path)
    assert loaded.to_dict() == cfg.to_dict()
    assert loaded.registry.convert(2, "bag", "kg").output_quantity == 50
    assert breakdown(loaded.get_product("PROD-B"), 850, "carton", "pallet").full_packages == 17
    assert loaded.materials["RESIN"].wastage_rate == Decimal("0.02")
    # loaded config is independent of the original
    loaded.get_product("PROD-A").update_level("box", contains=1)
    assert product_a.get_level("box").contains == 12
    with pytest.raises(UnknownProductError):
        loaded.get_product("NOPE")
    assert not (tmp_path / "config.json.tmp").exists()


def test_configuration_rejects_bad_files(tmp_path):
    cfg = AticaConfig()
    good = cfg.to_dict()
    for data in (
        [], {"type": "nope"}, {**good, "schema_version": 99}, {**good, "schema_version": "1"},
        {**good, "products": "x"}, {**good, "products": [{"product_id": "P", "levels": [{"name": "a", "contains": 5}]}]},
        {**good, "materials": [{"material_id": "m"}]},
    ):
        with pytest.raises(ConfigurationError):
            AticaConfig.from_dict(data)  # includes a product whose base level contains 5: invalid hierarchy
    (tmp_path / "bad.json").write_text("{nope")
    with pytest.raises(ConfigurationError):
        AticaConfig.load(tmp_path / "bad.json")
    with pytest.raises(ConfigurationError):
        AticaConfig.load(tmp_path / "missing.json")
    # duplicate product ids
    dup = {**good, "products": [{"product_id": "P"}, {"product_id": "P"}]}
    with pytest.raises(ConfigurationError):
        AticaConfig.from_dict(dup)


def test_public_api_imports():
    for name in atica.__all__:
        assert hasattr(atica, name), name
    from atica.units import convert, register_unit  # noqa: F401
    from atica.packaging import Product, PackagingLevel, breakdown  # noqa: F401
    from atica.manufacturing import calculate_material_requirement  # noqa: F401
    from atica.inventory import calculate_purchase_quantity  # noqa: F401


def test_core_has_no_third_party_dependencies():
    """Importing the whole library must not pull in Pint, PySide6, pandas or openpyxl."""
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
    code = (
        "import sys; sys.path.insert(0, %r)\n" % src +
        "import atica, atica.units, atica.packaging, atica.manufacturing, atica.inventory, "
        "atica.io, atica.validation, atica.config\n"
        "bad = [m for m in ('pint', 'PySide6', 'pandas', 'openpyxl', 'numpy') if m in sys.modules]\n"
        "print(bad)\n"
        "sys.exit(1 if bad else 0)"
    )
    proc = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_no_mutation_of_inputs(product_a):
    before = product_a.to_dict()
    breakdown(product_a, 100, "carton", "pallet")
    Product.from_dict(product_a.to_dict())
    assert product_a.to_dict() == before
