"""把在售商品换成中文名称，保留原商品 id 和行为记录。"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.models.tables import Category, Product

DATA = Path(__file__).resolve().parents[2] / "data" / "external" / "chinese_products.csv"
KEEP = ["手机数码", "家用电器", "服装鞋包", "食品饮料", "运动户外", "家居日用"]
CHINESE = re.compile(r"[\u4e00-\u9fff]")
ENGLISH_WORD = re.compile(r"[A-Za-z]{3,}")


def catalog() -> list[dict]:
    frame = pd.read_csv(DATA, encoding="utf-8-sig")
    rows = []
    for row in frame.itertuples(index=False):
        name = " ".join(str(row.name).split())
        category = str(row.category).strip()
        if category not in KEEP:
            raise SystemExit(f"类目不支持: {category}")
        if not CHINESE.search(name) or ENGLISH_WORD.search(name):
            raise SystemExit(f"商品名必须是中文: {name}")
        price = round(float(row.price), 2)
        if price <= 0:
            raise SystemExit(f"价格不合法: {name}")
        rows.append({"sku": str(row.sku).strip()[:64], "name": name[:128], "category": category, "price": price})
    skus = [row["sku"] for row in rows]
    if len(skus) != len(set(skus)):
        raise SystemExit("商品编号重复")
    if len(rows) < 8:
        raise SystemExit("中文商品过少")
    return rows


def apply() -> None:
    rows = catalog()
    db = SessionLocal()
    try:
        by_name = {row.name: row for row in db.query(Category).all()}
        for name in KEEP:
            if name not in by_name:
                category = Category(name=name)
                db.add(category)
                db.flush()
                by_name[name] = category
        products = db.query(Product).order_by(Product.id.asc()).all()
        for product in products:
            product.sku_code = f"TMP{product.id}"
        db.flush()
        for index, row in enumerate(rows):
            category_id = by_name[row["category"]].id
            if index < len(products):
                product = products[index]
                product.sku_code = row["sku"]
                product.name = row["name"]
                product.category_id = category_id
                product.price = row["price"]
                product.status = "ON"
            else:
                db.add(Product(
                    sku_code=row["sku"],
                    name=row["name"],
                    category_id=category_id,
                    price=row["price"],
                    status="ON",
                ))
        for product in products[len(rows):]:
            product.status = "OFF"
        used = {by_name[name].id for name in KEEP}
        for category in list(by_name.values()):
            if category.id not in used and db.query(Product).filter(Product.category_id == category.id).count() == 0:
                db.delete(category)
        db.commit()
        print(f"updated={min(len(products), len(rows))} inserted={max(0, len(rows) - len(products))} catalog={len(rows)}")
        for row in rows:
            print(f"{row['category']}\t{row['price']}\t{row['name']}")
    finally:
        db.close()


if __name__ == "__main__":
    apply()
