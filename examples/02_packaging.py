"""Packaging: 1 carton = 20 boxes, 1 box = 12 pieces; what does 250 pieces make?"""

from atica.packaging import PackagingLevel, Product, breakdown, decompose

product = Product(
    "P001",
    "Product A",
    levels=[
        PackagingLevel("piece"),
        PackagingLevel("box", 12, "piece"),
        PackagingLevel("carton", 20, "box"),
    ],
)

r = breakdown(product, 250, "piece", "carton")
print(r)  # 250 piece = 1 full carton + 10 piece remaining (2 carton required)
assert (int(r.full_packages), int(r.remainder), int(r.packages_required)) == (1, 10, 2)

plan = decompose(product, 250)
print({name: int(count) for name, count in plan.by_level().items()})  # {'carton': 1, 'box': 0, 'piece': 10}

# Products are immutable: adding a level returns a new product.
bigger = product.with_level(PackagingLevel("pallet", 40, "carton"))
print(product.level_names, "->", bigger.level_names)
