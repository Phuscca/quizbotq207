import os
import discord
from discord.ext import commands, tasks
import json
import random
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# ===== Load câu hỏi và điểm =====
with open("questions.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

if os.path.exists("scores.json"):
    with open("scores.json", "r", encoding="utf-8") as f:
        scores = json.load(f)
else:
    scores = {}

# ======= Cấu hình =======
DAILY_CHANNEL_IDS = [1373205872817344553, 1373205811731497121]

# ===== Quiz command =====
@bot.command()
async def quiz(ctx):
    q = random.choice(questions)
    await ctx.send(f"Câu hỏi: {q['question']}\nA. {q['A']}\nB. {q['B']}\nC. {q['C']}\nD. {q['D']}")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    msg = await bot.wait_for("message", check=check)
    user = str(msg.author.id)
    if msg.content.upper() == q['answer']:
        scores[user] = scores.get(user, 0) + 1
        await ctx.send("✅ Đúng rồi!")
    else:
        await ctx.send(f"❌ Sai. Đáp án đúng là {q['answer']}")
    with open("scores.json", "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)

# ===== Score command =====
@bot.command()
async def score(ctx):
    user = str(ctx.author.id)
    point = scores.get(user, 0)
    await ctx.send(f"📊 Điểm của bạn là: {point}")

# ===== Leaderboard command =====
@bot.command()
async def leaderboard(ctx):
    top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5]
    msg = "**🏆 Bảng xếp hạng TOP 5:**\n"
    for i, (uid, point) in enumerate(top, 1):
        user = await bot.fetch_user(int(uid))
        msg += f"{i}. {user.name}: {point} điểm\n"
    await ctx.send(msg)

# ===== Daily quiz =====
@tasks.loop(minutes=1)
async def send_daily_quiz():
    now = datetime.now()
    if now.hour == 9 and now.minute == 0:
        q = random.choice(questions)
        for ch_id in DAILY_CHANNEL_IDS:
            channel = bot.get_channel(ch_id)
            if channel:
                await channel.send(f"📢 **Quiz mỗi ngày:**\n{q['question']}\nA. {q['A']}\nB. {q['B']}\nC. {q['C']}\nD. {q['D']}")

@bot.event
async def on_ready():
    print(f"Bot đã sẵn sàng dưới tên {bot.user}")
    send_daily_quiz.start()
