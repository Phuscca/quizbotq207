import os, json, random, discord
from discord.ext import tasks
from discord import app_commands
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

with open("questions.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

scores = {}
if os.path.exists("scores.json"):
    with open("scores.json", "r", encoding="utf-8") as f:
        scores = json.load(f)

channel_project_map = {
    1373205811731497121: "fiato",
    1373205872817344553: "ttavio"
}

@client.tree.command(name="quiz", description="Nhận một câu hỏi trắc nghiệm")
async def quiz(interaction: discord.Interaction):
    project = channel_project_map.get(interaction.channel.id)
    if not project:
        await interaction.response.send_message("Channel này chưa được gán vào dự án nào.")
        return
    filtered = [q for q in questions if q["project"] == project]
    if not filtered:
        await interaction.response.send_message(f"Không có câu hỏi nào cho dự án {project.upper()}.")
        return
    q = random.choice(filtered)
    await interaction.response.send_message(
        f"Câu hỏi: {q['question']}\nA. {q['A']}\nB. {q['B']}\nC. {q['C']}\nD. {q['D']}"
    )
    def check(m): return m.author.id == interaction.user.id and m.channel == interaction.channel
    msg = await client.wait_for("message", check=check)
    user = str(msg.author.id)
    if msg.content.upper() == q["answer"]:
        scores[user] = scores.get(user, 0) + 1
        await msg.reply("✅ Đúng rồi!")
    else:
        await msg.reply(f"❌ Sai. Đáp án đúng là: {q['answer']}")
    with open("scores.json", "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2, ensure_ascii=False)

@client.tree.command(name="score", description="Xem điểm cá nhân")
async def score(interaction: discord.Interaction):
    user = str(interaction.user.id)
    await interaction.response.send_message(f"📊 Điểm của bạn là: {scores.get(user, 0)}")

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
        for ch_id, project in channel_project_map.items():
            channel = client.get_channel(ch_id)
            filtered = [q for q in questions if q["project"] == project]
            if filtered and channel:
                q = random.choice(filtered)
                await channel.send(
                    f"📢 **Quiz mỗi ngày ({project.upper()})**\n{q['question']}\nA. {q['A']}\nB. {q['B']}\nC. {q['C']}\nD. {q['D']}"
                )

@tasks.loop(minutes=1)
async def send_weekly_summary():
    now = datetime.now()
    if now.weekday() == 6 and now.hour == 20 and now.minute == 0:
        if not scores: return
        top_user_id, top_score = max(scores.items(), key=lambda x: x[1])
        top_user = await client.fetch_user(int(top_user_id))
        msg = f"📅 **Tổng kết tuần**\n🏅 Người có điểm cao nhất: {top_user.name} với {top_score} điểm!"
        for ch_id in channel_project_map:
            channel = client.get_channel(ch_id)
            if channel: await channel.send(msg)

@client.event
async def on_ready():
    print(f"✅ Bot đã sẵn sàng dưới tên {client.user}")

client.run(os.getenv("BOT_TOKEN"))
