import random
import json
import discord

def setup_quiz_commands(bot):
    @bot.tree.command(name="quiz", description="Get a random quiz question")
    async def quiz(interaction: discord.Interaction):
        # Lọc câu hỏi project "fiato"
        fiato_questions = [q for q in bot.questions if q.get("project") == "fiato"]
        if not fiato_questions:
            await interaction.response.send_message("Không có câu hỏi 'fiato' nào. Vui lòng thêm câu hỏi vào file data/questions.json với trường 'project': 'fiato'.")
            return

        q = random.choice(fiato_questions)

        # Lưu câu hỏi và đáp án cho kênh này để xử lý câu trả lời sau
        # current_manual_quiz sẽ lưu trữ một dictionary với channel_id làm key
        # và một dictionary chứa thông tin câu hỏi (question, answer, asked_by) làm value
        bot.current_manual_quiz[interaction.channel_id] = {
            "question": q,
            "answer": q["answer"].upper(),
            "asked_by": interaction.user.id # Có thể dùng để chỉ cho phép người yêu cầu trả lời
        }

        # Sử dụng Embed để hiển thị câu hỏi đẹp hơn
        embed = discord.Embed(
            title="❓ Câu hỏi Kiến thức (FIATO Project)",
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
                user = await bot.fetch_user(int(uid)) # fetch_user là async, cần await
                user_name = user.display_name # Hoặc user.name
            except discord.NotFound:
                user_name = f"Người dùng không tồn tại (<@{uid}>)" # Fallback nếu người dùng không tìm thấy
            except ValueError: # uid không phải số
                user_name = f"Người dùng không hợp lệ (<@{uid}>)"
            msg.append(f"{i+1}. {user_name}: {score} điểm")

        await interaction.response.send_message(f"🏆 **Bảng xếp hạng:**\n" + "\n".join(msg))


# Đổi tên từ handle_today_quiz sang handle_quiz_answer và thay đổi logic
async def handle_quiz_answer(bot, message):
    ch_id = message.channel.id
    content = message.content.strip().upper() # Chuyển đổi toàn bộ tin nhắn thành chữ hoa để so sánh

    # Chỉ xử lý các câu trả lời dạng A, B, C, D
    if content not in ["A", "B", "C", "D"]:
        return # Nếu không phải A, B, C, D thì bỏ qua

    # --- Xử lý câu trả lời cho Daily Quiz ---
    # Kiểm tra xem có câu đố daily quiz nào đang active trong kênh này không
    # và chưa có người thắng (bot.daily_quiz_winner.get(ch_id) is None)
    if ch_id in bot.daily_quiz_answer and bot.daily_quiz_winner.get(ch_id) is None:
        correct_answer_daily = bot.daily_quiz_answer[ch_id]

        if content == correct_answer_daily:
            bot.daily_quiz_winner[ch_id] = message.author.id # Đánh dấu người thắng đầu tiên
            uid = str(message.author.id)
            bot.scores[uid] = bot.scores.get(uid, 0) + 5 # Cộng 5 điểm cho daily quiz

            await message.reply(f"✅ Chúc mừng {message.author.mention}! Đáp án chính xác! Bạn là người đầu tiên trả lời đúng và được cộng **5 điểm**.")
            
            # Lưu điểm ngay lập tức vào file
            with open("data/scores.json", "w", encoding="utf-8") as f:
                json.dump(bot.scores, f, indent=2, ensure_ascii=False)
            
            # Xóa câu hỏi daily quiz sau khi có người trả lời đúng đầu tiên
            # Điều này ngăn không cho người khác trả lời đúng và nhận điểm trong cùng một quiz
            del bot.daily_quiz_answer[ch_id] 
            if ch_id in bot.daily_quiz_question:
                del bot.daily_quiz_question[ch_id] # Xóa luôn câu hỏi đã lưu
        else:
            # Người trả lời sai trong Daily Quiz (không bị trừ điểm)
            # Thông báo đáp án đúng cho người trả lời sai
            current_daily_q = bot.daily_quiz_question.get(ch_id) # Lấy lại câu hỏi đã gửi
            if current_daily_q:
                correct_option_text = current_daily_q.get(correct_answer_daily)
                if correct_option_text:
                    await message.reply(f"❌ Sai rồi. Đáp án đúng là **{correct_answer_daily}. {correct_option_text}**")
                else: # Fallback nếu không lấy được text của đáp án
                    await message.reply(f"❌ Sai rồi. Đáp án đúng là **{correct_answer_daily}**")
            else:
                await message.reply(f"❌ Sai rồi. Đáp án đúng là **{correct_answer_daily}**")
        return # Đã xử lý Daily Quiz, không cần kiểm tra Manual Quiz nữa

    # --- Xử lý câu trả lời cho Quiz thủ công (`/quiz`) ---
    # Kiểm tra xem có câu đố thủ công nào đang active trong kênh này không
    if ch_id in bot.current_manual_quiz:
        quiz_data = bot.current_manual_quiz[ch_id]
        correct_answer_manual = quiz_data["answer"]
        question_content_manual = quiz_data["question"] # Lấy lại nội dung câu hỏi đã gửi

        if content == correct_answer_manual:
            uid = str(message.author.id)
            bot.scores[uid] = bot.scores.get(uid, 0) + 1 # Cộng 1 điểm cho manual quiz
            await message.reply(f"✅ Chính xác! Bạn được cộng **1 điểm**.")
            
            # Lưu điểm ngay lập tức vào file
            with open("data/scores.json", "w", encoding="utf-8") as f:
                json.dump(bot.scores, f, indent=2, ensure_ascii=False)
            
            # Xóa câu hỏi thủ công sau khi trả lời đúng
            del bot.current_manual_quiz[ch_id]
        else:
            # Người trả lời sai trong Quiz thủ công
            # Thông báo đáp án đúng cho người trả lời sai
            correct_option_text = question_content_manual.get(correct_answer_manual)
            if correct_option_text:
                await message.reply(f"❌ Sai rồi. Đáp án đúng là **{correct_answer_manual}. {correct_option_text}**")
            else: # Fallback nếu không lấy được text của đáp án
                await message.reply(f"❌ Sai rồi. Đáp án đúng là **{correct_answer_manual}**")
            
            # Quyết định: Sau khi trả lời sai, có nên xóa câu hỏi thủ công không?
            # Hiện tại, tôi sẽ không xóa để người khác có thể thử tiếp.
            # Nếu bạn muốn xóa để chỉ cho phép 1 lần trả lời cho mỗi `/quiz`, hãy uncomment dòng dưới:
            # del bot.current_manual_quiz[ch_id]
