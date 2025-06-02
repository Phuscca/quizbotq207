import os
import json
import random
import asyncio
import discord
from discord.ext import tasks
from discord import app_commands
from datetime import datetime, timedelta
import pytz

from modules.quiz import setup_quiz_commands, handle_today_quiz
from modules.encouragement import handle_encouragement_message, setup_encouragement_commands

IMAGE_CHANNELS_FOR_ENCOURAGEMENT = [123456789012345678]  # Replace with actual channel IDs
USER_COOLDOWN = 1800
BOT_COOLDOWN = 120
TIMEZONE = "Asia/Ho_Chi_Minh"

intents = discord.Intents.default()
intents.message_content = True

class QuizBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.questions = []
        self.scores = {}
        self.encouragement_messages = []
        self.daily_quiz_answer = {}
        self.daily_quiz_winner = {}
        self.user_cooldowns = {}
        self.channel_cooldowns = {}
        self.post_counts = {}

    async def setup_hook(self):
        setup_quiz_commands(self)
        setup_encouragement_commands(self)
        self.loop.create_task(schedule_daily_quiz(self))
        await self.tree.sync()

client = QuizBot()

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

client.questions = load_json("data/questions.json", [])
client.scores = load_json("data/scores.json", {})
client.encouragement_messages = load_json("data/encouraging_messages.json", [])
client.post_counts = load_json("data/post_counts.json", {})

async def schedule_daily_quiz(bot):
    await bot.wait_until_ready()
    while True:
        now = datetime.now(pytz.timezone(TIMEZONE))
        target = now.replace(hour=random.randint(6, 23), minute=random.randint(0, 59), second=0, microsecond=0)
        if target < now:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())

        for channel_id in IMAGE_CHANNELS_FOR_ENCOURAGEMENT:
            channel = bot.get_channel(channel_id)
            if not channel:
                continue
            filtered = [q for q in bot.questions if q.get("project") == "default"]
            if filtered:
                q = random.choice(filtered)
                bot.daily_quiz_answer[channel_id] = q["answer"].upper()
                bot.daily_quiz_winner[channel_id] = None
                await channel.send(f"📢 **TODAY QUIZ**\n{q['question']}\nA. {q['A']}\nB. {q['B']}\nC. {q['C']}\nD. {q['D']}\nReply with `today quiz: A/B/C/D`")

@client.event
async def on_ready():
    print(f"✅ Bot ready as {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return
    await handle_today_quiz(client, message)
    await handle_encouragement_message(client, message, IMAGE_CHANNELS_FOR_ENCOURAGEMENT, USER_COOLDOWN, BOT_COOLDOWN)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if BOT_TOKEN:
    client.run(BOT_TOKEN)
else:
    print("❌ BOT_TOKEN not set in environment.")
