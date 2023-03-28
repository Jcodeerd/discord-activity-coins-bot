import discord
import sqlite3
import random
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
import time
import datetime

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.members = True  # Subscribe to the members intent

client = commands.Bot(command_prefix='/', intents=intents)
client.remove_command('help')

# Connect to the database
conn = sqlite3.connect('coins.db')
c = conn.cursor()

# Create the table if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS coins
             (user_id TEXT PRIMARY KEY, balance INTEGER)''')

# Set rate limits (in seconds)
CHAT_RATE_LIMIT = 10
VOICE_RATE_LIMIT = 60

# Helper function to get the user's balance
def get_balance(user_id):
    c.execute("SELECT balance FROM coins WHERE user_id=?", (str(user_id),))
    result = c.fetchone()
    if result:
        return result[0]
    else:
        return 0

# Helper function to update the user's balance and print a message in the console
def update_balance(user_id, amount):
    balance = get_balance(user_id) + amount
    c.execute("REPLACE INTO coins VALUES (?, ?)", (str(user_id), balance))
    conn.commit()
    if amount > 0:
        user = client.get_user(user_id)
        print(f"{user.name}#{user.discriminator} earned {amount} coins.")

# Give coins for voice chat every minute
@tasks.loop(seconds=VOICE_RATE_LIMIT)
async def give_voice_coins():
    for guild in client.guilds:
        for member in guild.members:
            if member.voice and member.voice.channel and not member.voice.afk and not member.voice.mute and not member.voice.deaf and not member.voice.self_mute and not member.voice.self_deaf and not member.guild_permissions.mute_members and not member.guild_permissions.deafen_members:
                update_balance(member.id, random.randint(5, 10))

# Give coins for chat messages every 10 seconds
@client.event
async def on_message(message):
    if message.author.bot:
        return
    if time.time() - on_message.last_called < CHAT_RATE_LIMIT:
        return
    on_message.last_called = time.time()
    update_balance(message.author.id, random.randint(1, 5))

on_message.last_called = 0

# Show user's balance
@client.slash_command(description="Check the amount of coins you / another user has!")
async def balance(ctx, user: discord.Member = None):
    await ctx.defer()  # Defer the response
    if not user:
        user = ctx.author
    balance = get_balance(user.id)
    response = f"{user.display_name} has {balance} coins."
    await ctx.respond(response)

# Show bot's uptime
START_TIME = time.time()
@client.slash_command(description="Get the bot's uptime.")
async def uptime(ctx):
    await ctx.defer()
    uptime = time.time() - START_TIME
    uptime = str(datetime.timedelta(seconds=int(uptime)))
    response = f"Bot has been online for {uptime}."
    await ctx.respond(response)

# Start the bot
@give_voice_coins.before_loop
async def before_give_voice_coins():
    await client.wait_until_ready()
    print('Bot is ready.')
give_voice_coins.start()

@client.event
async def on_ready():
    print(f'{client.user} is connected to the following guilds:')
    for guild in client.guilds:
        print(f'- {guild.name} (id: {guild.id}')

client.run(TOKEN)