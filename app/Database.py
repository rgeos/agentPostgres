import os
import psycopg2


class DatabaseTool:
    def __init__(self):
        self.conn_string = os.getenv("DATABASE_URL", "postgres+psycopg2://postgres:password@localhost:5432/rag_database")
        self.forbidden_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "UPDATE", "INSERT"]

    def run_query(self, query: str) -> str:
        """
        Executes a read-only SQL query against the PostgreSQL database and returns results.
        Use this tool to fetch structural enterprise schemas, products stock, and transaction tables.

        :param query: A valid SQL query string.
        :return: string representation of rows or error message.
        """
        # Security Guardrail check
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

                    # Format as clean scannable text output
                    result = [dict(zip(columns, row)) for row in rows]
                    return str(result)
        except Exception as e:
            return f"Database Execution Error: {str(e)}"
