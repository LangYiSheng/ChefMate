from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

try:
    import pymysql
except ImportError:  # pragma: no cover
    pymysql = None


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SOURCE_DIR = BASE_DIR  /  "processor" / "workspace" / "approved"
ENV_FILE = BASE_DIR / ".env"


def load_dotenv_file() -> None:
    if not ENV_FILE.exists():
        return
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将审核通过的菜谱 JSON 导入 MySQL。")
    parser.add_argument("--source-dir", default=str(DEFAULT_SOURCE_DIR), help="审核通过 JSON 所在目录")
    parser.add_argument("--mode", choices=["replace", "skip"], default="replace", help="遇到同名菜谱时的处理方式")
    parser.add_argument("--limit", type=int, default=0, help="只导入前 N 条，0 表示全部")
    parser.add_argument("--dry-run", action="store_true", help="只检查数据，不写入数据库")
    return parser.parse_args()


def require_env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None or value == "":
        raise RuntimeError(f"缺少环境变量：{name}")
    return value


def connect_mysql():
    if pymysql is None:
        raise RuntimeError("未安装 pymysql，请先执行 `pip install pymysql`。")
    return pymysql.connect(
        host=require_env("MYSQL_HOST"),
        port=int(require_env("MYSQL_PORT", "3306")),
        user=require_env("MYSQL_USER"),
        password=require_env("MYSQL_PASSWORD"),
        database=require_env("MYSQL_DATABASE"),
        charset=os.environ.get("MYSQL_CHARSET", "utf8mb4"),
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
    )


def load_tag_mapping(conn) -> dict[tuple[str, str], int]:
    sql = """
        SELECT c.category_code, t.tag_name, t.id
        FROM recipe_tag t
        JOIN recipe_tag_category c ON c.id = t.category_id
        WHERE t.is_enabled = 1
    """
    with conn.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
    return {(row["category_code"], row["tag_name"]): row["id"] for row in rows}


def load_recipe_files(source_dir: Path, limit: int) -> list[Path]:
    files = sorted(path for path in source_dir.glob("*.json") if path.is_file())
    if limit > 0:
        return files[:limit]
    return files


def load_recipe_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_recipe_payload(data: dict[str, Any], tag_mapping: dict[tuple[str, str], int]) -> None:
    required_fields = [
        "name",
        "image_path",
        "description",
        "difficulty",
        "estimated_minutes",
        "servings",
        "tags",
        "ingredients",
        "steps",
        "tips",
    ]
    for field in required_fields:
        if field not in data:
            raise RuntimeError(f"缺少字段：{field}")

    if not isinstance(data["name"], str) or not data["name"].strip():
        raise RuntimeError("name 必须是非空字符串。")
    if data["image_path"] is not None and not isinstance(data["image_path"], str):
        raise RuntimeError("image_path 必须是字符串或 null。")
    if data["difficulty"] not in ["简单", "中等", "困难"]:
        raise RuntimeError("difficulty 不在固定集合中。")
    if not isinstance(data["estimated_minutes"], int) or data["estimated_minutes"] <= 0:
        raise RuntimeError("estimated_minutes 必须是正整数。")
    if not isinstance(data["servings"], int) or data["servings"] <= 0:
        raise RuntimeError("servings 必须是正整数。")
    if not isinstance(data["ingredients"], list) or not data["ingredients"]:
        raise RuntimeError("ingredients 不能为空。")
    if not isinstance(data["steps"], list) or not data["steps"]:
        raise RuntimeError("steps 不能为空。")
    if not isinstance(data["tips"], list):
        raise RuntimeError("tips 必须是数组。")

    tags = data["tags"]
    if not isinstance(tags, dict):
        raise RuntimeError("tags 必须是对象。")
    for category in ["flavor", "method", "scene", "health", "time", "tool"]:
        if category not in tags or not isinstance(tags[category], list):
            raise RuntimeError(f"tags.{category} 缺失或格式不正确。")
        for tag_name in tags[category]:
            if (category, tag_name) not in tag_mapping:
                raise RuntimeError(f"未在数据库标签字典中找到标签：{category}.{tag_name}")


def find_existing_recipe_id(conn, recipe_name: str) -> int | None:
    with conn.cursor() as cursor:
        cursor.execute("SELECT id FROM recipe WHERE name = %s ORDER BY id DESC LIMIT 1", (recipe_name,))
        row = cursor.fetchone()
    return row["id"] if row else None


def delete_recipe_by_id(conn, recipe_id: int) -> None:
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM recipe WHERE id = %s", (recipe_id,))


