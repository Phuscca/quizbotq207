import os
import discord
from discord.ext import tasks
from discord import app_commands
import json
import random
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True

class QuizBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        send_daily_quiz.start()
        send_weekly_summary.start()

client = QuizBot()

# ===== Load dữ liệu =====
with open("questions.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

if os.path.exists("scores.json"):
    with open("scores.json", "r", encoding="utf-8") as f:
        scores = json.load(f)
else:
    scores = {}

DAILY_CHANNEL_IDS = [1373205872817344553, 1373205811731497121]

@client.tree.command(name="quiz", description="Nhận một câu hỏi trắc nghiệm")
async def quiz(interaction: discord.Interaction):
    q = random.choice(questions)
    await interaction.response.send_message(
        f"Câu hỏi: {q['question']}\nA. {q['A']}\nB. {q['B']}\nC. {q['C']}\nD. {q['D']}"
    )

    def check(m):
        return m.author.id == interaction.user.id and m.channel == interaction.channel

    msg = await client.wait_for("message", check=check)
    user = str(msg.author.id)
    if msg.content.upper() == q['answer']:
        scores[user] = scores.get(user, 0) + 1
        await msg.reply("✅ Đúng rồi!")
    else:
        await msg.reply(f"❌ Sai. Đáp án đúng là {q['answer']}")
    with open("scores.json", "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)

@client.tree.command(name="score", description="Xem điểm cá nhân")
async def score(interaction: discord.Interaction):
    user = str(interaction.user.id)
    point = scores.get(user, 0)
    await interaction.response.send_message(f"📊 Điểm của bạn là: {point}")

@client.tree.command(name="leaderboard", description="Top 5 điểm cao nhất")
async def leaderboard(interaction: discord.Interaction):
    top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5]
    msg = "**🏆 Bảng xếp hạng TOP 5:**\n"
    for i, (uid, point) in enumerate(top, 1):
        user = await client.fetch_user(int(uid))
        msg += f"{i}. {user.name}: {point} điểm\n"
    await interaction.response.send_message(msg)

@tasks.loop(minutes=1)
async def send_daily_quiz():
    now = datetime.now()
    if now.hour == 9 and now.minute == 0:
        q = random.choice(questions)
        for ch_id in DAILY_CHANNEL_IDS:
            channel = client.get_channel(ch_id)
            if channel:
                await channel.send(
                    f"📢 **Quiz mỗi ngày:**\n{q['question']}\nA. {q['A']}\nB. {q['B']}\nC. {q['C']}\nD. {q['D']}"
                )

@tasks.loop(minutes=1)
async def send_weekly_summary():
    now = datetime.now()
    if now.weekday() == 6 and now.hour == 20 and now.minute == 0:
        if not scores:
            return
        top_user_id, top_score = max(scores.items(), key=lambda x: x[1])
        top_user = await client.fetch_user(int(top_user_id))
        msg = f"📅 **Tổng kết tuần**\n🏅 Người có điểm cao nhất: {top_user.name} với {top_score} điểm!"

        for ch_id in DAILY_CHANNEL_IDS:
            channel = client.get_channel(ch_id)
            if channel:
                await channel.send(msg)

@client.event
async def on_ready():
    print(f"Bot đã sẵn sàng dưới tên {client.user}")

client.run(os.getenv("BOT_TOKEN"))