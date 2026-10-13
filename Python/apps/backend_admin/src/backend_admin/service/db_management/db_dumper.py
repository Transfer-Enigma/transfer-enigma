from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TABLES = {"drop", "service_prices", "prices", "routes", "companies", "containers", "points", "services"}


async def create_db_dump(session: AsyncSession, structure: bool, all_tables: bool = False):
    yield "SET FOREIGN_KEY_CHECKS = 0;\n\n"

    tables_descriptor = (await session.execute(text("SHOW TABLES"))).scalars() if all_tables else TABLES

    for table in tables_descriptor:
        if table == "alembic_version":
            continue

        if structure:
            table_structure_descriptor = (await session.execute(text(f"SHOW CREATE TABLE `{table}`"))).fetchone()[1]
            tables_descriptor = table_structure_descriptor.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ", 1)
            yield f"{tables_descriptor};\n\n"

        table_data_rows = (await session.execute(text(f"SELECT * FROM `{table}`"))).fetchall()

        if table_data_rows:
            columns = (await session.execute(text(f"DESCRIBE `{table}`"))).scalars()

            values_list = []
            for row in table_data_rows:
                row_values = []
                for value in row:
                    if value is None:
                        row_values.append("NULL")
                    elif isinstance(value, (int, float)):
                        row_values.append(str(value))
                    else:
                        escaped = str(value).replace("\\", "\\\\").replace("'", "''")
                        row_values.append(f"'{escaped}'")

                values_list.append(f"({', '.join(row_values)})")

            if values_list:
                columns_str = ', '.join([f"`{col}`" for col in columns])
                values_str = ',\n    '.join(values_list)
                insert_sql = f"INSERT INTO `{table}` ({columns_str}) VALUES\n    {values_str};\n\n"
                yield insert_sql

        yield "\n"

    yield "\n\nSET FOREIGN_KEY_CHECKS = 1;"
