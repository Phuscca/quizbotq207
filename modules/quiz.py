import random
import json
import discord
from discord import app_commands

# Định nghĩa ánh xạ từ ID kênh sang tên dự án
# Bạn cần điền đúng ID kênh của các dự án FIATO và TTAVIO vào đây
CHANNEL_PROJECT_MAP = {
    1373205811731497121: "fiato",  # ID kênh FIATO của bạn
    1373205872817344553: "ttavio", # ID kênh TTAVIO của bạn
    # Bạn có thể thêm các kênh khác và project tương ứng nếu cần
    # Ví dụ: 123456789012345678: "another_project",
}

def setup_quiz_commands(bot):
    @bot.tree.command(name="quiz", description="Nhận một câu hỏi quiz theo dự án của kênh")
    async def quiz(interaction: discord.Interaction):
        channel_id = interaction.channel_id
        
        # Xác định project dựa trên kênh hiện tại
        project_name = CHANNEL_PROJECT_MAP.get(channel_id, "default") # Mặc định là "default" nếu kênh không được định nghĩa

        # Lọc câu hỏi theo project_name đã xác định
        filtered_questions = [q for q in bot.questions if q.get("project") == project_name]

        if not filtered_questions:
            await interaction.response.send_message(
                f"Không có câu hỏi nào thuộc dự án '{project_name}'. "
                "Vui lòng thêm câu hỏi vào file data/questions.json với trường 'project' tương ứng."
            )
            return

        q = random.choice(filtered_questions)

        # Lưu câu hỏi và đáp án cho kênh này để xử lý câu trả lời sau
        bot.current_manual_quiz[interaction.channel_id] = {
            "question": q,
            "answer": q["answer"].upper(),
            "asked_by": interaction.user.id
        }

        # Sử dụng Embed để hiển thị câu hỏi đẹp hơn
        embed = discord.Embed(
            title=f"❓ Câu hỏi Kiến thức ({project_name.upper()} Project)", # Hiển thị tên dự án
            description=f"**{q['question']}**\n\nA. {q['A']}\nB. {q['B']}\nC. {q['C']}\nD. {q['D']}",
            color=discord.Color.green()
        )
        embed.set_footer(text="Trả lời bằng cách gõ A, B, C hoặc D (ví dụ: A)")
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="score", description="Hiển thị điểm số cá nhân của bạn")
    async def score(interaction: discord.Interaction):
        uid = str(interaction.user.id)
        await interaction.response.send_message(f"Điểm số hiện tại của bạn: {bot.scores.get(uid, 0)}")

    @bot.tree.command(name="leaderboard", description="Hiển thị Top 5 người dùng có điểm cao nhất")
    async def leaderboard(interaction: discord.Interaction):
        # Sắp xếp theo điểm giảm dần và lấy 5 người đầu tiên
        top = sorted(bot.scores.items(), key=lambda x: x[1], reverse=True)[:5]

        if not top:
            await interaction.response.send_message("Bảng xếp hạng hiện đang trống. Hãy chơi quiz để giành điểm!")
            return

        msg = []
        for i, (uid, score) in enumerate(top):
            # Cố gắng lấy tên người dùng để hiển thị đẹp hơn
            try:
                # bot.get_user chỉ hoạt động nếu user nằm trong cache của bot
                # bot.fetch_user(int(uid)) là async và sẽ tìm kiếm trên Discord nếu không có trong cache,
                # nhưng cần intents.members và quyền Gateway Privileged.
                user = bot.get_user(int(uid))
                user_name = user.display_name if user else f"<@{uid}>"
            except ValueError: # uid không phải số
                user_name = f"Người dùng không hợp lệ (<@{uid}>)"
            msg.append(f"{i+1}. {user_name}: {score} điểm")

        await interaction.response.send_message(f"🏆 **Bảng xếp hạng:**\n" + "\n".join(msg))


async def handle_quiz_answer(bot, message):
    ch_id = message.channel.id
    content = message.content.strip().upper() # Chuyển đổi toàn bộ tin nhắn thành chữ hoa để so sánh

    # Chỉ xử lý các câu trả lời dạng A, B, C, D
    if content not in ["A", "B", "C", "D"]:
        return # Nếu không phải A, B, C, D thì bỏ qua

    # --- Xử lý câu trả lời cho Daily Quiz ---
    if ch_id in bot.daily_quiz_answer and bot.daily_quiz_winner.get(ch_id) is None:
        correct_answer_daily = bot.daily_quiz_answer[ch_id]

        if content == correct_answer_daily:
            bot.daily_quiz_winner[ch_id] = message.author.id # Đánh dấu người thắng đầu tiên
            uid = str(message.author.id)
            bot.scores[uid] = bot.scores.get(uid, 0) + 5 # Cộng 5 điểm cho daily quiz

            await message.reply(f"✅ Chúc mừng {message.author.mention}! Đáp án chính xác! Bạn là người đầu tiên trả lời đúng và được cộng **5 điểm**.")
            
            with open("data/scores.json", "w", encoding="utf-8") as f:
                json.dump(bot.scores, f, indent=2, ensure_ascii=False)
            
            del bot.daily_quiz_answer[ch_id] 
            if ch_id in bot.daily_quiz_question:
                del bot.daily_quiz_question[ch_id]
        else:
            current_daily_q = bot.daily_quiz_question.get(ch_id)
            if current_daily_q:
                correct_option_text = current_daily_q.get(correct_answer_daily)
                if correct_option_text:
                    await message.reply(f"❌ Sai rồi. Đáp án đúng là **{correct_answer_daily}. {correct_option_text}**")
                else:
                    await message.reply(f"❌ Sai rồi. Đáp án đúng là **{correct_answer_daily}**")
            else:
                await message.reply(f"❌ Sai rồi. Đáp án đúng là **{correct_answer_daily}**")
        return # Đã xử lý Daily Quiz, không cần kiểm tra Manual Quiz nữa

    # --- Xử lý câu trả lời cho Quiz thủ công (`/quiz`) ---
    if ch_id in bot.current_manual_quiz:
        quiz_data = bot.current_manual_quiz[ch_id]
        correct_answer_manual = quiz_data["answer"]
        question_content_manual = quiz_data["question"]

        if content == correct_answer_manual:
            uid = str(message.author.id)
            bot.scores[uid] = bot.scores.get(uid, 0) + 1 # Cộng 1 điểm cho manual quiz
            await message.reply(f"✅ Chính xác! Bạn được cộng **1 điểm**.")
            
            with open("data/scores.json", "w", encoding="utf-8") as f:
                json.dump(bot.scores, f, indent=2, ensure_ascii=False)
            
            del bot.current_manual_quiz[ch_id]
        else:
            correct_option_text = question_content_manual.get(correct_answer_manual)
            if correct_option_text:
                await message.reply(f"❌ Sai rồi. Đáp án đúng là **{correct_answer_manual}. {correct_option_text}**")
            else:
                await message.reply(f"❌ Sai rồi. Đáp án đúng là **{correct_answer_manual}**")
            # del bot.current_manual_quiz[ch_id] # Tùy chọn: Xóa sau khi trả lời sai
