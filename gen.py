import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import time

# ---- CONFIG ----
TARGET_GUILD_ID = 1384939779052929044  # Replace with your server ID
PREMIUM_ROLE_ID = (1384939779078230269, 1384939779052929051)  # Tuple of premium role IDs
FREE_GEN_ROLE_ID = 1384939779052929047  # Replace with your actual Free Gen Access role ID
STOCK_FILE = "stock_data.json"

# ---- Setup ----
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
user_cooldowns = {}

def load_stock():
    if not os.path.exists(STOCK_FILE):
        with open(STOCK_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
    with open(STOCK_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_stock(data):
    with open(STOCK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

async def is_admin_or_owner(interaction: discord.Interaction) -> bool:
    guild = interaction.guild
    if guild is None:
        return False
    member = guild.get_member(interaction.user.id)
    if member is None:
        return False
    return member.guild_permissions.administrator or (interaction.user.id == guild.owner_id)

def get_cooldown_seconds(member: discord.Member):
    return 5 * 60 if any(role.id in PREMIUM_ROLE_ID for role in member.roles) else 60 * 60

# ---- Slash Commands ----

@bot.tree.command(name="createstock", description="Create a new stock section with access type")
@app_commands.guilds(discord.Object(id=TARGET_GUILD_ID))
@app_commands.describe(
    name="Name of the stock section",
    icon="Emoji icon for the stock (default 📦)",
    access="Access type: free or premium (default free)"
)
async def createstock(interaction: discord.Interaction, name: str, icon: str = "📦", access: str = "free"):
    if not await is_admin_or_owner(interaction):
        await interaction.response.send_message("❌ You must be an admin or the server owner to use this command.", ephemeral=True)
        return

    access = access.lower()
    if access not in ["free", "premium"]:
        await interaction.response.send_message("❌ Access must be 'free' or 'premium'.", ephemeral=True)
        return

    stock = load_stock()
    if name in stock:
        await interaction.response.send_message(f"❌ Stock `{name}` already exists.", ephemeral=True)
        return

    stock[name] = {"icon": icon, "items": [], "access": access}
    save_stock(stock)
    await interaction.response.send_message(f"✅ Created stock `{name}` with access `{access}` and icon {icon}.", ephemeral=True)

@bot.tree.command(name="addstockfile", description="Add stock from a .txt file")
@app_commands.guilds(discord.Object(id=TARGET_GUILD_ID))
async def addstockfile(interaction: discord.Interaction, name: str, file: discord.Attachment):
    if not await is_admin_or_owner(interaction):
        await interaction.response.send_message("❌ You must be an admin or the server owner to use this command.", ephemeral=True)
        return

    stock = load_stock()
    if name not in stock:
        await interaction.response.send_message(f"❌ Stock `{name}` does not exist.", ephemeral=True)
        return

    if not file.filename.endswith(".txt"):
        await interaction.response.send_message("❌ Only `.txt` files are supported.", ephemeral=True)
        return

    content = await file.read()
    lines = content.decode("utf-8").splitlines()
    added = 0

    for line in lines:
        if line.strip():
            stock[name]["items"].append(line.strip())
            added += 1

    save_stock(stock)
    await interaction.response.send_message(f"✅ Added `{added}` lines to `{name}` stock.", ephemeral=True)

@bot.tree.command(name="clearstock", description="Clear all entries from a stock section")
@app_commands.guilds(discord.Object(id=TARGET_GUILD_ID))
async def clearstock(interaction: discord.Interaction, name: str):
    if not await is_admin_or_owner(interaction):
        await interaction.response.send_message("❌ You must be an admin or the server owner to use this command.", ephemeral=True)
        return

    stock = load_stock()
    if name not in stock:
        await interaction.response.send_message(f"❌ Stock `{name}` does not exist.", ephemeral=True)
        return

    stock[name]["items"] = []
    save_stock(stock)
    await interaction.response.send_message(f"✅ Cleared all entries from `{name}` stock.", ephemeral=True)

@bot.tree.command(name="removestock", description="Completely delete a stock section")
@app_commands.guilds(discord.Object(id=TARGET_GUILD_ID))
async def removestock(interaction: discord.Interaction, name: str):
    if not await is_admin_or_owner(interaction):
        await interaction.response.send_message("❌ You must be an admin or the server owner to use this command.", ephemeral=True)
        return

    stock = load_stock()
    if name not in stock:
        await interaction.response.send_message(f"❌ Stock `{name}` does not exist.", ephemeral=True)
        return

    del stock[name]
    save_stock(stock)
    await interaction.response.send_message(f"✅ Removed stock section `{name}`.", ephemeral=True)

@bot.tree.command(name="sendpanel", description="Send the stock panel with available stocks")
@app_commands.guilds(discord.Object(id=TARGET_GUILD_ID))
async def sendpanel(interaction: discord.Interaction):
    if not await is_admin_or_owner(interaction):
        await interaction.response.send_message("❌ You must be an admin or the server owner to use this command.", ephemeral=True)
        return

    stock_data = load_stock()
    view = StockView(stock_data)

    gif_url = "https://api.gamingbanners.com/out/ecc5a8bc1qlr2e5xvzc4kq3qmzmlhmjlclz66ctu3wgg2y6w.gif"

    embed = discord.Embed(
        title="🎁 Stock Panel",
        description="Choose a stock category below and receive your items instantly!",
        color=discord.Color.blurple()
    )
    embed.set_image(url=gif_url)

    await interaction.response.send_message(embed=embed, view=view)

class StockView(discord.ui.View):
    def __init__(self, stock_data):
        super().__init__(timeout=None)
        self.stock_data = stock_data
        for name, data in stock_data.items():
            count = len(data["items"])
            emoji = data.get("icon", "")
            access = data.get("access", "free")

            label = f"{emoji} {name.title()}"
            style = discord.ButtonStyle.green if access == "free" else discord.ButtonStyle.red
            if count == 0:
                style = discord.ButtonStyle.secondary

            self.add_item(discord.ui.Button(
                label=label,
                style=style,
                custom_id=f"stock_{name}",
                disabled=(count == 0)
            ))

    @discord.ui.button(label="Check Stock", style=discord.ButtonStyle.secondary, custom_id="check_stock")
    async def check_stock(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
        stock_data = load_stock()
        msg = ""
        for name, data in stock_data.items():
            icon = data.get("icon", "📦")
            msg += f"{icon} **{name.title()}** ({data.get('access', 'free')}): `{len(data['items'])}` left\n"
        await interaction_btn.response.send_message(msg or "No stock available.", ephemeral=True)

@bot.event
async def on_ready():
    print("🔔 on_ready triggered")
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=TARGET_GUILD_ID))
        print(f"✅ Synced {len(synced)} slash commands to guild {TARGET_GUILD_ID}")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")
    print(f"🤖 Logged in as: {bot.user}")
    print(f"📌 Connected to guilds: {[guild.name + ' (' + str(guild.id) + ')' for guild in bot.guilds]}")
    print("✅ Ready!")

@bot.event
async def on_interaction(interaction_btn: discord.Interaction):
    if interaction_btn.type == discord.InteractionType.component:
        cid = interaction_btn.data.get("custom_id", "")
        if cid.startswith("stock_"):
            stock_name = cid[6:]
            member = interaction_btn.user
            stock_data = load_stock()

            # Free Gen Access Role Check
            if FREE_GEN_ROLE_ID not in [role.id for role in member.roles]:
                await interaction_btn.response.send_message(
                    "🛑 You must put our vanity tag in your status and get the **Free Gen Access** role to use the generator.\n"
                    "📌 Update your status And You Will Recieve Access Shortyl!",
                    ephemeral=True
                )
                return

            if stock_name not in stock_data:
                await interaction_btn.response.send_message(f"❌ Stock `{stock_name}` does not exist.", ephemeral=True)
                return

            stock_section = stock_data[stock_name]
            access = stock_section.get("access", "free")

            if access == "premium" and not any(role.id in PREMIUM_ROLE_ID for role in member.roles):
                await interaction_btn.response.send_message(
                    "⛔ You need the premium role to access this stock section.", ephemeral=True)
                return

            now = time.time()
            last_used = user_cooldowns.get(member.id, 0)
            cooldown = get_cooldown_seconds(member)
            remaining = cooldown - (now - last_used)
            if remaining > 0:
                minutes = int(remaining // 60)
                seconds = int(remaining % 60)
                await interaction_btn.response.send_message(
                    f"⏳ You are on cooldown. Please wait {minutes}m {seconds}s before generating again.",
                    ephemeral=True)
                return

            if not stock_section["items"]:
                await interaction_btn.response.send_message(f"⚠️ No accounts left in `{stock_name}` stock.", ephemeral=True)
                return

            account = stock_section["items"].pop(0)
            save_stock(stock_data)

            user_cooldowns[member.id] = now

            icon = stock_section.get("icon", "📦")
            embed = discord.Embed(
                title=f"{icon} Generated from {stock_name.title()}",
                description=f"```\n{account}\n```",
                color=discord.Color.blue()
            )

            try:
                await member.send(embed=embed)
                await interaction_btn.response.send_message("📬 Account has been sent to your DMs!", ephemeral=True)
            except discord.Forbidden:
                await interaction_btn.response.send_message(
                    "❌ I couldn't DM you. Please enable DMs from server members.",
                    ephemeral=True
                )
            return

    await bot.process_application_commands(interaction_btn)

# Run the bot with your token
bot.run('MTM1NTY4NTkxNzM3Mjk3NzM2NA.Gxz5L5.rN8g2cYzcPS4Lr2kxO6makz47XBRibLXEgFaxE')