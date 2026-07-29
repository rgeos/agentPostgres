import os
import re
import json
from decimal import Decimal
import psycopg2


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder to safely handle PostgreSQL Decimal data types."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


class DatabaseManager:
    """Manages high-privilege configuration, table schemas, and permissions structural work."""

    def __init__(self):
        self.host = os.getenv("DB_HOST")
        self.db_name = os.getenv("DB_NAME")
        self.admin_user = os.getenv("DB_USER")
        self.admin_password = os.getenv("DB_PASSWORD")
        self.schema = os.getenv("TARGET_SCHEMA", "public_read_only")
        self.reader_user = os.getenv("LLM_READER_USER", "llm_reader")
        self.reader_password = os.getenv("LLM_READER_PASSWORD", "readonlypassword")

    def get_admin_connection(self):
        return psycopg2.connect(
            host=self.host,
            database=self.db_name,
            user=self.admin_user,
            password=self.admin_password,
        )

    def initialize_environment(self):
        """Creates custom schemas, activates fuzzy matching, and loads default data."""
        try:
            with self.get_admin_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

                    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema};")
                    cursor.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS {self.schema}.products (
                            id SERIAL PRIMARY KEY,
                            name VARCHAR(100),
                            price NUMERIC,
                            stock INT
                        );
                    """
                    )

                    cursor.execute(
                        f"CREATE INDEX IF NOT EXISTS idx_products_name_trgm ON {self.schema}.products USING gin (name gin_trgm_ops);"
                    )

                    cursor.execute(f"SELECT COUNT(*) FROM {self.schema}.products;")
                    if cursor.fetchone() == 0:
                        cursor.execute(
                            f"INSERT INTO {self.schema}.products (name, price, stock) VALUES ('Apple', 1.50, 150);"
                        )
                        cursor.execute(
                            f"INSERT INTO {self.schema}.products (name, price, stock) VALUES ('Laptop', 1200.00, 15);"
                        )
                        cursor.execute(
                            f"INSERT INTO {self.schema}.products (name, price, stock) VALUES ('Smartphone', 800.00, 42);"
                        )
                        cursor.execute(
                            f"INSERT INTO {self.schema}.products (name, price, stock) VALUES ('Headphones', 150.00, 100);"
                        )

                    cursor.execute(
                        f"SELECT 1 FROM pg_roles WHERE rolname='{self.reader_user}';"
                    )
                    if not cursor.fetchone():
                        cursor.execute(
                            f"CREATE USER {self.reader_user} WITH PASSWORD '{self.reader_password}';"
                        )

                    cursor.execute(
                        f"REVOKE ALL ON SCHEMA public FROM {self.reader_user};"
                    )

                    cursor.execute(
                        f"GRANT USAGE ON SCHEMA {self.schema} TO {self.reader_user};"
                    )
                    cursor.execute(
                        f"GRANT SELECT ON ALL TABLES IN SCHEMA {self.schema} TO {self.reader_user};"
                    )
                    cursor.execute(
                        f"ALTER DEFAULT PRIVILEGES IN SCHEMA {self.schema} GRANT SELECT ON TABLES TO {self.reader_user};"
                    )

                    conn.commit()
            print(
                f"Database initialized with fuzzy text lookup tools matching schema: '{self.schema}'"
            )
        except Exception as e:
            print(f"Database initialization lifecycle failure: {e}")


class DatabaseTool:
    """Safely validates, cleans, and routes read-only queries through restricted user logins."""

    def __init__(self):
        self.host = os.getenv("DB_HOST")
        self.db_name = os.getenv("DB_NAME")
        self.user = os.getenv("LLM_READER_USER", "llm_reader")
        self.password = os.getenv("LLM_READER_PASSWORD", "readonlypassword")
        self.forbidden_keywords = [
            "drop",
            "delete",
            "truncate",
            "update",
            "insert",
            "alter",
            "grant",
        ]

        raw_tables = os.getenv("ALLOWED_TABLES", "products,orders")
        self.allowed_tables = [t.strip() for t in raw_tables.split(",") if t.strip()]

        # we want deterministic answers
        try:
            self.seed = int(os.getenv("LLM_SEED", "0"))
        except ValueError:
            print("[WARN] LLM_SEED in .env is not a valid integer. Defaulting to 0.")
            self.seed = 0

    def get_connection(self):
        return psycopg2.connect(
            host=self.host,
            database=self.db_name,
            user=self.user,
            password=self.password,
        )

    def _sanitize_query(self, sql_query: str) -> str:
        cleaned = sql_query.strip()
        has_semicolon = cleaned.endswith(";")
        if has_semicolon:
            cleaned = cleaned[:-1]

        group_by_id_pattern = r"(?i)\s+group\s+by\s+([a-zA-Z0-9_\.]+)?\b(id)\b"
        if re.search(group_by_id_pattern, cleaned):
            print(
                f"[SQL SANITIZER] Intercepted primary key grouping clause inside: '{sql_query}'"
            )
            cleaned = re.sub(group_by_id_pattern, "", cleaned)
            select_id_comma_pattern = r"(?i)select\s+(\w+\.)?id\s*,\s*"
            cleaned = re.sub(select_id_comma_pattern, "SELECT ", cleaned)

        if has_semicolon:
            cleaned += ";"
        return cleaned

    def execute_read_query_raw(self, sql_query: str) -> list:
        """Executes query and returns a clean, native Python list object with serialized decimals."""
        sql_query = self._sanitize_query(sql_query)
        print(f"[TOOL EXECUTION] Processing query context: {sql_query}")

        if any(keyword in sql_query.lower() for keyword in self.forbidden_keywords):
            raise PermissionError(
                "Security Error: Prohibited operational structure string generated by LLM."
            )

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql_query)
                columns = [desc[0] for desc in cursor.description]
                results = cursor.fetchall()

                raw_records = [dict(zip(columns, row)) for row in results]
                json_str = json.dumps(raw_records, cls=DecimalEncoder)
                return json.loads(json_str)


class SchemaDiscoverer:
    """Queries system catalog records at runtime to auto-generate documentation for the LLM."""

    def __init__(self):
        self.db_tool = DatabaseTool()
        self.target_schema = os.getenv("TARGET_SCHEMA", "public_read_only")

    def get_active_schema_documentation(self) -> str:
        query = f"""
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = '{self.target_schema}'
            ORDER BY table_name, ordinal_position;
        """
        try:
            with self.db_tool.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    rows = cursor.fetchall()

            if not rows:
                return "Schema Status Notice: No accessible structural tables found."

            schema_map = {}
            for table, column, d_type in rows:
                if table not in schema_map:
                    schema_map[table] = []
                schema_map[table].append(f"{column} ({d_type})")

            doc_lines = ["Available Database Tables and Structural Columns:"]
            for table_name, columns in schema_map.items():
                col_string = ", ".join(columns)
                doc_lines.append(
                    f"- Table: {self.target_schema}.{table_name} -> Columns: [{col_string}]"
                )

            return "\n".join(doc_lines)

        except Exception as e:
            print(
                f"[SCHEMA DISCOVERER ERROR] Could not extract live documentation data: {e}"
            )
            # Fix column headers to perfectly mirror your live schema tables
            return f"- Table: {self.target_schema}.products -> Columns: [id (integer), product_name (character varying), product_price (numeric), stock_volume (integer)]"
