import os
import json
import random
import asyncio
import discord
from discord.ext import tasks
from discord import app_commands
from datetime import datetime, timedelta
import pytz

# Import các hàm đã được cập nhật từ module quiz và encouragement
from modules.quiz import setup_quiz_commands, handle_quiz_answer # Đổi handle_today_quiz thành handle_quiz_answer
from modules.encouragement import handle_encouragement_message, setup_encouragement_commands

# Cập nhật các hằng số kênh theo yêu cầu mới
# Giữ nguyên IMAGE_CHANNELS_FOR_ENCOURAGEMENT nếu bạn vẫn dùng cho khuyến khích
IMAGE_CHANNELS_FOR_ENCOURAGEMENT = [1372263906948546600, 1372263291283570790]
TRAINING_CHANNELS = [1373205811731497121, 1373205872817344553] # FIATO, TTAVIO

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

        # THÊM CÁC BIẾN MỚI DƯỚI ĐÂY:
        self.daily_quiz_answer = {}          # Lưu đáp án của câu đố hàng ngày cho từng kênh
        self.daily_quiz_winner = {}          # Lưu người thắng câu đố hàng ngày cho từng kênh
        self.daily_quiz_question = {}        # LƯU TRỮ CÂU HỎI DAILY QUIZ ĐÃ GỬI CHO MỖI KÊNH
        self.current_manual_quiz = {}        # LƯU TRỮ CÂU HỎI QUIZ THỦ CÔNG ĐANG ACTIVE CHO MỖI KÊNH (Dành cho /quiz)

        self.user_cooldowns = {}
        self.channel_cooldowns = {}
        self.post_counts = {}

    async def setup_hook(self):
        setup_quiz_commands(self)
        setup_encouragement_commands(self)
        self.loop.create_task(schedule_daily_quiz(self))
        self.loop.create_task(schedule_weekly_summary(self)) # Thêm tác vụ mới cho tổng kết tuần
        await self.tree.sync()

client = QuizBot()

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e: # Nên bắt Exception cụ thể hơn để biết lỗi là gì
        print(f"Error loading {path}: {e}")
        return default

client.questions = load_json("data/questions.json", [])
client.scores = load_json("data/scores.json", {})
client.encouragement_messages = load_json("data/encouraging_messages.json", [])
client.post_counts = load_json("data/post_counts.json", {})


# Cập nhật hàm schedule_daily_quiz
async def schedule_daily_quiz(bot):
    await bot.wait_until_ready()
    while True:
        now = datetime.now(pytz.timezone(TIMEZONE))
        # Đặt giờ cố định 9:00 sáng
        target = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if target < now:
            target += timedelta(days=1) # Nếu đã qua 9h hôm nay thì đợi đến 9h ngày mai

        print(f"Daily Quiz scheduled for: {target}")
        await asyncio.sleep((target - now).total_seconds())

        for channel_id in TRAINING_CHANNELS: # Thay đổi sang TRAINING_CHANNELS
            channel = bot.get_channel(channel_id)
            if not channel:
                print(f"Warning: Daily Quiz channel {channel_id} not found.")
                continue

            filtered_questions = [q for q in bot.questions if q.get("project") == "default"] # Daily quiz vẫn dùng "default"
            if filtered_questions:
                q = random.choice(filtered_questions)
                bot.daily_quiz_answer[channel_id] = q["answer"].upper()
                bot.daily_quiz_winner[channel_id] = None
                bot.daily_quiz_question[channel_id] = q # Lưu lại câu hỏi daily quiz

                # Định dạng tin nhắn Daily Quiz với Embed
                embed = discord.Embed(
                    title="📢 TODAY QUIZ 📢",
                    description=f"**Câu hỏi:** {q['question']}\n\nA. {q['A']}\nB. {q['B']}\nC. {q['C']}\nD. {q['D']}",
                    color=discord.Color.blue()
                )
                embed.set_footer(text="Trả lời bằng cách gõ A, B, C hoặc D.")
                await channel.send(embed=embed)
            else:
                print(f"No 'default' project questions available for Daily Quiz in channel {channel_id}.")


# Thêm hàm schedule_weekly_summary mới
async def schedule_weekly_summary(bot):
    await bot.wait_until_ready()
    while True:
        now = datetime.now(pytz.timezone(TIMEZONE))
        # Tìm ngày Chủ Nhật tiếp theo lúc 20:00
        # weekday() trả về 0 cho Monday và 6 cho Sunday.
        # (6 - now.weekday() + 7) % 7 sẽ cho số ngày đến Chủ Nhật tiếp theo (bao gồm cả Chủ Nhật hiện tại nếu là Chủ Nhật)
        days_until_sunday = (6 - now.weekday() + 7) % 7
        
        target = now + timedelta(days=days_until_sunday)
        target = target.replace(hour=20, minute=0, second=0, microsecond=0)

        # Nếu thời gian mục tiêu đã qua trong Chủ Nhật hiện tại, chuyển sang Chủ Nhật tuần sau
        if target < now:
            target += timedelta(weeks=1)

        print(f"Weekly Summary scheduled for: {target}")
        await asyncio.sleep((target - now).total_seconds())

        # Tạo nội dung tổng kết
        top_users = sorted(bot.scores.items(), key=lambda x: x[1], reverse=True)[:3]
        if top_users:
            summary_msg = "🏆 **TỔNG KẾT TUẦN** 🏆\n\n**Top 3 người có điểm cao nhất:**\n"
            for i, (uid, score) in enumerate(top_users):
                try:
                    user = bot.get_user(int(uid)) # Cố gắng lấy đối tượng user từ ID
                    user_name = user.mention if user else f"<@{uid}>" # Dùng mention nếu có user object, không thì dùng ID
                    summary_msg += f"{i+1}. {user_name}: {score} điểm\n"
                except ValueError: # Xử lý trường hợp uid không phải số
                    summary_msg += f"{i+1}. <@{uid}>: {score} điểm\n"
        else:
            summary_msg = "🏆 **TỔNG KẾT TUẦN** 🏆\n\nHiện chưa có dữ liệu điểm số."

        # Gửi tin nhắn tổng kết vào các kênh training
        for channel_id in TRAINING_CHANNELS:
            channel = bot.get_channel(channel_id)
            if channel:
                await channel.send(summary_msg)
            else:
                print(f"Warning: Weekly Summary channel {channel_id} not found.")


@client.event
async def on_ready():
    print(f"✅ Bot ready as {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    # Gọi hàm xử lý câu trả lời quiz thủ công và daily quiz
    await handle_quiz_answer(client, message) # Thay thế handle_today_quiz

    # Giữ nguyên phần encouragement nếu bạn muốn
    await handle_encouragement_message(client, message, IMAGE_CHANNELS_FOR_ENCOURAGEMENT, USER_COOLDOWN, BOT_COOLDOWN)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if BOT_TOKEN:
    client.run(BOT_TOKEN)
else:
    print("❌ BOT_TOKEN not set in environment.")
