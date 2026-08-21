
import io
import os
import asyncio
import static_ffmpeg
static_ffmpeg.add_paths()
from aiohttp import web, ClientSession
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import yt_dlp

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractflat': False,
    'noplaylist': True,
    'quiet': True,
    'default_search': 'scsearch',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

TOKEN = os.getenv("DISCORD_TOKEN")
PORT = int(os.getenv("PORT", "10000"))

# Welcome settings
WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID", "0"))
AUTO_ROLE_ID = int(os.getenv("AUTO_ROLE_ID=0", "0"))

# Existing image-reply feature
CHANNEL_IDS = {
    int(x.strip())
    for x in os.getenv("CHANNEL_IDS", "").split(",")
    if x.strip()
}
REPLY_IMAGE = "discord_profile_themes.jpg"

CARD_WIDTH = 1024
CARD_HEIGHT = 512
GOLD = (224, 190, 112, 255)
GOLD_LIGHT = (255, 225, 155, 255)
CREAM = (245, 235, 210, 255)
WHITE = (255, 255, 255, 255)
BLACK = (7, 7, 8, 255)
PANEL = (15, 14, 13, 235)

FONT_REG = "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
FONT_SERIF = "/usr/share/fonts/truetype/freefont/FreeSerif.ttf"
FONT_SERIF_BOLD = "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf"

if not TOKEN:
    raise RuntimeError("Thieu bien moi truong DISCORD_TOKEN")

if WELCOME_CHANNEL_ID == 0:
    raise RuntimeError("Thieu bien moi truong WELCOME_CHANNEL_ID")


def font(path, size):
    return ImageFont.truetype(path, size)


def rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size[0] - 1, size[1] - 1),
        radius=radius,
        fill=255,
    )
    return mask


def circle_crop(image, size):
    image = image.convert("RGBA")
    image.thumbnail((size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - image.width) // 2
    y = (size - image.height) // 2
    canvas.alpha_composite(image, (x, y))

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    canvas.putalpha(mask)
    return canvas


def make_background():
    img = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), BLACK)
    px = img.load()

    # Black to warm brown gradient
    for y in range(CARD_HEIGHT):
        for x in range(CARD_WIDTH):
            d = ((x - 720) ** 2 + (y - 220) ** 2) ** 0.5
            glow = max(0, 1 - d / 850)
            r = int(6 + 20 * glow)
            g = int(6 + 15 * glow)
            b = int(7 + 8 * glow)
            px[x, y] = (r, g, b, 255)

    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((620, -120, 1120, 380), fill=(210, 165, 70, 70))
    gd.ellipse((-180, 290, 380, 800), fill=(150, 105, 35, 35))
    glow = glow.filter(ImageFilter.GaussianBlur(80))
    img.alpha_composite(glow)

    return img


def draw_text_center(draw, box, text, fnt, fill):
    x1, y1, x2, y2 = box
    bbox = draw.textbbox((0, 0), text, font=fnt)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text(((x1 + x2 - w) / 2, (y1 + y2 - h) / 2 - bbox[1]), text, font=fnt, fill=fill)


async def download_image(url):
    async with ClientSession() as session:
        async with session.get(url, timeout=15) as resp:
            resp.raise_for_status()
            return await resp.read()


