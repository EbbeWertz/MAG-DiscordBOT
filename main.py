import json
import os
import discord
from aiohttp import web
from discord.ext import commands
from dotenv import load_dotenv

from AdjesService import AdjesService

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CONFIG_FILE = "config.json"

# --- PERSISTENT CONFIGURATION FOR CHANNEL ID ---


def load_allowed_channel_id() -> int:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return data.get("allowed_channel_id", 0)
        except Exception as e:
            print(f"Error loading config file: {e}")
    return 0


def save_allowed_channel_id(channel_id: int) -> None:
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump({"allowed_channel_id": channel_id}, f)
    except Exception as e:
        print(f"Error saving config file: {e}")


ALLOWED_CHANNEL_ID = load_allowed_channel_id()
adje_service = AdjesService()

intents = discord.Intents.default()
intents.message_content = True


class AdjeBot(commands.Bot):

    async def setup_hook(self):
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} slash command(s).")
        except Exception as e:
            print(f"Failed to sync slash commands: {e}")


bot = AdjeBot(command_prefix="!", intents=intents)


def get_help_message() -> str:
    return (
        "❓ **Hoe gebruik je de adjesbot?**\n"
        "Om een adje te registreren gebruik je het `!adje`-command op 1 van de volgende manieren:\n\n"
        "• Zet je gewoon een adje?\n"
        "  --> `!adje` — Verhoogt je eigen teller met 1\n\n"
        "• Zet je meerdere adjes tegelijk?\n"
        "  --> `!adje [aantal]` — Verhoogt je eigen teller met het opgegeven aantal\n\n"
        "• Film je voor iemand anders een adje?\n"
        "  --> `!adje [@user]` — Verhoog de score van de getagde gebruiker met 1\n\n"
        "• Film je voor iemand anders meerdere adjes tegelijk?\n"
        "  --> `!adje [@user] [aantal]` (of `!adje [aantal] [@user]`) — Verhoog de score van de gebruiker met het opgegeven aantal\n\n"
        "• Oeps, foutje?\n"
        "  --> `!adje undo` — Maak de adje(s) van je laatste command ongedaan\n\n"
        "*Voorbeelden:* `!adje`, `!adje 2`, `!adje @Bram`, `!adje @Bram 2`"
    )


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")


@bot.event
async def on_message(message: discord.Message):
    global ALLOWED_CHANNEL_ID

    if message.author.bot or message.channel.id != ALLOWED_CHANNEL_ID:
        return

    parts = message.content.strip().split()
    if not parts:
        return

    first_word = parts[0].lower()

    if first_word in ["!adje", "adje"]:
        args = parts[1:]

        if args and args[0].lower() == "undo":
            user_id_str = str(message.author.id)
            adje_service.undo_adje(user_id_str)
            current_count = adje_service.get_adjes(user_id_str)
            await message.reply(
                f"↩️ Laatste adje(s) ongedaan gemaakt. Je staat nu terug op {current_count}"
            )
            return

        target_member: discord.Member = message.author
        is_tagged = False
        amount: int = 1
        found_user = False
        found_amount = False

        for arg in args:
            arg_clean = arg.strip()

            if arg_clean.startswith("<@") and arg_clean.endswith(">"):
                if found_user:
                    await message.reply(get_help_message())
                    return
                raw_id = arg_clean.translate({ord(c): None for c in "<@!>"})
                if raw_id.isdigit() and message.guild:
                    found_member = message.guild.get_member(int(raw_id))
                    if found_member:
                        target_member = found_member
                        is_tagged = True
                        found_user = True
                    else:
                        await message.reply(get_help_message())
                        return
                else:
                    await message.reply(get_help_message())
                    return

            elif arg_clean.isdigit():
                if found_amount:
                    await message.reply(get_help_message())
                    return
                amount = int(arg_clean)
                found_amount = True
            else:
                await message.reply(get_help_message())
                return

        user_id_str = str(target_member.id)
        adje_service.register_adje(user_id_str, amount)
        current_count = adje_service.get_adjes(user_id_str)

        subject = target_member.mention if is_tagged else "Jij"
        await message.reply(f"{subject} staat nu op {current_count}")

    await bot.process_commands(message)


