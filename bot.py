
import io
import os
import asyncio
from aiohttp import web, ClientSession
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter

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

FONT_REG = "FreeSans.ttf"
FONT_BOLD = "FreeSansBold.ttf"
FONT_SERIF = "FreeSerif.ttf"
FONT_SERIF_BOLD = "FreeSerifBold.ttf"

if not TOKEN:
    raise RuntimeError("Thieu bien moi truong DISCORD_TOKEN")

if WELCOME_CHANNEL_ID == 0:
    raise RuntimeError("Thieu bien moi truong WELCOME_CHANNEL_ID")


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        # Nếu không tìm thấy file font, tự động dùng font mặc định của Pillow
        return ImageFont.load_default()


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
    try:
        base_img = Image.open("welcome_template.png").convert("RGBA")
    except FileNotFoundError:
        base_img = Image.new("RGBA", (1000, 600), (15, 15, 15, 255))

    # Lấy tỷ lệ thực tế của file ảnh mẫu bạn tải lên
    img_w, img_h = base_img.size

    # 1. Avatar: Tăng kích thước lên 290px và căn chính giữa khung nguyệt quế bên phải
    avatar_size = int(img_h * 0.38) # Tự động co giãn theo cỡ ảnh mẫu
    
    try:
        avatar_url = member.display_avatar.replace(format="png", size=512).url
        avatar_bytes = await download_image(str(avatar_url))
        avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    except Exception:
        avatar_img = Image.new("RGBA", (avatar_size, avatar_size), (100, 100, 100, 255))

    avatar_cropped = circle_crop(avatar_img, avatar_size)

    # Tọa độ khung tròn vàng bên phải
    avatar_x = int(img_w * 0.585) 
    avatar_y = int(img_h * 0.280)
    base_img.alpha_composite(avatar_cropped, (avatar_x, avatar_y))

    draw = ImageDraw.Draw(base_img)

    # 2. Tên Username: Viết to rõ dưới chữ WELCOME,
    username = f"@{member.display_name}"
    if len(username) > 16:
        username = username[:15] + "…"

    # Căn giữa vùng bên trái (dưới chữ WELCOME,)
    draw_text_center(
        draw,
        (int(img_w * 0.12), int(img_h * 0.500), int(img_w * 0.48), int(img_h * 0.570)),
        username,
        font(FONT_BOLD, int(img_h * 0.065)),  # Tăng cỡ chữ to rõ
        WHITE,
    )

    # 3. Số thứ tự thành viên (Ví dụ: 1,234)
    member_count_str = f"{member.guild.member_count:,}"
    draw_text_center(
        draw,
        (int(img_w * 0.12), int(img_h * 0.630), int(img_w * 0.48), int(img_h * 0.720)),
        member_count_str,
        font(FONT_BOLD, int(img_h * 0.080)),  # Font chữ to nổi bật
        GOLD_LIGHT,
    )

    # 4. Số lượng thành viên ở khung nhỏ phía dưới (MEMBER COUNT)
    draw_text_center(
        draw,
        (int(img_w * 0.44), int(img_h * 0.810), int(img_w * 0.55), int(img_h * 0.870)),
        member_count_str,
        font(FONT_BOLD, int(img_h * 0.028)),
        WHITE,
    )

    output = io.BytesIO()
    base_img.convert("RGB").save(output, format="PNG", optimize=True)
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

bot = commands.Bot(command_prefix="!", intents=intents)


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
    
@bot.command(name="testwelcome")
async def testwelcome(ctx):
    try:
        await ctx.send("⏳ Đang tạo ảnh test welcome...")
        
        # 1. Tạo ảnh card
        card = await create_welcome_card(ctx.author)
        
        # 2. Gửi thẳng vào kênh vừa gõ lệnh (ctx.channel)
        await ctx.send(
            content=f"Chào mừng {ctx.author.mention} đến với ANH THU COMMUNITY!",
            file=discord.File(card, filename="welcome.png")
        )
        await ctx.send("✅ Đã tạo ảnh thành công!")
        
    except Exception as e:
        # Nếu vẽ ảnh lỗi (thiếu file nền, sai font...), lỗi sẽ báo ngay ra Discord
        await ctx.send(f"❌ Lỗi khi tạo ảnh: `{e}`")

async def main():
    await start_web_server()
    await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
