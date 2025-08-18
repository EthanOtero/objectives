import aiosqlite
import os
from pathlib import Path


class Database():
    async def get_last_id():
        async with Database.connection_obj.cursor() as cursor:
            await cursor.execute("SELECT objective_id FROM objectives ORDER BY objective_id DESC")
            result = await cursor.fetchone()
            try:
                last_id = int(result[0])
            except:
                last_id = None
            return last_id

    async def set_connection_obj(DB_path):
        DB_path = Path(DB_path)
        Database.connection_obj = await aiosqlite.connect(DB_path)

    async def create_tables(tables):
        async with Database.connection_obj.cursor() as cursor:
            for table in tables.values():
                table_name = table['name']
                values = []
                for key, value in table['values'].items(): 
                    values.append(f"{key} {value}")
                value_string = Database.SQL_format(values)
                command = f"CREATE TABLE IF NOT EXISTS {table_name} {value_string}"
                await cursor.execute(command)
        await Database.connection_obj.commit()
    
    async def update_database(table_name, column, column_value, condition, condition_value):
        async with Database.connection_obj.cursor() as cursor:
            await cursor.execute(f"UPDATE {table_name} SET {column} = ? WHERE {condition} = ?", (column_value, condition_value))
        await Database.connection_obj.commit()
    
    async def insert_into_database(table_name, columns, values):
        values = tuple(values) # change values into a tuple to execute the SQL command
        column_string = Database.SQL_format(columns)

        question_mark_list = []
        for value in values:
            question_mark_list.append("?")

        placeholder_string = Database.SQL_format(question_mark_list)

        async with Database.connection_obj.cursor() as cursor:
            await cursor.execute(f"INSERT INTO {table_name} {column_string} VALUES {placeholder_string}", values)
        await Database.connection_obj.commit()

    async def delete_database_value(table_name, condition, condition_value):
        async with Database.connection_obj.cursor() as cursor:
            await cursor.execute(f"DELETE FROM {table_name} WHERE {condition} = ?", (condition_value,))
        await Database.connection_obj.commit()

    def SQL_format(values, no_parentheses = False):
        if no_parentheses:
            value_string = ", ".join(values)
        else:
            value_string = f"({", ".join(values)})" # Formats values for SQL command
        return value_string
    
    