# --- DASHBOARD HTML WEB PAGE ---

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Adjes Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 2rem; }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { color: #f59e0b; text-align: center; }
        .card { background: #1e293b; border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3); }
        h2 { margin-top: 0; border-bottom: 2px solid #334155; padding-bottom: 0.5rem; }
        table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
        th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #334155; }
        th { color: #94a3b8; }
        input[type="number"], select { background: #0f172a; color: #fff; border: 1px solid #475569; padding: 0.5rem; border-radius: 6px; width: 80px; }
        select { width: 100%; max-width: 300px; }
        button { background: #2563eb; color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; transition: 0.2s; }
        button:hover { background: #1d4ed8; }
        .btn-danger { background: #dc2626; }
        .btn-danger:hover { background: #b91c1c; }
        .flex-between { display: flex; justify-content: space-between; align-items: center; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🍻 Adjes Dashboard</h1>

        <!-- CHART CARD -->
        <div class="card">
            <h2>Overview Graph</h2>
            <canvas id="adjesChart"></canvas>
        </div>

        <!-- SETTINGS: CHANNEL SELECTION -->
        <div class="card">
            <h2>Channel Configuration</h2>
            <form action="/set-channel" method="POST" class="flex-between">
                <select name="channel_id">
                    <option value="0">-- Select Channel --</option>
                    {% for ch in channels %}
                    <option value="{{ ch.id }}" {% if ch.id == current_channel %}selected{% endif %}>
                        #{{ ch.name }} ({{ ch.guild }})
                    </option>
                    {% endfor %}
                </select>
                <button type="submit">Save Channel</button>
            </form>
        </div>

        <!-- USER MANAGEMENT -->
        <div class="card">
            <h2>User Management</h2>
            <table>
                <thead>
                    <tr>
                        <th>User ID</th>
                        <th>User Name</th>
                        <th>Adjes Count</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for user in users %}
                    <tr>
                        <td><code>{{ user.id }}</code></td>
                        <td><strong>{{ user.name }}</strong></td>
                        <td>
                            <form action="/update-user" method="POST" style="display:inline;">
                                <input type="hidden" name="user_id" value="{{ user.id }}">
                                <input type="number" name="count" value="{{ user.count }}" min="0">
                                <button type="submit">Override</button>
                            </form>
                        </td>
                        <td>
                            <form action="/remove-user" method="POST" style="display:inline;">
                                <input type="hidden" name="user_id" value="{{ user.id }}">
                                <button type="submit" class="btn-danger">Remove</button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- CLEAR ALL -->
        <div class="card flex-between">
            <div>
                <h3 style="margin:0; color:#ef4444;">Danger Zone</h3>
                <p style="margin:0; color:#94a3b8; font-size:0.9rem;">Reset all user counts back to 0.</p>
            </div>
            <form action="/clear-all" method="POST" onsubmit="return confirm('Are you sure you want to reset all counts to 0?');">
                <button type="submit" class="btn-danger">Reset All Adjes</button>
            </form>
        </div>
    </div>

    <script>
        const ctx = document.getElementById('adjesChart').getContext('2d');
        const chartData = {{ chart_data | safe }};
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: 'Total Adjes',
                    data: chartData.values,
                    backgroundColor: '#f59e0b',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 } }
                }
            }
        });
    </script>
</body>
</html>
"""

# --- AIOHTTP WEB HANDLERS ---


async def handle_dashboard(request: web.Request):
    global ALLOWED_CHANNEL_ID

    # Resolve channel objects from Discord cache
    channels = []
    for guild in bot.guilds:
        for ch in guild.text_channels:
            channels.append({"id": ch.id, "name": ch.name, "guild": guild.name})

    # Resolve user names from Discord cache or fallback to User ID
    users = []
    labels = []
    values = []

    for user_id, count in adje_service.adjes.items():
        user_obj = bot.get_user(int(user_id))
        name = user_obj.display_name if user_obj else f"User {user_id}"
        users.append({"id": user_id, "name": name, "count": count})
        labels.append(name)
        values.append(count)

    # Simple Jinja-style manual rendering for a standalone file
    rendered_html = (
        HTML_TEMPLATE.replace(
            "{{ chart_data | safe }}",
            json.dumps({"labels": labels, "values": values}),
        )
        .replace("{{ current_channel }}", str(ALLOWED_CHANNEL_ID))
        .replace(
            "{% for ch in channels %}",
            "".join(
                [
                    f'<option value="{c["id"]}" {"selected" if c["id"] == ALLOWED_CHANNEL_ID else ""}>#{c["name"]} ({c["guild"]})</option>'
                    for c in channels
                ]
            ),
        )
        .replace("{% endfor %}", "")
    )

    # Render User Rows
    user_rows = ""
    for u in users:
        user_rows += f"""
        <tr>
            <td><code>{u['id']}</code></td>
            <td><strong>{u['name']}</strong></td>
            <td>
                <form action="/update-user" method="POST" style="display:inline;">
                    <input type="hidden" name="user_id" value="{u['id']}">
                    <input type="number" name="count" value="{u['count']}" min="0">
                    <button type="submit">Override</button>
                </form>
            </td>
            <td>
                <form action="/remove-user" method="POST" style="display:inline;">
                    <input type="hidden" name="user_id" value="{u['id']}">
                    <button type="submit" class="btn-danger">Remove</button>
                </form>
            </td>
        </tr>
        """

    # Inject table rows into HTML
    start_tag = "<tbody>"
    end_tag = "</tbody>"
    pre = rendered_html.split(start_tag)[0]
    post = rendered_html.split(end_tag)[1]
    final_html = f"{pre}<tbody>{user_rows}</tbody>{post}"

    return web.Response(text=final_html, content_type="text/html")


async def handle_set_channel(request: web.Request):
    global ALLOWED_CHANNEL_ID
    data = await request.post()
    channel_id = int(data.get("channel_id", 0))
    ALLOWED_CHANNEL_ID = channel_id
    save_allowed_channel_id(channel_id)
    return web.HTTPFound("/")


async def handle_update_user(request: web.Request):
    data = await request.post()
    user_id = str(data.get("user_id"))
    count = int(data.get("count", 0))

    adje_service.adjes[user_id] = count
    adje_service._save_counter()
    return web.HTTPFound("/")


async def handle_remove_user(request: web.Request):
    data = await request.post()
    user_id = str(data.get("user_id"))
    adje_service.remove_user(user_id)
    return web.HTTPFound("/")


async def handle_clear_all(request: web.Request):
    adje_service.clear_all()
    return web.HTTPFound("/")


# --- START BOT & WEB SERVER CONCURRENTLY ---


async def main():
    # Setup AIOHTTP web app
    app = web.Application()
    app.router.add_get("/", handle_dashboard)
    app.router.add_post("/set-channel", handle_set_channel)
    app.router.add_post("/update-user", handle_update_user)
    app.router.add_post("/remove-user", handle_remove_user)
    app.router.add_post("/clear-all", handle_clear_all)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 5000)
    await site.start()
    print("🌐 Dashboard web server running on http://localhost:5000")

    # Start Discord Bot
    async with bot:
        await bot.start(BOT_TOKEN)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())