import aiomysql
import re
import logging

logger = logging.getLogger(__name__)

class MariaDBClient:
    def __init__(self, host, user, password, database, port=3306):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.pool = None

    async def connect(self, host=None, port=None):
        if self.pool is None:
            try:
                self.pool = await aiomysql.create_pool(
                    host=host or self.host,
                    user=self.user,
                    password=self.password,
                    db=self.database,
                    port=port or self.port,
                    autocommit=True,
                    connect_timeout=10,
                )
                logger.info("MariaDB connection pool created successfully")
            except Exception as e:
                logger.error(f"Failed to connect to MariaDB: {e}")
                self.pool = None

    async def disconnect(self):
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None
            logger.info("MariaDB connection pool closed")

    async def explain(self, query: str):
        if self.pool is None:
            return {"error": "Database connection not available"}
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(f"EXPLAIN {query}")
                    return await cur.fetchall()
        except Exception as e:
            logger.error(f"EXPLAIN failed: {e}")
            return {"error": str(e)}

    async def fetch_sample_rows(self, query: str, limit: int = 5):
        """Fetch sample rows from query safely (works with aggregates too)."""
        if self.pool is None:
            return {"error": "Database connection not available"}
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                try:
                    q = query.rstrip(";")

                    # If query already has LIMIT, run as is
                    if re.search(r"\blimit\b", q, re.IGNORECASE):
                        safe_query = q
                    else:
                        safe_query = f"SELECT * FROM ({q}) AS subq LIMIT {limit}"

                    await cur.execute(safe_query)
                    rows = await cur.fetchall()

                    if not rows:
                        return {"rows": [], "message": "Query returned no rows"}

                    # Clean up aggregate column names
                    cleaned_rows = []
                    for row in rows:
                        new_row = {}
                        for k, v in row.items():
                            clean_key = (
                                k.replace("COUNT(*)", "total_count")
                                .replace("SUM(", "sum_")
                                .replace(")", "")
                                .replace("AVG(", "avg_")
                                .replace("MAX(", "max_")
                                .replace("MIN(", "min_")
                                .replace("GROUP_CONCAT(", "group_concat_")
                                .replace("STDDEV(", "stddev_")
                                .replace("VARIANCE(", "variance_")
                            )
                            # fallback: lowercase & replace spaces
                            clean_key = re.sub(r"\W+", "_", clean_key).strip("_").lower()
                            new_row[clean_key] = v
                        cleaned_rows.append(new_row)

                    return {
                        "rows": cleaned_rows,
                        "message": f"Showing up to {limit} rows from actual query"
                    }

                except Exception as e:
                    logger.error(f"Sample row fetch failed: {e}")
                    return {"error": f"Sample row fetch failed: {str(e)}"}

    async def get_schema_context(self, query: str):
        """Extract table names from query and return schema details."""
        if self.pool is None:
            return {"error": "Database connection not available"}
        tables = self._extract_tables(query)
        schema = {}
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    for tbl in tables:
                        try:
                            await cur.execute(f"DESCRIBE {tbl}")
                            schema[tbl] = await cur.fetchall()
                        except Exception as e:
                            schema[tbl] = {"error": str(e)}
            return schema
        except Exception as e:
            logger.error(f"Schema context failed: {e}")
            return {"error": str(e)}

    async def get_full_schema(self):
        """Return full database schema overview via information_schema."""
        if self.pool is None:
            return {"error": "Database connection not available"}
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(
                        """
                        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_TYPE
                        FROM information_schema.columns
                        WHERE table_schema = DATABASE()
                        ORDER BY TABLE_NAME, ORDINAL_POSITION
                        """
                    )
                    rows = await cur.fetchall()
            tables = {}
            for r in rows:
                t = r["TABLE_NAME"]
                tables.setdefault(t, []).append(r)
            return tables
        except Exception as e:
            logger.error(f"Full schema fetch failed: {e}")
            return {"error": str(e)}

    def _extract_tables(self, query: str):
        """More tolerant regex-based table extractor: handles backticks, schema-qualified, subqueries/CTEs."""
        # matches from/join followed by optional schema and backticks, also in subqueries
        matches = re.findall(r"(?:from|join)\s+(`?[\w\.]+`?)", query, re.IGNORECASE)
        # Also check for CTEs: WITH cte AS (SELECT ... FROM table)
        cte_matches = re.findall(r"with\s+\w+\s+as\s*\(\s*select.*?\s+from\s+(`?[\w\.]+`?)", query, re.IGNORECASE | re.DOTALL)
        matches.extend(cte_matches)
        # Strip backticks
        cleaned = [m.replace("`", "") for m in matches]
        # Only table part if schema qualified
        return list(set(c.split(".")[-1] for c in cleaned if c))  # dedupe
