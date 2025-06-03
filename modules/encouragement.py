import random
import json
from datetime import datetime
import discord

async def handle_encouragement_message(bot, message, image_channels, user_cd, bot_cd):
    print(f"DEBUG: Message received in channel: {message.channel.id}")
    print(f"DEBUG: Channel ID in config: {image_channels}")
    
    if message.channel.id not in image_channels:
        print(f"DEBUG: Channel {message.channel.id} is NOT an image channel. Returning.")
        return

    print("DEBUG: Channel is an image channel. Checking attachments.")
    if not message.attachments:
        print("DEBUG: No attachments found. Returning.")
        return

    print(f"DEBUG: Found {len(message.attachments)} attachment(s). Checking content type.")
    is_image = False
    for att in message.attachments:
        print(f"DEBUG: Attachment URL: {att.url}, Content Type: {att.content_type}")
        if att.content_type and att.content_type.startswith("image/"):
            is_image = True
            break
    
    if not is_image:
        print("DEBUG: No image attachments found. Returning.")
        return

    print("DEBUG: Image attachment found. Proceeding with cooldown checks.")

    now = datetime.now()
    uid = str(message.author.id)
    cid = message.channel.id

    # --- Kiểm tra cooldown của bot trên kênh ---
    last_bot_time = bot.channel_cooldowns.get(cid)
    if last_bot_time and (now - last_bot_time).total_seconds() < bot_cd:
        remaining_time = int(bot_cd - (now - last_bot_time).total_seconds())
        try:
            await message.reply(f"Bot đang nghỉ một chút! Vui lòng đợi {remaining_time} giây trước khi gửi ảnh tiếp nhé. ⏳")
            print(f"DEBUG: Bot on cooldown for channel {cid}. Remaining: {remaining_time}s")
        except discord.Forbidden:
            print(f"ERROR: Bot does not have permission to reply in channel {cid} (bot cooldown message).")
        return

    # --- Kiểm tra cooldown của người dùng ---
    user_cooldowns = bot.user_cooldowns.get(cid, {})
    last_user_time = user_cooldowns.get(uid)
    if last_user_time and (now - last_user_time).total_seconds() < user_cd:
        remaining_time = int(user_cd - (now - last_user_time).total_seconds())
        try:
            await message.reply(f"{message.author.mention}, bạn đang cooldown! Vui lòng đợi {remaining_time} giây nữa nhé. 🕒")
            print(f"DEBUG: User {uid} on cooldown for channel {cid}. Remaining: {remaining_time}s")
        except discord.Forbidden:
            print(f"ERROR: Bot does not have permission to reply in channel {cid} (user cooldown message).")
        return

    # --- Nếu không bị cooldown và đủ điều kiện, gửi tin nhắn khuyến khích ---
    if bot.encouragement_messages:
        msg = random.choice(bot.encouragement_messages)
        
        try:
            await message.channel.send(f"{message.author.mention} {msg}")
            print(f"DEBUG: Successfully sent encouragement message to {message.author} in channel {cid}.")
            
            bot.channel_cooldowns[cid] = now
            if cid not in bot.user_cooldowns:
                bot.user_cooldowns[cid] = {}
            bot.user_cooldowns[cid][uid] = now

            bot.post_counts[uid] = bot.post_counts.get(uid, 0) + 1
            with open("data/post_counts.json", "w", encoding="utf-8") as f:
                json.dump(bot.post_counts, f, indent=2, ensure_ascii=False)
                print(f"DEBUG: Updated post counts for {uid} and saved scores.")
        except discord.Forbidden:
            print(f"ERROR: Bot does not have permission to send message in channel {cid}. Check channel permissions again!")
        except Exception as e:
            print(f"ERROR: An unexpected error occurred while sending encouragement: {e}")
    else:
        print("DEBUG: bot.encouragement_messages is empty. Not sending message.")
    
# Đây là phần code của hàm setup_encouragement_commands
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