def insert_recipe(conn, data: dict[str, Any]) -> int:
    tips_text = "\n".join(tip.strip() for tip in data["tips"] if isinstance(tip, str) and tip.strip()) or None
    sql = """
        INSERT INTO recipe (
            name, image_path, description, difficulty, estimated_minutes, servings, tips, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'PUBLISHED')
    """
    values = (
        data["name"].strip(),
        data["image_path"],
        data["description"].strip(),
        data["difficulty"],
        data["estimated_minutes"],
        data["servings"],
        tips_text,
    )
    with conn.cursor() as cursor:
        cursor.execute(sql, values)
        return int(cursor.lastrowid)


def insert_ingredients(conn, recipe_id: int, ingredients: list[dict[str, Any]]) -> None:
    sql = """
        INSERT INTO recipe_ingredient (
            recipe_id, ingredient_name, amount_value, amount_text, unit, is_optional, purpose, sort_order
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    rows: list[tuple[Any, ...]] = []
    for index, ingredient in enumerate(ingredients, start=1):
        rows.append(
            (
                recipe_id,
                ingredient.get("name"),
                ingredient.get("amount_value"),
                ingredient.get("amount_text"),
                ingredient.get("unit"),
                1 if ingredient.get("optional", False) else 0,
                ingredient.get("purpose"),
                index,
            )
        )
    with conn.cursor() as cursor:
        cursor.executemany(sql, rows)


def insert_steps(conn, recipe_id: int, steps: list[dict[str, Any]]) -> None:
    sql = """
        INSERT INTO recipe_step (
            recipe_id, step_no, title, instruction, timer_seconds, notes
        ) VALUES (%s, %s, %s, %s, %s, %s)
    """
    rows: list[tuple[Any, ...]] = []
    for step in steps:
        rows.append(
            (
                recipe_id,
                step.get("step_no"),
                step.get("title"),
                step.get("instruction"),
                step.get("timer_seconds"),
                step.get("notes"),
            )
        )
    with conn.cursor() as cursor:
        cursor.executemany(sql, rows)


def insert_tag_maps(conn, recipe_id: int, tags: dict[str, list[str]], tag_mapping: dict[tuple[str, str], int]) -> None:
    sql = "INSERT INTO recipe_tag_map (recipe_id, tag_id) VALUES (%s, %s)"
    rows: list[tuple[int, int]] = []
    for category, tag_names in tags.items():
        for tag_name in tag_names:
            tag_id = tag_mapping[(category, tag_name)]
            rows.append((recipe_id, tag_id))
    with conn.cursor() as cursor:
        cursor.executemany(sql, rows)


def import_one_recipe(conn, path: Path, mode: str, dry_run: bool, tag_mapping: dict[tuple[str, str], int]) -> str:
    data = load_recipe_json(path)
    validate_recipe_payload(data, tag_mapping)

    existing_id = find_existing_recipe_id(conn, data["name"])
    if existing_id is not None:
        if mode == "skip":
            return "skipped"
        if not dry_run:
            delete_recipe_by_id(conn, existing_id)

    if dry_run:
        return "prepared"

    recipe_id = insert_recipe(conn, data)
    insert_ingredients(conn, recipe_id, data["ingredients"])
    insert_steps(conn, recipe_id, data["steps"])
    insert_tag_maps(conn, recipe_id, data["tags"], tag_mapping)
    return "imported"


def main() -> None:
    load_dotenv_file()
    args = parse_args()
    source_dir = Path(args.source_dir).resolve()
    if not source_dir.exists():
        raise RuntimeError(f"源目录不存在：{source_dir}")

    files = load_recipe_files(source_dir, args.limit)
    if not files:
        print("没有找到可导入的 JSON 文件。")
        return

    conn = connect_mysql()
    try:
        tag_mapping = load_tag_mapping(conn)
        imported = 0
        skipped = 0
        prepared = 0
        failed = 0

        for path in files:
            try:
                result = import_one_recipe(conn, path, args.mode, args.dry_run, tag_mapping)
                conn.commit()
                if result == "imported":
                    imported += 1
                    print(f"[IMPORTED] {path.name}")
                elif result == "prepared":
                    prepared += 1
                    print(f"[DRY-RUN] {path.name}")
                else:
                    skipped += 1
                    print(f"[SKIPPED] {path.name}")
            except Exception as exc:  # noqa: BLE001
                conn.rollback()
                failed += 1
                print(f"[FAILED] {path.name}: {exc}")

        print("")
        print("导入完成。")
        print(f"总文件数: {len(files)}")
        print(f"成功导入: {imported}")
        print(f"跳过数量: {skipped}")
        print(f"仅校验数量: {prepared}")
        print(f"失败数量: {failed}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
