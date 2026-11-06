import os
import psycopg2


class DatabaseTool:
    def __init__(self):
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "postgres")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "rag_database")

        self.conn_string = os.getenv(
            "DATABASE_URL",
            f"postgres+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}",
        )
        self.forbidden_keywords = [
            "DROP",
            "DELETE",
            "TRUNCATE",
            "ALTER",
            "UPDATE",
            "INSERT",
        ]

    def verify_connection(self, timeout: int = 5) -> dict:
        """
        Verifies database connectivity before agent operations.
        Safe to call before run_query to ensure agent can access the database.

        :param timeout: Connection timeout in seconds (default: 5).
        :return: dict with 'status' (bool), 'message' (str), and 'database_version' (str or None).
        """
        try:
            with psycopg2.connect(self.conn_string, connect_timeout=timeout) as conn:
                with conn.cursor() as cursor:
                    # Execute minimal query to verify connectivity
                    cursor.execute("SELECT version();")
                    version = cursor.fetchone()[0]

            return {
                "status": True,
                "message": "Database connection verified successfully.",
                "database_version": version,
            }
        except psycopg2.OperationalError as e:
            return {
                "status": False,
                "message": f"Database connection failed: {str(e)}",
                "database_version": None,
            }
        except psycopg2.DatabaseError as e:
            return {
                "status": False,
                "message": f"Database error during verification: {str(e)}",
                "database_version": None,
            }
        except Exception as e:
            return {
                "status": False,
                "message": f"Unexpected error verifying database connection: {str(e)}",
                "database_version": None,
            }

    def run_query(self, query: str) -> str:
        """
        Executes a read-only SQL query against the PostgreSQL database and returns results.
        Use this tool to fetch structural enterprise schemas, products stock, and transaction tables.

        :param query: A valid SQL query string.
        :return: string representation of rows or error message.
        """
        if any(keyword in query.upper() for keyword in self.forbidden_keywords):
            return "Error: Security violation. Query contains forbidden modification keywords."

        try:
            with psycopg2.connect(self.conn_string) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()

                    if not rows:
                        return "Query executed successfully. No records returned."

                    result = [dict(zip(columns, row)) for row in rows]
                    return str(result)
        except Exception as e:
            return f"Database Execution Error: {str(e)}"