async def create_welcome_card(member: discord.Member):
    img = make_background()
    draw = ImageDraw.Draw(img)

    # Luxury frame
    draw.rounded_rectangle(
        (20, 20, CARD_WIDTH - 21, CARD_HEIGHT - 21),
        radius=28,
        outline=(175, 137, 62, 180),
        width=2,
    )
    draw.rounded_rectangle(
        (28, 28, CARD_WIDTH - 29, CARD_HEIGHT - 29),
        radius=22,
        outline=(88, 68, 35, 150),
        width=1,
    )

    # Decorative gold corner details
    for off in (0, 1):
        draw.line((58 + off, 72, 120 + off, 72), fill=GOLD, width=2)
        draw.line((58, 72 + off, 58, 134 + off), fill=GOLD, width=2)
        draw.line((904 - off, 440, 966 - off, 440), fill=GOLD, width=2)
        draw.line((966, 378 - off, 966, 440 - off), fill=GOLD, width=2)

    # Small top label
    draw_text_center(
        draw,
        (330, 48, 694, 102),
        "ANH THU COMMUNITY",
        font(FONT_BOLD, 22),
        GOLD,
    )

    # Welcome title
    draw_text_center(
        draw,
        (250, 92, 774, 190),
        "WELCOME",
        font(FONT_SERIF_BOLD, 70),
        CREAM,
    )

    # Avatar
    avatar_size = 170
    avatar_x = 427
    avatar_y = 168

    try:
        avatar_url = member.display_avatar.replace(format="png", size=256).url
        avatar_bytes = await download_image(str(avatar_url))
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    except Exception:
        avatar = Image.new("RGBA", (avatar_size, avatar_size), (65, 65, 65, 255))

    # Gold glow behind avatar
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gg = ImageDraw.Draw(glow)
    gg.ellipse(
        (avatar_x - 13, avatar_y - 13, avatar_x + avatar_size + 13, avatar_y + avatar_size + 13),
        outline=(238, 198, 104, 110),
        width=10,
    )
    glow = glow.filter(ImageFilter.GaussianBlur(9))
    img.alpha_composite(glow)

    draw = ImageDraw.Draw(img)
    draw.ellipse(
        (avatar_x - 7, avatar_y - 7, avatar_x + avatar_size + 7, avatar_y + avatar_size + 7),
        fill=(5, 5, 6, 255),
        outline=GOLD,
        width=3,
    )
    img.alpha_composite(circle_crop(avatar, avatar_size), (avatar_x, avatar_y))

    # Username
    username = member.display_name
    if len(username) > 24:
        username = username[:23] + "…"

    draw = ImageDraw.Draw(img)
    draw_text_center(
        draw,
        (120, 350, 904, 398),
        username,
        font(FONT_BOLD, 34),
        WHITE,
    )

    # Member count panel
    panel = (350, 407, 674, 464)
    draw.rounded_rectangle(
        panel,
        radius=18,
        fill=PANEL,
        outline=(155, 118, 54, 170),
        width=1,
    )
    label = f"MEMBER  #{member.guild.member_count:,}"
    draw_text_center(
        draw,
        panel,
        label,
        font(FONT_BOLD, 19),
        GOLD_LIGHT,
    )

    # Fine divider
    draw.line((250, 332, 774, 332), fill=(151, 117, 55, 120), width=1)

    # Bottom micro text
    draw_text_center(
        draw,
        (310, 470, 714, 493),
        "WELCOME TO THE COMMUNITY",
        font(FONT_REG, 12),
        (165, 150, 125, 255),
    )

    output = io.BytesIO()
    img.convert("RGB").save(output, format="PNG", optimize=True)
    output.seek(0)
    return output


async def health(request):
    return web.Response(text="Bot is online")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"Health server dang chay tai port {PORT}")


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=['!', ','], intents=intents)


@bot.event
async def on_ready():
    print(f"Bot da dang nhap: {bot.user}")
    print(f"Welcome channel: {WELCOME_CHANNEL_ID}")
    print(f"Dang theo doi {len(CHANNEL_IDS)} kenh cho image-reply")


