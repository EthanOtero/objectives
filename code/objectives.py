import time
from database import Database
import inspect
import asyncio

class Objective():
    objective_objects = {}
    def __init__(self, 
            name="Unnamed",
            description = "This object was not given a description. Oops!", 
            time_assigned = int(time.time()),
            time_due = None, 
            completion_status = False,
            point_value = 0,
            objective_id = 0,
            assigned_member_id = None,
            guild_id = None):
        
        self.name = name
        self.description = description
        self.time_assigned = time_assigned
        self.time_due = time_due
        self.completion_status = completion_status
        self.point_value = point_value
        self.objective_id = objective_id
        self.assigned_member_id = assigned_member_id
        self.guild_id = guild_id

    async def complete(self):
        self.completion_status = True
        completion_status = self.completion_status
        await Objective.db_update(column="completion_status", column_value=completion_status, condition="objective_id", condition_value=self.objective_id)

    async def delete(self):
        await Objective.db_delete(condition="objective_id", condition_value=self.objective_id)
        del Objective.objective_objects[self.objective_id]

    def assign_time_due(self, time_due):
        self.time_due = time_due

    
    
    async def assign(self, member_id, objective_id):
        """
        Assigns an objective to a member.
        Args:
            member_id: Discord id of the member to assign the objective to
        """
        self.assigned_member_id = member_id
        await self.db_update("member_id", self.assigned_member_id, "objective_id", objective_id)

    async def db_update(column, column_value, condition, condition_value):
        await Database.update_database("objectives", column, column_value, condition, condition_value)
    
    async def db_insert(columns, values):
        await Database.insert_into_database("objectives", columns, values)

    async def db_delete(condition, condition_value):
        await Database.delete_database_value("objectives", condition, condition_value)
    

    @staticmethod
    async def generate_objective_id():
        """
        Generates a new objective ID based on the last one entered in the database.
        """
        last_id = await Database.get_last_id()
        return (last_id + 1) if last_id is not None else 0
    
    @classmethod
    async def create(
        cls,
        name="Unnamed",
        description="This object was not given a description. Oops!",
        time_assigned=int(time.time()),
        time_due=None,
        completion_status=False,
        point_value=0,
        assigned_member_id=None,
        guild_id=None,
    ):

        new_id = await cls.generate_objective_id()
        new_instance = cls(
            name=name,
            description=description,
            time_assigned=time_assigned,
            time_due=time_due,
            completion_status=completion_status,
            point_value=point_value,
            assigned_member_id=assigned_member_id,
            objective_id=new_id,
            guild_id=guild_id
        )
        attrs = vars(new_instance)
        print(list(attrs.keys()))
        print(list(attrs.values()))
        await Objective.db_insert(list(attrs.keys()), list(attrs.values()))
        return new_instance

    async def get_all_objectives_from_member_id(member_id, showcompleted = False):
        async with Database.connection_obj.cursor() as cursor:
            if showcompleted:
                await cursor.execute("SELECT objective_id FROM objectives WHERE assigned_member_id = ? ORDER BY completion_status ASC", (member_id,))
            else:
                await cursor.execute("SELECT objective_id FROM objectives WHERE assigned_member_id = ? AND completion_status = ? ORDER BY completion_status ASC", (member_id,0))
            data = await cursor.fetchall()
            objective_list = []
            for objective_id in data:
                objective_id = objective_id[0]
                objective_list.append(await Objective.get_objective_from_id(objective_id))
            return objective_list
    
    async def get_objective_from_id(objective_id):
        objective_objects = Objective.objective_objects
        if objective_id in objective_objects:
            print("why this lowk work tho")
            return objective_objects[objective_id]
        objective = await Objective.create_objective_from_objective_id(objective_id)
        objective_objects[objective_id] = objective
        return objective
    
    async def create_objective_from_objective_id(objective_id):
        async with Database.connection_obj.cursor() as cursor:
            parameter_list = list(inspect.signature(Objective.__init__).parameters.keys()) # thanks to Paloha on StackOverflow!
            parameter_list = parameter_list[1:] # removes "self" from the results
            search_string = Database.SQL_format(parameter_list, no_parentheses=True)
            await cursor.execute(f"SELECT {search_string} FROM objectives WHERE objective_id = ?", (objective_id,))
            general_data = await cursor.fetchall()
            general_data = general_data[0]
            name, description, time_assigned, time_due, completion_status, point_value, objective_id, assigned_member_id, guild_id = general_data
            objective = Objective(name, description, time_assigned, time_due, completion_status, point_value, objective_id, assigned_member_id, guild_id)
            return objective
        
    async def convert_objective_name_to_objective_id(objective_name):
        async with Database.connection_obj.cursor() as cursor:
            await cursor.execute("SELECT objective_id FROM objectives WHERE name = ?", (objective_name,))
            data = await cursor.fetchone()
            return data[0]
    
    async def get_objective_from_objective_name(objective_name):
        async with Database.connection_obj.cursor() as cursor:
            objective_id = await Objective.convert_objective_name_to_objective_id(objective_name)
            objective = await Objective.get_objective_from_id(objective_id)
            return objective
        

# print(new_obj.completion_status)
# new_obj.complete()
# print(new_obj.completion_status)
# new_obj.assign_time_due(1754978963)
# print(new_obj.time_due)
# print(new_obj.point_value)