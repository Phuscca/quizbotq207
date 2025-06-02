import os
import json
import random
import asyncio
import discord
from discord.ext import tasks
from discord import app_commands
from datetime import datetime, timedelta
import pytz

# Intents cơ bản, bao gồm quyền đọc nội dung tin nhắn
intents = discord.Intents.default()
intents.message_content = True

class QuizBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        # Lưu trữ đáp án của daily quiz cho mỗi channel {channel_id: answer}
        self.daily_quiz_answer = {}
        # Lưu trữ người thắng daily quiz cho mỗi channel {channel_id: user_id}
        self.daily_quiz_winner = {}

    async def setup_hook(self):
        # Đồng bộ hóa các slash commands khi bot khởi động
        await self.tree.sync()
        # Tạo một background task để lên lịch gửi quiz ngẫu nhiên
        self.loop.create_task(schedule_random_quiz())

client = QuizBot()

# Tải câu hỏi từ file questions.json
with open("questions.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

# Tải điểm số từ file scores.json (nếu có)
scores = {}
if os.path.exists("scores.json"):
    with open("scores.json", "r", encoding="utf-8") as f:
        scores = json.load(f)

# Ánh xạ ID kênh với tên dự án tương ứng
channel_project_map = {
    1373205811731497121: "fiato", # Ví dụ ID kênh và tên dự án
    1373205872817344553: "ttavio"  # Ví dụ ID kênh và tên dự án
    # Thêm các kênh và dự án khác của bạn vào đây
    # Ví dụ:
    # YOUR_CHANNEL_ID_1: "project_name_1",
    # YOUR_CHANNEL_ID_2: "project_name_2",
}

@client.tree.command(name="quiz", description="Nhận một câu hỏi trắc nghiệm")
async def quiz(interaction: discord.Interaction):
    project = channel_project_map.get(interaction.channel.id)
    if not project:
        await interaction.response.send_message("Channel này chưa được gán vào dự án nào.")
        return

    filtered_questions = [q for q in questions if q["project"] == project]
    if not filtered_questions:
        await interaction.response.send_message(f"Không có câu hỏi nào cho dự án {project.upper()}.")
        return

    q = random.choice(filtered_questions)
    await interaction.response.send_message(
        f"Câu hỏi: {q['question']}\nA. {q['A']}\nB. {q['B']}\nC. {q['C']}\nD. {q['D']}"
    )

    def check(m):
        # Chỉ chấp nhận tin nhắn từ người dùng đã gọi lệnh và trong cùng một kênh
        return m.author.id == interaction.user.id and m.channel == interaction.channel

    try:
        # Chờ tin nhắn trả lời trong 60 giây
        msg = await client.wait_for("message", check=check, timeout=60.0)
    except asyncio.TimeoutError:
        await interaction.followup.send("Hết thời gian trả lời!")
        return

    user_id_str = str(msg.author.id)
    if msg.content.upper() == q["answer"].upper(): # So sánh không phân biệt hoa thường
        scores[user_id_str] = scores.get(user_id_str, 0) + 1
        await msg.reply("✅ Đúng rồi!")
    else:
        await msg.reply(f"❌ Sai. Đáp án đúng là: {q['answer']}")

    # Lưu điểm số vào file
    with open("scores.json", "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2, ensure_ascii=False)

@client.tree.command(name="score", description="Xem điểm cá nhân")
async def score(interaction: discord.Interaction):
    user_id_str = str(interaction.user.id)
    await interaction.response.send_message(f"📊 Điểm của bạn là: {scores.get(user_id_str, 0)}")

@client.tree.command(name="leaderboard", description="Top 5 điểm cao nhất")
async def leaderboard(interaction: discord.Interaction):
    if not scores:
        await interaction.response.send_message("Chưa có ai có điểm để hiển thị bảng xếp hạng.")
        return
        
    # Sắp xếp điểm số và lấy top 5
    top_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5]
    
    msg_content = "**🏆 Bảng xếp hạng TOP 5:**\n"
    for i, (user_id_str, point) in enumerate(top_scores, 1):
        try:
            user = await client.fetch_user(int(user_id_str))
            user_name = user.name
        except discord.NotFound:
            user_name = f"Người dùng (ID: {user_id_str})" # Xử lý trường hợp không tìm thấy user
        except Exception as e:
            user_name = f"Người dùng (ID: {user_id_str})"
            print(f"Lỗi khi fetch user {user_id_str}: {e}")
            
        msg_content += f"{i}. {user_name}: {point} điểm\n"
        
    await interaction.response.send_message(msg_content)

async def schedule_random_quiz():
    await client.wait_until_ready()
    while True:
        now_vn = datetime.now(pytz.timezone("Asia/Ho_Chi_Minh"))
        
        # Chọn thời gian ngẫu nhiên từ 6 giờ sáng đến 23 giờ tối
        target_hour = random.randint(6, 23)
        target_minute = random.randint(0, 59)
        
        target_time = now_vn.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        
        if target_time < now_vn:
            target_time += timedelta(days=1) # Nếu đã qua, lên lịch cho ngày mai
            
        wait_seconds = (target_time - now_vn).total_seconds()
        print(f"⏰ Today Quiz tiếp theo sẽ được gửi lúc: {target_time.strftime('%Y-%m-%d %H:%M:%S')} (giờ VN)")
        await asyncio.sleep(wait_seconds)

        for channel_id, project_name in channel_project_map.items():
            channel = client.get_channel(channel_id)
            if not channel:
                print(f"Không tìm thấy kênh có ID: {channel_id} cho dự án {project_name}")
                continue

            filtered_questions = [q for q in questions if q["project"] == project_name]
            if filtered_questions:
                question_data = random.choice(filtered_questions)
                # Đặt lại trạng thái cho quiz mới
                client.daily_quiz_answer[channel_id] = question_data["answer"].upper()
                client.daily_quiz_winner[channel_id] = None # Chưa có ai thắng

                try:
                    await channel.send(
                        f"📢 **TODAY QUIZ ({project_name.upper()})**\n"
                        f"{question_data['question']}\n"
                        f"A. {question_data['A']}\n"
                        f"B. {question_data['B']}\n"
                        f"C. {question_data['C']}\n"
                        f"D. {question_data['D']}\n\n"
                        "⏳ Hãy trả lời bằng cách nhắn: `today quiz: [Đáp án của bạn]` (ví dụ: `today quiz: A`)"
                    )
                    print(f"Đã gửi Today Quiz cho dự án {project_name} trong kênh {channel.name}")
                except discord.Forbidden:
                    print(f"Không có quyền gửi tin nhắn đến kênh {channel.name} (ID: {channel_id})")
                except Exception as e:
                    print(f"Lỗi khi gửi Today Quiz đến kênh {channel.name}: {e}")
            else:
                print(f"Không có câu hỏi nào cho dự án {project_name} để gửi Today Quiz.")

@client.event
async def on_message(message: discord.Message):
    # Dòng này để xử lý các command dạng prefix (ví dụ !help).
    # Nếu bot của bạn chỉ dùng slash command thì có thể không cần thiết,
    # nhưng để đó cũng không ảnh hưởng nếu không có prefix command nào được đăng ký.
    await client.process_commands(message)

    if message.author.bot:
        return

    channel_id = message.channel.id
    content_lower_stripped = message.content.lower().strip()

    # Xử lý câu trả lời cho "Today Quiz"
    if channel_id in client.daily_quiz_answer and client.daily_quiz_winner.get(channel_id) is None:
        if content_lower_stripped.startswith("today quiz:"):
            # Lấy phần nội dung sau "today quiz:" và loại bỏ khoảng trắng thừa
            answer_part = content_lower_stripped[len("today quiz:"):].strip()
            
            user_submitted_answer = "" # Mặc định là câu trả lời không hợp lệ
            # Kiểm tra xem phần trả lời có phải là một ký tự A, B, C, D duy nhất không
            if len(answer_part) == 1 and answer_part.upper() in ['A', 'B', 'C', 'D']:
                user_submitted_answer = answer_part.upper()

            correct_answer = client.daily_quiz_answer.get(channel_id)

            if correct_answer and user_submitted_answer == correct_answer:
                client.daily_quiz_winner[channel_id] = message.author.id
                user_id_str = str(message.author.id)
                scores[user_id_str] = scores.get(user_id_str, 0) + 5 # Cộng 5 điểm cho today quiz
                
                await message.reply("✅ Chính xác! Bạn là người đầu tiên trả lời đúng today quiz và nhận +5 điểm.")
                # Tin nhắn thông báo chung cho kênh (tùy chọn, có thể bỏ nếu thấy reply là đủ)
                # await message.channel.send(f"🎉 Chúc mừng {message.author.mention} đã trả lời đúng đầu tiên today quiz và nhận +5 điểm!")
                
                with open("scores.json", "w", encoding="utf-8") as f:
                    json.dump(scores, f, indent=2, ensure_ascii=False)
            elif user_submitted_answer: # Nếu người dùng nhập A/B/C/D nhưng sai
                await message.reply(f"❌ Sai rồi. Đáp án đúng là **{correct_answer}**. Chỉ người đầu tiên trả lời đúng mới được tính điểm.")
            # else: # Trường hợp người dùng nhập "today quiz:" nhưng phần sau không phải A/B/C/D
                  # ví dụ "today quiz: XYZ" hoặc "today quiz: ". Bot sẽ không phản hồi gì trong trường hợp này.
                  # Nếu muốn, bạn có thể thêm một tin nhắn thông báo định dạng tại đây.
                  # await message.reply("Định dạng trả lời không đúng. Vui lòng dùng `today quiz: A/B/C/D`.")
    # Các xử lý tin nhắn khác (nếu có) có thể được thêm vào đây

@client.event
async def on_ready():
    print(f"✅ Bot đã sẵn sàng dưới tên {client.user}")
    print(f"Bot ID: {client.user.id}")
    # In ra các kênh được map để kiểm tra
    print("Kênh được map với dự án:")
    for ch_id, proj in channel_project_map.items():
        channel = client.get_channel(ch_id)
        if channel:
            print(f"  - Kênh '{channel.name}' (ID: {ch_id}) -> Dự án '{proj}'")
        else:
            print(f"  - Kênh ID: {ch_id} (Không tìm thấy) -> Dự án '{proj}'")


# Lấy token từ biến môi trường
BOT_TOKEN = os.getenv("BOT_TOKEN")
if BOT_TOKEN is None:
    print("Lỗi: BOT_TOKEN chưa được thiết lập trong biến môi trường.")
else:
    client.run(BOT_TOKEN)
