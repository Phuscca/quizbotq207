import os
import discord
from discord.ext import commands
import json

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

with open("questions.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

scores = {}

@bot.event
async def on_ready():
    print(f"Bot is running as {bot.user}")

@bot.command()
async def quiz(ctx):
    import random
    q = random.choice(questions)
    await ctx.send(f"Câu hỏi: {q['question']}\nA. {q['A']}\nB. {q['B']}\nC. {q['C']}\nD. {q['D']}")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    msg = await bot.wait_for("message", check=check)
    if msg.content.upper() == q['answer']:
        scores[msg.author.name] = scores.get(msg.author.name, 0) + 1
        await ctx.send("✅ Đúng rồi!")
    else:
        await ctx.send(f"❌ Sai. Đáp án đúng là {q['answer']}")

@bot.command()
async def score(ctx):
    score = scores.get(ctx.author.name, 0)
    await ctx.send(f"Điểm của bạn là: {score}")

bot.run(os.getenv("BOT_TOKEN"))
