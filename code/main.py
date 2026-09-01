import nextcord
from nextcord.ext import commands
import aiosqlite
import dotenv
import os
import json
import asyncio
from typing import Optional
from datetime import datetime

from database import Database
from objectives import Objective

JSON_PATH = "tables.json"

with open(JSON_PATH) as f:
    tables = json.load(f)

intents = nextcord.Intents.all()
intents.members = True

secrets = dotenv.load_dotenv(dotenv_path="secrets.env")
TOKEN = os.getenv("TOKEN")
OWNER_ROLE_ID = os.getenv("OWNER_ROLE_ID")
DB_PATH = os.getenv("DB_PATH")
bot = commands.Bot(intents=intents)


class ContactOptions(nextcord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @nextcord.ui.button(label='Request Completion', style=nextcord.ButtonStyle.green, emoji="✅")
    async def confirm(self, button: nextcord.ui.Button, ctx: nextcord.Interaction):
        self.value = "Complete"
        self.stop()

    @nextcord.ui.button(label='Request Clarification', style=nextcord.ButtonStyle.gray, emoji="❓")
    async def cancel(self, button: nextcord.ui.Button, ctx: nextcord.Interaction):
        self.value = "Clarify"
        self.stop()

async def check_member_for_data(member: nextcord.Member):
    async with Database.connection_obj.cursor() as cursor:
        await cursor.execute("SELECT points, guild_id FROM members WHERE member_id = ? AND guild_id = ?", (member.id, member.guild.id,))
        data = await cursor.fetchone()
        if not data:
            await cursor.execute("INSERT INTO members (member_id, guild_id, points, tasks_completed) VALUES (?, ?, ?, ?)", (member.id, member.guild.id, 0, 0))
        try:

            points = data[0]
            tasks_completed = data[1]

            if str(points) == "None" or str(tasks_completed) == "None":
                await cursor.execute("UPDATE members SET points = ?, tasks_completed = ? WHERE member_id = ? AND guild_id = ?", (0, 0, member.id, member.guild.id,))
        except TypeError:
            await cursor.execute("UPDATE members SET points = ?, tasks_completed = ? WHERE member_id = ? AND guild_id = ?", (0, 0, member.id, member.guild.id,))
    await Database.connection_obj.commit()

def date_to_unix(date):   
    month, day, year = date.split("/")
    if len(month) == 1:
        month = "0" + month
    if len(day) == 1:
        day = "0" + day
    date = f"{month}/{day}/{year}"
    if len(year) == 2:
        epoch = datetime.strptime(date, "%m/%d/%y").timestamp()
    else:
        epoch = datetime.strptime(date, "%m/%d/%Y").timestamp()
    return int(epoch)

@bot.event
async def on_ready():
    await Database.set_connection_obj(DB_PATH)
    await Database.create_tables(tables)
    print(f"Objectives is now online in {len(bot.guilds)} servers!")

@bot.slash_command()
async def objective(interaction: nextcord.Interaction):
    pass

@bot.slash_command(description="[ADMIN] Create an objective!", default_member_permissions=nextcord.Permissions(administrator=True))
async def create(interaction: nextcord.Interaction, 
                 name: Optional[str] = nextcord.SlashOption(name='name', description='Name for the objective.'), 
                 description: Optional[str] = nextcord.SlashOption(name='description', description='Description of the objective.'), 
                 time_due: Optional[str] = nextcord.SlashOption(name='timedue', description='Due date for the objective (in format Month/Day/Year).'), 
                 point_value: Optional[int] = nextcord.SlashOption(name='pointvalue', description='Point value of the objective.'), 
                 assigned_member: Optional[nextcord.Member] = nextcord.SlashOption(name='assignedmember', description='Member to assign to the objective.'),
                 assigned_channel: Optional[nextcord.TextChannel] = nextcord.SlashOption(name='channel', description="Channel to send the objective to."),
                 ):
    if time_due:
        time_due = date_to_unix(time_due)
    assigned_member_id = assigned_member.id if assigned_member else None
    new_obj = await Objective.create(name=name, description=description, time_due=time_due, point_value=point_value, assigned_member_id=assigned_member_id, guild_id=interaction.guild.id)
    em = nextcord.Embed(
            title=new_obj.name, color=nextcord.Color(int("999999", 16)))
    if point_value and point_value > 0:
        em.add_field(name=new_obj.description,
                        value=f"Worth {new_obj.point_value} points!", inline=False)
    else:
        em.add_field(name=new_obj.description, value="​", inline=False)
    em.add_field(name='​',
                    value=f"Assigned <t:{new_obj.time_assigned}:D>; due <t:{new_obj.time_due}:D>.")
    if assigned_channel:
        await assigned_member.send(f"{assigned_member.mention}: You've just been assigned a new objective in `{assigned_member.guild.name}`! -> {assigned_channel.mention}", embed=em)
    else:
        await assigned_member.send(f"{assigned_member.mention}: You've just been assigned a new objective in `{assigned_member.guild.name}`!", embed=em)
    view = ContactOptions()
    await assigned_channel.send(f"{assigned_member.mention}", embed=em)
    return await interaction.send(f"Objective `{name}` has been created!", ephemeral=True)

@objective.subcommand(description="List all currently assigned objectives.")
async def list(interaction: nextcord.Interaction, showcompleted: Optional[bool] = nextcord.SlashOption(name='showcompleted', description='Show completed objectives?')):
    if not showcompleted:
        showcompleted = False
    objective_list = await Objective.get_all_objectives_from_member_id(interaction.user.id, showcompleted = showcompleted)
    em = nextcord.Embed(
            title="Current Objectives\n", color=nextcord.Color(int("CC99FF", 16)))
    for objective in objective_list:
        if objective.completion_status:
            if objective.point_value and objective.point_value > 0:
                em.add_field(name=f"✅ {objective.name}",
                            value=f"Description: {objective.description}​\n **Worth {objective.point_value} points!**", inline=False)
            else:
                em.add_field(name=f"✅ {objective.name}",
                                            value=f"Description: {objective.description}​", inline=False)
        else:
            if objective.point_value and objective.point_value > 0:
                em.add_field(name=f"❌ {objective.name}",
                            value=f"Description: {objective.description}​\n **Worth {objective.point_value} points!**", inline=False)
            else:
                em.add_field(name=f"❌ {objective.name}",
                                            value=f"Description: {objective.description}​", inline=False)
    print(objective_list)
    return await interaction.send(embed=em, ephemeral=True)

@objective.subcommand(description="View more info about a specific objective.")
async def view(interaction: nextcord.Interaction, name = nextcord.SlashOption(name='name', description='Name of the objective.')):
    selected_objective = await Objective.get_objective_from_objective_name(name)
    if selected_objective.description == None:
            selected_objective.description = "No description provided. Sorry!"
    if selected_objective.completion_status:
        em = nextcord.Embed(
            title=selected_objective.name, color=nextcord.Color(int("42f54b", 16)))
        if selected_objective.point_value and selected_objective.point_value > 0:
            em.add_field(name=selected_objective.description,
                    value=f"Worth {selected_objective.point_value} points!", inline=False)
        else:
            em.add_field(name=selected_objective.description, value="​", inline=False)
        em.add_field(name='​',
                     value=f"Assigned <t:{selected_objective.time_assigned}:D>; due <t:{selected_objective.time_due}:D>.\nComplete!")
        return await interaction.send(embed=em, ephemeral=True)
    else:
        em = nextcord.Embed(
            title=selected_objective.name, color=nextcord.Color(int("f54242", 16)))
        if selected_objective.point_value and selected_objective.point_value > 0:
            em.add_field(name=selected_objective.description,
                        value=f"Worth {selected_objective.point_value} points!", inline=False)
        else:
            em.add_field(name=selected_objective.description, inline=False)
        em.add_field(name='​',
                     value=f"Assigned <t:{selected_objective.time_assigned}:D>; due <t:{selected_objective.time_due}:D>.\nStill Completable!")
        view = ContactOptions()
        await interaction.send(embed=em, view=view, ephemeral=True)
        await view.wait()
        if view.value is None:
            return
        elif view.value == "Complete":
            role = interaction.guild.get_role(int(OWNER_ROLE_ID))
            new_thread = await interaction.channel.create_thread(name=f"\"{selected_objective.name}\" Completion Review", type=nextcord.ChannelType.public_thread)
            return await new_thread.send(f"{role.mention}: {interaction.user.mention} has marked the objective `{selected_objective.name}` as complete!")
        elif view.value == "Clarify":
            role = interaction.guild.get_role(int(OWNER_ROLE_ID))
            new_thread = await interaction.channel.create_thread(name=f"\"{selected_objective.name}\" Clarification Discussion", type=nextcord.ChannelType.public_thread)
            return await new_thread.send(f"{role.mention}: {interaction.user.mention} is requesting clarification on `{selected_objective.name}`.") 

@view.on_autocomplete('name')
async def view_autocompletion(ctx: nextcord.Interaction, team: str):
    async with Database.connection_obj.cursor() as cursor:
        choices = await fetch_assigned_objectives(ctx.guild.id, ctx.user.id, False)
        print(choices)
        await ctx.response.send_autocomplete(choices)

async def fetch_assigned_objectives(guild_id, user_id, show_complete = True):
    async with Database.connection_obj.cursor() as cursor:
        if show_complete:
            await cursor.execute("SELECT name FROM objectives WHERE guild_id = ? AND assigned_member_id = ?", (guild_id, user_id))
        else:
            await cursor.execute("SELECT name FROM objectives WHERE guild_id = ? AND assigned_member_id = ? AND completion_status = ?", (guild_id, user_id, 0))
        names = await cursor.fetchall()
        items = []
        for name in names:
            items.append(name[0])
        return items

@bot.slash_command(description="[ADMIN] Mark an objective as complete.", default_member_permissions=nextcord.Permissions(administrator=True))
async def complete(interaction: nextcord.Interaction, name = nextcord.SlashOption(name='name', description='Name of the objective to mark complete.')):
    selected_objective = await Objective.get_objective_from_objective_name(name)
    await check_member_for_data(interaction.guild.get_member(selected_objective.assigned_member_id))
    await selected_objective.complete()
    
    # TODO: make this pretty or whatever
    async with Database.connection_obj.cursor() as cursor:
        await cursor.execute("SELECT points,tasks_completed FROM members WHERE member_id = ?", (selected_objective.assigned_member_id,))
        data = await cursor.fetchone()
        new_points = int(data[0]) + selected_objective.point_value
        new_tasks_completed = int(data[1]) + 1
        await cursor.execute("UPDATE members SET points = ?, tasks_completed = ? WHERE member_id = ?", (new_points, new_tasks_completed, selected_objective.assigned_member_id))
    await Database.connection_obj.commit()
    return await interaction.send(f"Marked `{selected_objective.name}` as complete.", ephemeral=True)

@complete.on_autocomplete('name')
async def complete_autocompletion(ctx: nextcord.Interaction, team: str):
    async with Database.connection_obj.cursor() as cursor:
        choices = await fetch_all_objectives(ctx.guild.id, ctx.user.id)
        print(choices)
        await ctx.response.send_autocomplete(choices)

@bot.slash_command(description="[ADMIN] Delete an objective.", default_member_permissions=nextcord.Permissions(administrator=True))
async def delete(interaction: nextcord.Interaction, name = nextcord.SlashOption(name='name', description='Name of the objective to delete.')):
    selected_objective = await Objective.get_objective_from_objective_name(name)
    selected_objective_name = selected_objective.name
    await check_member_for_data(interaction.guild.get_member(selected_objective.assigned_member_id))
    await selected_objective.delete()
    return await interaction.send(f"Deleted `{selected_objective_name}`.", ephemeral=True)

@delete.on_autocomplete('name')
async def complete_autocompletion(ctx: nextcord.Interaction, team: str):
    async with Database.connection_obj.cursor() as cursor:
        choices = await fetch_all_objectives(ctx.guild.id, ctx.user.id)
        print(choices)
        await ctx.response.send_autocomplete(choices)

async def fetch_all_objectives(guild_id, user_id):
    async with Database.connection_obj.cursor() as cursor:
        await cursor.execute("SELECT name FROM objectives WHERE guild_id = ?", (guild_id,))
        names = await cursor.fetchall()
        items = []
        for name in names:
            items.append(name[0])
        return items
    
@objective.subcommand(description="Review your stats!")
async def stats(interaction: nextcord.Interaction):
    await check_member_for_data(interaction.guild.get_member(interaction.user.id))
    em = nextcord.Embed(
        title=f"{interaction.user.name} stats:", color=nextcord.Color(int("CC99FF", 16)))
    async with Database.connection_obj.cursor() as cursor:
        await cursor.execute("SELECT points, tasks_completed FROM members WHERE guild_id = ? AND member_id = ?", (interaction.guild.id, interaction.user.id))
        data = await cursor.fetchone()
        points = data[0]
        tasks_completed = data[1]
    em.add_field(name="Total Points:",
                    value=f"🪙 {points}", inline=False)
    em.add_field(name='Completed Objectives:',
                    value=f"☑️ {tasks_completed}")
    await interaction.send(embed=em, ephemeral=True)
print(date_to_unix("4/11/08"))
print(date_to_unix("04/11/2008"))
bot.run(TOKEN)