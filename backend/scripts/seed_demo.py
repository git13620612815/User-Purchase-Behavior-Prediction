"""写入可训练的演示数据。普通用户密码 User12345。"""

from datetime import datetime, timedelta
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.tables import Behavior, Category, Product, User
from app.services.behavior_service import rebuild_stats

CATEGORIES = ["手机数码", "家用电器", "服装鞋包", "食品饮料", "美妆个护", "图书文具", "运动户外", "家居日用"]


def main() -> None:
    random.seed(7)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if db.query(Product).count():
        print("已有商品数据，跳过生成")
        db.close()
        return
    categories = []
    for name in CATEGORIES:
        row = Category(name=name)
        db.add(row)
        categories.append(row)
    db.flush()
    products = []
    for index, category in enumerate(categories):
        for seq in range(5):
            number = index * 5 + seq + 1
            product = Product(
                sku_code=f"P{number:03d}",
                name=f"{category.name}商品{seq + 1}",
                category_id=category.id,
                price=round(29 + number * 3.5, 2),
                status="ON",
            )
            db.add(product)
            products.append(product)
    db.flush()
    password = hash_password("User12345")
    users = []
    for index in range(1, 25):
        user = User(
            username=f"user{index:02d}",
            password_hash=password,
            nickname=f"用户{index:02d}",
            gender=random.choice(["男", "女", "未知"]),
            age=random.randint(18, 45),
            role="USER",
            status="ENABLED",
        )
        db.add(user)
        users.append(user)
    db.flush()
    start = datetime.now().replace(microsecond=0) - timedelta(days=50)
    for user in users:
        favorite_categories = random.sample(categories, 2)
        pool = [product for product in products if product.category_id in {item.id for item in favorite_categories}]
        moment = start + timedelta(hours=random.randint(0, 48))
        for _ in range(90):
            product = random.choice(pool if random.random() < 0.8 else products)
            moment += timedelta(hours=random.randint(3, 18))
            if moment >= datetime.now():
                break
            db.add(Behavior(user_id=user.id, product_id=product.id, behavior_type="browse", behavior_time=moment, source="IMPORT"))
            roll = random.random()
            if roll < 0.45:
                moment += timedelta(minutes=20)
                db.add(Behavior(user_id=user.id, product_id=product.id, behavior_type="favorite", behavior_time=moment, source="IMPORT"))
            if roll < 0.28:
                moment += timedelta(minutes=30)
                db.add(Behavior(user_id=user.id, product_id=product.id, behavior_type="cart", behavior_time=moment, source="IMPORT"))
            if roll < 0.16:
                moment += timedelta(hours=2)
                if moment < datetime.now():
                    db.add(Behavior(user_id=user.id, product_id=product.id, behavior_type="purchase", behavior_time=moment, source="IMPORT"))
    rebuild_stats(db)
    db.commit()
    print(f"users={len(users)} products={len(products)} behaviors={db.query(Behavior).count()}")
    db.close()


if __name__ == "__main__":
    main()
