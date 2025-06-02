import random
import json
from datetime import datetime
import discord

async def handle_encouragement_message(bot, message, image_channels, user_cd, bot_cd):
    if message.channel.id not in image_channels:
        return
    if not message.attachments:
        return
    if not any(att.content_type and att.content_type.startswith("image/") for att in message.attachments):
        return

    now = datetime.now()
    uid = str(message.author.id)
    cid = message.channel.id

    last_bot_time = bot.channel_cooldowns.get(cid)
    if last_bot_time and (now - last_bot_time).total_seconds() < bot_cd:
        return

    user_cooldowns = bot.user_cooldowns.get(cid, {})
    last_user_time = user_cooldowns.get(uid)
    if last_user_time and (now - last_user_time).total_seconds() < user_cd:
        return

    if bot.encouragement_messages:
        msg = random.choice(bot.encouragement_messages)
        gif_url = "https://media.giphy.com/media/111ebonMs90YLu/giphy.gif"  # sample gif
        await message.channel.send(f"{message.author.mention} {msg}", file=discord.File(fp="data/thumbs_up.png", filename="thumbs_up.png"))  # Optional sticker
        bot.channel_cooldowns[cid] = now
        if cid not in bot.user_cooldowns:
            bot.user_cooldowns[cid] = {}
        bot.user_cooldowns[cid][uid] = now

        bot.post_counts[uid] = bot.post_counts.get(uid, 0) + 1
        with open("data/post_counts.json", "w", encoding="utf-8") as f:
            json.dump(bot.post_counts, f, indent=2, ensure_ascii=False)

def setup_encouragement_commands(bot):
    @bot.tree.command(name="post_leaderboard", description="Top users who posted the most screenshots")
    async def post_leaderboard(interaction: discord.Interaction):
        if not bot.post_counts:
            await interaction.response.send_message("Chưa có dữ liệu.")
            return
        top = sorted(bot.post_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        msg = "\n".join([f"{i+1}. <@{uid}>: {count} ảnh" for i, (uid, count) in enumerate(top)])
        await interaction.response.send_message(f"📸 **Top 5 người đăng ảnh nhiều nhất**:\n{msg}")
