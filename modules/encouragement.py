import random
import json
from datetime import datetime
import discord

async def handle_encouragement_message(bot, message, image_channels, user_cd, bot_cd):
    # Log: Ghi nhận tin nhắn để debug (có thể bỏ đi sau khi bot hoạt động ổn định)
    # print(f"Processing message from {message.author} in channel {message.channel.id}")

    if message.channel.id not in image_channels:
        # print("Channel not in image_channels, returning.")
        return
    if not message.attachments:
        # print("No attachments found, returning.")
        return
    if not any(att.content_type and att.content_type.startswith("image/") for att in message.attachments):
        # print("No image attachments found, returning.")
        return

    now = datetime.now()
    uid = str(message.author.id)
    cid = message.channel.id

    # --- Kiểm tra cooldown của bot trên kênh ---
    last_bot_time = bot.channel_cooldowns.get(cid)
    if last_bot_time and (now - last_bot_time).total_seconds() < bot_cd:
        remaining_time = int(bot_cd - (now - last_bot_time).total_seconds())
        # Thay vì chỉ return, gửi thông báo cooldown của bot
        try:
            await message.reply(f"Bot đang nghỉ một chút! Vui lòng đợi {remaining_time} giây trước khi gửi ảnh tiếp nhé. ⏳")
        except discord.Forbidden: # Bot không có quyền gửi tin nhắn
            print(f"Warning: Bot does not have permission to reply in channel {cid}")
        return

    # --- Kiểm tra cooldown của người dùng ---
    user_cooldowns = bot.user_cooldowns.get(cid, {})
    last_user_time = user_cooldowns.get(uid)
    if last_user_time and (now - last_user_time).total_seconds() < user_cd:
        remaining_time = int(user_cd - (now - last_user_time).total_seconds())
        # Thay vì chỉ return, gửi thông báo cooldown của người dùng
        try:
            await message.reply(f"{message.author.mention}, bạn đang cooldown! Vui lòng đợi {remaining_time} giây nữa nhé. 🕒")
        except discord.Forbidden:
            print(f"Warning: Bot does not have permission to reply in channel {cid}")
        return

    # --- Nếu không bị cooldown và đủ điều kiện, gửi tin nhắn khuyến khích ---
    if bot.encouragement_messages:
        msg = random.choice(bot.encouragement_messages)
        
        try:
            # Gửi tin nhắn kèm theo emoji đã được nhúng trong encouraging_messages.json
            await message.channel.send(f"{message.author.mention} {msg}")
            
            # Cập nhật thời gian cooldown sau khi gửi thành công
            bot.channel_cooldowns[cid] = now
            if cid not in bot.user_cooldowns:
                bot.user_cooldowns[cid] = {}
            bot.user_cooldowns[cid][uid] = now

            # Cập nhật và lưu số lần đăng ảnh
            bot.post_counts[uid] = bot.post_counts.get(uid, 0) + 1
            with open("data/post_counts.json", "w", encoding="utf-8") as f:
                json.dump(bot.post_counts, f, indent=2, ensure_ascii=False)
                
            # print(f"Sent encouragement message in channel {cid} to {uid}.")
        except discord.Forbidden:
            print(f"Error: Bot does not have permission to send message in channel {cid}")
        except Exception as e:
            print(f"An unexpected error occurred while sending encouragement: {e}")
    else:
        # print("No encouragement messages loaded.")
        pass # Bot sẽ không làm gì nếu không có tin nhắn khuyến khích
    
def setup_encouragement_commands(bot):
    @bot.tree.command(name="post_leaderboard", description="Top users who posted the most screenshots")
    async def post_leaderboard(interaction: discord.Interaction):
        if not bot.post_counts:
            await interaction.response.send_message("Chưa có dữ liệu.")
            return
        top = sorted(bot.post_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        msg = []
        for i, (uid, count) in enumerate(top):
            try:
                user = bot.get_user(int(uid))
                user_name = user.display_name if user else f"<@{uid}>"
            except ValueError:
                user_name = f"Người dùng không hợp lệ (<@{uid}>)"
            msg.append(f"{i+1}. {user_name}: {count} ảnh")
        await interaction.response.send_message(f"📸 **Top 5 người đăng ảnh nhiều nhất**:\n" + "\n".join(msg))