@bot.event
async def on_member_join(member: discord.Member):
    try:
        # Optional auto-role
        if AUTO_ROLE_ID:
            role = member.guild.get_role(AUTO_ROLE_ID)
            if role:
                await member.add_roles(role, reason="Auto role for new member")

        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if channel is None:
            print(f"Khong tim thay welcome channel {WELCOME_CHANNEL_ID}")
            return

        card = await create_welcome_card(member)
        await channel.send(
            content=f"Chào mừng {member.mention} đến với ANH THU COMMUNITY!",
            file=discord.File(card, filename="welcome.png"),
        )
        print(f"Da gui welcome cho {member} tai guild {member.guild.id}")

    except Exception as e:
        print(f"Loi welcome: {e}")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id in CHANNEL_IDS:
        has_image = any(
            attachment.content_type
            and attachment.content_type.startswith("image/")
            for attachment in message.attachments
        )

        if has_image:
            try:
                await message.channel.send(file=discord.File(REPLY_IMAGE))
                print(f"Da gui anh tai kenh {message.channel.id}")
            except Exception as e:
                print(f"Loi gui anh: {e}")

    await bot.process_commands(message)

# ================= HỆ THỐNG PHÁT NHẠC VÀ AUTOPLAY SOUNDCLOUD =================
song_queue = []
last_played_url = None  # Lưu link bài gần nhất để gợi ý nhạc tương tự

async def play_next(ctx):
    global last_played_url
    
    # 1. Tự động tìm bài tương tự từ SoundCloud nếu hết hàng chờ
    if len(song_queue) == 0 and last_played_url:
        await ctx.send("📻 *Hết hàng chờ! Đang tự động tìm bài hát tương tự trên SoundCloud...*")
        try:
            loop = asyncio.get_event_loop()
            related_data = await loop.run_in_executor(
                None, 
                lambda: ytdl.extract_info(f"{last_played_url}", download=False)
            )
            
            related_tracks = related_data.get('related_tracks') or related_data.get('entries')
            if related_tracks and len(related_tracks) > 0:
                next_track = related_tracks[0]
                track_url = next_track.get('url') or next_track.get('webpage_url')
                song_queue.append({'query': track_url})
        except Exception as e:
            print(f"Lỗi Autoplay: {e}")

    # 2. Phát bài hát tiếp theo
    if len(song_queue) > 0:
        next_song = song_queue.pop(0)
        
        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(next_song['query'], download=False))

            if 'entries' in data and len(data['entries']) > 0:
                data = data['entries'][0]

            stream_url = data['url']
            title = data.get('title', 'Bài hát SoundCloud')
            
            last_played_url = data.get('webpage_url', next_song['query'])
            source = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS)
            
            ctx.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
            await ctx.send(f"🎵 **Đang phát:** {title}\n🔗 <{last_played_url}>")

        except Exception as e:
            await ctx.send(f"❌ Lỗi khi tải bài hát: `{e}`")
            await play_next(ctx)
    else:
        await ctx.send("✅ Không tìm thấy bài hát gợi ý mới. Dừng phát nhạc!")

@bot.command(name='play')
async def play(ctx, *, query: str):
    if not ctx.author.voice:
        return await ctx.send("❌ Bạn cần tham gia một Voice Channel trước!")

    channel = ctx.author.voice.channel

    try:
        if ctx.voice_client is None:
            await channel.connect()
        elif ctx.voice_client.channel != channel:
            await ctx.voice_client.move_to(channel)
    except Exception as e:
        return await ctx.send(f"❌ Không thể vào Voice Channel: `{e}`")

    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        song_queue.append({'query': query})
        await ctx.send(f"📥 Đã thêm vào hàng chờ (Vị trí #{len(song_queue)})")
    else:
        song_queue.append({'query': query})
        await play_next(ctx)

@bot.command(name='skip')
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Đã bỏ qua bài hát!")
    else:
        await ctx.send("Không có bài hát nào đang phát.")

@bot.command(name='stop')
async def stop(ctx):
    global song_queue, last_played_url
    song_queue.clear()
    last_played_url = None
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("🛑 Đã dừng phát nhạc, xóa lịch sử và rời kênh!")
    else:
        await ctx.send("Bot chưa vào kênh thoại nào.")
# ==============================================================================

async def main():
    await start_web_server()
    await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
