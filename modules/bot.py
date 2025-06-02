import random
import json
import discord

def setup_quiz_commands(bot):
    @bot.tree.command(name="quiz", description="Get a random quiz question")
    async def quiz(interaction: discord.Interaction):
        if not bot.questions:
            await interaction.response.send_message("No questions available.")
            return
        q = random.choice(bot.questions)
        await interaction.response.send_message(f"{q['question']}\nA. {q['A']}\nB. {q['B']}\nC. {q['C']}\nD. {q['D']}")

    @bot.tree.command(name="score", description="Your current score")
    async def score(interaction: discord.Interaction):
        uid = str(interaction.user.id)
        await interaction.response.send_message(f"Your score: {bot.scores.get(uid, 0)}")

    @bot.tree.command(name="leaderboard", description="Top 5 users")
    async def leaderboard(interaction: discord.Interaction):
        top = sorted(bot.scores.items(), key=lambda x: x[1], reverse=True)[:5]
        msg = "\n".join([f"{i+1}. <@{uid}>: {score}" for i, (uid, score) in enumerate(top)])
        await interaction.response.send_message(f"🏆 Leaderboard:\n{msg}")

async def handle_today_quiz(bot, message):
    ch_id = message.channel.id
    content = message.content.lower().strip()
    if ch_id in bot.daily_quiz_answer and bot.daily_quiz_winner.get(ch_id) is None:
        if content.startswith("today quiz:"):
            answer = content.replace("today quiz:", "").strip().upper()
            if answer == bot.daily_quiz_answer[ch_id]:
                bot.daily_quiz_winner[ch_id] = message.author.id
                uid = str(message.author.id)
                bot.scores[uid] = bot.scores.get(uid, 0) + 5
                await message.reply("✅ Correct! +5 points.")
                with open("data/scores.json", "w", encoding="utf-8") as f:
                    json.dump(bot.scores, f, indent=2, ensure_ascii=False)
            else:
                await message.reply(f"❌ Wrong answer. Correct was: {bot.daily_quiz_answer[ch_id]}")
