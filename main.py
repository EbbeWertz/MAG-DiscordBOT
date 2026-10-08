import json
import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_CHANNEL_ID = 1557733627956166819
DATA_FILE = "adje_count.json"

def load_counter() -> int:
    """Loads count from JSON file, or defaults to 0."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                return data.get("adje_counter", 0)
        except Exception as e:
            print(f"Error loading counter file: {e}")
    return 0


def save_counter(count: int) -> None:
    """Saves current count to JSON file."""
    try:
        with open(DATA_FILE, "w") as f:
            json.dump({"adje_counter": count}, f)
    except Exception as e:
        print(f"Error saving counter file: {e}")


intents = discord.Intents.default()

class AdjeBot(commands.Bot):

    async def setup_hook(self):
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} slash command(s).")
        except Exception as e:
            print(f"Failed to sync slash commands: {e}")


bot = AdjeBot(command_prefix="!", intents=intents)
adje_counter = load_counter()


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"Loaded initial adje count: {adje_counter}")


# --- SLASH COMMANDS ---


@bot.tree.command(name="adje", description="Increment the global adje counter")
async def adje(interaction: discord.Interaction):
    global adje_counter

    if interaction.channel_id != ALLOWED_CHANNEL_ID:
        await interaction.response.send_message(
            f"This command can only be used in <#{ALLOWED_CHANNEL_ID}>.",
            ephemeral=True,
        )
        return

    adje_counter += 1
    save_counter(adje_counter)

    # Private confirmation message visible ONLY to the user
    await interaction.response.send_message(
        f"🍻 **Adje registered!** Total count is now **{adje_counter}**.",
        ephemeral=True,
    )


@bot.tree.command(
    name="adjes-overview", description="Display the current total adje count"
)
async def adjes_overview(interaction: discord.Interaction):
    if interaction.channel_id != ALLOWED_CHANNEL_ID:
        await interaction.response.send_message(
            f"This command can only be used in <#{ALLOWED_CHANNEL_ID}>.",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        f"📊 Current global adje count: **{adje_counter}**"
    )


# --- RUN BOT ---
if __name__ == "__main__":
    bot.run(BOT_TOKEN)