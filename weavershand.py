import discord
from discord.ext import commands
import datetime
import json
import random
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Leveling System Class
class LevelingSystem:
    def __init__(self, bot):
        self.bot = bot
        self.levels_file = "levels.json"
        self.users = self.load_levels()
        self.xp_cooldown = {}
        self.cooldown_time = 60  # Cooldown in seconds
        
        # Realm definitions with level ranges and colors
        self.realms = {
            0: {
                "name": "Foundation Realm",
                "color": discord.Color.from_rgb(133, 133, 133),  # Gray
                "message": "You have taken your first step into cultivation. The Foundation Realm welcomes you!"
            },
            10: {
                "name": "Intermediate Realm",
                "color": discord.Color.from_rgb(0, 255, 0),  # Green
                "message": "Your dedication shows promise. Welcome to the Intermediate Realm!"
            },
            20: {
                "name": "Advanced Realm",
                "color": discord.Color.from_rgb(0, 0, 255),  # Blue
                "message": "Your power grows stronger. The Advanced Realm acknowledges your progress!"
            },
            30: {
                "name": "Master Realm",
                "color": discord.Color.from_rgb(148, 0, 211),  # Purple
                "message": "Few reach such heights. The Master Realm embraces your strength!"
            },
            40: {
                "name": "Legendary Realm",
                "color": discord.Color.from_rgb(255, 215, 0),  # Gold
                "message": "Tales of your achievements spread far. Welcome to the Legendary Realm!"
            },
            50: {
                "name": "Mythical Realm",
                "color": discord.Color.from_rgb(255, 140, 0),  # Dark Orange
                "message": "Your existence defies common sense. The Mythical Realm accepts you!"
            },
            60: {
                "name": "Sovereign Realm",
                "color": discord.Color.from_rgb(255, 0, 0),  # Red
                "message": "Your authority shakes the heavens. The Sovereign Realm bows to your might!"
            },
            70: {
                "name": "Transcendence Realm",
                "color": discord.Color.from_rgb(255, 255, 255),  # White
                "message": "You have broken through the limits of mortality. The Transcendence Realm is your domain!"
            }
        }

    def load_levels(self):
        try:
            with open(self.levels_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_levels(self):
        with open(self.levels_file, 'w') as f:
            json.dump(self.users, f, indent=4)

    def get_xp_needed(self, level):
        return 5 * (level ** 2) + 50 * level + 100

    def get_realm_data(self, level):
        realm_level = (level - 1) // 10 * 10
        return self.realms.get(realm_level, self.realms[0])

    async def handle_level_up(self, member, channel, old_level, new_level):
        level_channel = discord.utils.get(member.guild.channels, name='level-up')
        if not level_channel:
            return

        # Regular level up message
        embed = discord.Embed(
            title="Level Up! 🎉",
            description=f"{member.mention} has reached level {new_level}!",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)

        old_realm_data = self.get_realm_data(old_level)
        new_realm_data = self.get_realm_data(new_level)

        # Handle realm transition
        if old_realm_data['name'] != new_realm_data['name']:
            # Remove old realm role
            old_role = discord.utils.get(member.guild.roles, name=old_realm_data['name'])
            if old_role:
                await member.remove_roles(old_role)

            # Add new realm role
            new_role = discord.utils.get(member.guild.roles, name=new_realm_data['name'])
            if new_role:
                await member.add_roles(new_role)
            
            # Send realm advancement message
            realm_embed = discord.Embed(
                title="🌟 Realm Advancement 🌟",
                description=f"{member.mention} has ascended to the {new_realm_data['name']}!\n\n{new_realm_data['message']}",
                color=new_realm_data['color']
            )
            realm_embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            await level_channel.send(embed=realm_embed)
        else:
            # Regular level up message
            await level_channel.send(embed=embed)

    async def add_xp(self, message):
        user_id = str(message.author.id)
        if user_id not in self.users:
            self.users[user_id] = {"xp": 0, "level": 1}

        current_time = message.created_at.timestamp()
        if user_id in self.xp_cooldown and current_time - self.xp_cooldown[user_id] < self.cooldown_time:
            return

        xp_gained = random.randint(15, 25)
        self.users[user_id]["xp"] += xp_gained
        self.xp_cooldown[user_id] = current_time

        current_xp = self.users[user_id]["xp"]
        current_level = self.users[user_id]["level"]
        xp_needed = self.get_xp_needed(current_level)

        if current_xp >= xp_needed:
            self.users[user_id]["level"] += 1
            self.users[user_id]["xp"] = current_xp - xp_needed
            await self.handle_level_up(message.author, message.channel, current_level, current_level + 1)

        self.save_levels()

# Create global instance of LevelingSystem
leveling_system = LevelingSystem(bot)

# Bot Events
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print("Bot is ready!")

@bot.event
async def on_member_join(member):
    try:
        # Add Reader and Foundation Realm roles
        reader_role = discord.utils.get(member.guild.roles, name="Reader")
        foundation_role = discord.utils.get(member.guild.roles, name="Foundation Realm")
        
        if reader_role and foundation_role:
            await member.add_roles(reader_role, foundation_role)
            
    except Exception as e:
        print(f"Error in on_member_join: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Process XP
    await leveling_system.add_xp(message)
    
    # Process commands
    await bot.process_commands(message)

# Commands
@bot.command()
async def rank(ctx):
    user_id = str(ctx.author.id)
    user_data = leveling_system.users.get(user_id)
    
    if not user_data:
        await ctx.send("You haven't gained any XP yet!")
        return

    level = user_data["level"]
    xp = user_data["xp"]
    xp_needed = leveling_system.get_xp_needed(level)
    realm_data = leveling_system.get_realm_data(level)

    embed = discord.Embed(
        title=f"{ctx.author.name}'s Rank",
        color=realm_data['color']
    )
    embed.add_field(name="Level", value=str(level), inline=True)
    embed.add_field(name="Realm", value=realm_data['name'], inline=True)
    embed.add_field(name="XP", value=f"{xp}/{xp_needed}", inline=True)
    embed.add_field(name="Progress to Next Level", 
                   value=f"{(xp/xp_needed*100):.1f}%", 
                   inline=True)
    
    next_realm_level = ((level // 10) + 1) * 10
    levels_to_next_realm = next_realm_level - level
    if levels_to_next_realm > 0 and next_realm_level <= 100:
        embed.add_field(name="Next Realm In", 
                       value=f"{levels_to_next_realm} levels", 
                       inline=True)
    
    embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else ctx.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def leaderboard(ctx):
    # Sort users by level and XP
    sorted_users = sorted(
        leveling_system.users.items(),
        key=lambda x: (x[1]['level'], x[1]['xp']),
        reverse=True
    )[:10]  # Get top 10

    embed = discord.Embed(
        title="📊 Cultivation Leaderboard",
        description="Top 10 Cultivators",
        color=discord.Color.gold()
    )

    for idx, (user_id, data) in enumerate(sorted_users, 1):
        try:
            member = await ctx.guild.fetch_member(int(user_id))
            realm_data = leveling_system.get_realm_data(data['level'])
            user_name = member.display_name if member else "Unknown Cultivator"
            
            embed.add_field(
                name=f"{idx}. {user_name}",
                value=f"Level: {data['level']} | Realm: {realm_data['name']}\nXP: {data['xp']}/{leveling_system.get_xp_needed(data['level'])}",
                inline=False
            )
        except discord.NotFound:
            continue

    embed.set_footer(text="Updated in real-time")
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def addxp(ctx, member: discord.Member, xp: int):
    """Add XP to a member (Admin only)"""
    user_id = str(member.id)
    
    if user_id not in leveling_system.users:
        leveling_system.users[user_id] = {"xp": 0, "level": 1}
    
    current_level = leveling_system.users[user_id]["level"]
    leveling_system.users[user_id]["xp"] += xp
    
    # Check for level ups
    while leveling_system.users[user_id]["xp"] >= leveling_system.get_xp_needed(leveling_system.users[user_id]["level"]):
        leveling_system.users[user_id]["xp"] -= leveling_system.get_xp_needed(leveling_system.users[user_id]["level"])
        leveling_system.users[user_id]["level"] += 1
        await leveling_system.handle_level_up(member, ctx.channel, 
                                     leveling_system.users[user_id]["level"]-1, 
                                     leveling_system.users[user_id]["level"])
    
    leveling_system.save_levels()
    await ctx.send(f"Added {xp} XP to {member.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def setlevel(ctx, member: discord.Member, level: int):
    """Set a member's level (Admin only)"""
    if level < 1 or level > 100:
        await ctx.send("Level must be between 1 and 100!")
        return
        
    user_id = str(member.id)
    old_level = leveling_system.users[user_id]["level"] if user_id in leveling_system.users else 1
    
    leveling_system.users[user_id] = {
        "xp": 0,
        "level": level
    }
    
    await leveling_system.handle_level_up(member, ctx.channel, old_level, level)
    leveling_system.save_levels()
    await ctx.send(f"Set {member.mention}'s level to {level}")

# Error Handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing required argument: {error.param.name}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Invalid argument provided!")
    else:
        await ctx.send(f"An error occurred: {str(error)}")

TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)
