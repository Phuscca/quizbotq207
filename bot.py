import os, json, random, asyncio, discord
from discord.ext import tasks
from discord import app_commands
from datetime import datetime, timedelta
import pytz

intents = discord.Intents.default()
intents.message_content = True

class QuizBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.daily_quiz_answer = {}
        self.daily_quiz_winner = {}

    async def setup_hook(self):
        await self.tree.sync()
        self.loop.create_task(schedule_random_quiz())

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

async def schedule_random_quiz():
    await client.wait_until_ready()
    while True:
        now_vn = datetime.now(pytz.timezone("Asia/Ho_Chi_Minh"))
        target_hour = random.randint(6, 23)
        target_minute = random.randint(0, 59)
        target_time = now_vn.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        if target_time < now_vn:
            target_time += timedelta(days=1)
        wait_seconds = (target_time - now_vn).total_seconds()
        print(f"⏰ Quiz sẽ được gửi lúc: {target_time.strftime('%H:%M:%S')} (giờ VN)")
        await asyncio.sleep(wait_seconds)

        for ch_id, project in channel_project_map.items():
            channel = client.get_channel(ch_id)
            filtered = [q for q in questions if q["project"] == project]
            if filtered and channel:
                q = random.choice(filtered)
                await channel.send(
                    f"📢 **TODAY QUIZ ({project.upper()})**\n{q['question']}\nA. {q['A']}\nB. {q['B']}\nC. {q['C']}\nD. {q['D']}\n\n"
                    "⏳ Hãy trả lời bằng cách nhắn: `today quiz: A/B/C/D`"
                )
                client.daily_quiz_answer[ch_id] = q["answer"]
                client.daily_quiz_winner[ch_id] = None

@client.event
async def on_message(message):
    await client.process_commands(message)
    if message.author.bot: return
    ch_id = message.channel.id
    content = message.content.lower().strip()
    if ch_id in client.daily_quiz_answer and client.daily_quiz_winner.get(ch_id) is None:
        if content.startswith("today quiz:"):
            answer = content[-1].upper()
            if answer == client.daily_quiz_answer[ch_id]:
                client.daily_quiz_winner[ch_id] = message.author.id
                user_id = str(message.author.id)
                scores[user_id] = scores.get(user_id, 0) + 5
                await message.reply("✅ Chính xác! Bạn là người đầu tiên trả lời đúng today quiz và nhận +5 điểm.")
                await message.channel.send(f"🎉 Chúc mừng {message.author.mention} đã trả lời đúng đầu tiên today quiz và nhận +5 điểm!")
                with open("scores.json", "w", encoding="utf-8") as f:
                    json.dump(scores, f, indent=2, ensure_ascii=False)
            else:
                await message.reply("❌ Sai rồi. Chỉ người đầu tiên trả lời đúng mới được tính điểm.")

@client.event
async def on_ready():
    print(f"✅ Bot đã sẵn sàng dưới tên {client.user}")

client.run(os.getenv("BOT_TOKEN"))
