# Snitch Mirror Discord Bot
# This simple bot script will mirror snitch messages from one channel to another, rounding coordinates to the nearest 20th for security. Feel free to incorporate this with our Global Snitch Network bot!

import re
import asyncio
import discord
from discord.ext import commands

DISCORD_TOKEN = XXXXXXXXXX

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

SNITCH_CHANNEL_ID               = XXXXXXXXXXXXXXXX
BORDER_SNITCH_CHANNEL_ID        = XXXXXXXXXXXXXXXX

MIRROR_SNITCH_CHANNEL_ID        = XXXXXXXXXXXXXXXX
MIRROR_BORDERSNITCH_CHANNEL_ID  = XXXXXXXXXXXXXXXX

SNITCH_RE             = re.compile(
    r'`?\[(?P<time>\d{2}:\d{2}:\d{2})\]`?\s+'
    r'`?\[(?P<channel>[^\]]+)\]`?\s+'
    r'\*{0,2}(?P<ign>[A-Za-z0-9_]+)\*{0,2}\s+'
    r'(?P<action>is at|entered|logged in|logged out)'
    r'(?:\s+(?P<location>[^(]*))?'
    r'(?:\((?P<x>-?\d+),\s*(?P<y>-?\d+),\s*(?P<z>-?\d+)\))?',
    re.IGNORECASE
)

COORD_RE              = re.compile(r'\((-?\d+),\s*(-?\d+),\s*(-?\d+)\)')

SNITCH_MIRROR_MAP = {
    SNITCH_CHANNEL_ID:        MIRROR_SNITCH_CHANNEL_ID,
    BORDER_SNITCH_CHANNEL_ID: MIRROR_BORDERSNITCH_CHANNEL_ID,
}

MIRROR_QUEUES:        dict[int, list] = {}
MIRROR_TASKS:         dict[int, asyncio.Task] = {}

def fuzz_coordinates(content: str, radius: int = 20) -> str:
    def replace_coord(m):
        try:
            x = round(int(m.group(1)) / radius) * radius
            y = round(int(m.group(2)) / radius) * radius
            z = round(int(m.group(3)) / radius) * radius
            return f"({x},{y},{z})"
        except (ValueError, TypeError):
            return m.group(0)
    try:
        return COORD_RE.sub(replace_coord, content)
    except Exception:
        return content
    
async def flush_mirror_queue(channel_id: int):
    await asyncio.sleep(2)
    messages = MIRROR_QUEUES.pop(channel_id, [])
    if not messages:
        return
    channel = bot.get_channel(channel_id)
    if not channel:
        try:
            channel = await bot.fetch_channel(channel_id)
        except Exception as e:
            print(f"[MIRROR ERROR] Could not fetch channel {channel_id}: {e}")
            return
    combined = "\n".join(messages)
    while combined:
        chunk    = combined[:2000]
        combined = combined[2000:]
        try:
            await channel.send(chunk)
        except Exception as e:
            print(f"[MIRROR] Failed to send batch: {e}")
    MIRROR_TASKS.pop(channel_id, None)
    
async def queue_mirror_message(channel_id: int, content: str):
    if channel_id not in MIRROR_QUEUES:
        MIRROR_QUEUES[channel_id] = []
    MIRROR_QUEUES[channel_id].append(content)
    if channel_id not in MIRROR_TASKS or MIRROR_TASKS[channel_id].done():
        MIRROR_TASKS[channel_id] = asyncio.create_task(flush_mirror_queue(channel_id))

@bot.event
async def on_message(message):
    if message.channel.id in (SNITCH_CHANNEL_ID, MIRROR_BORDERSNITCH_CHANNEL_ID):
        content = message.content

        mirror_channel_id = SNITCH_MIRROR_MAP.get(message.channel.id)
        if mirror_channel_id:
            fuzzed = fuzz_coordinates(content)
            await queue_mirror_message(mirror_channel_id, fuzzed)

bot.run(DISCORD_TOKEN)