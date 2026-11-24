import os
import re
import discord
from discord.ext import commands

# ==============================
# CẤU HÌNH
# ==============================

TOKEN = os.getenv("DISCORD_TOKEN")

# Để 0 nếu muốn bot kiểm tra mọi kênh mà bot có quyền đọc.
# Hoặc nhập ID kênh cụ thể, ví dụ:
# WATCH_CHANNEL_ID = 1495362331964870819
WATCH_CHANNEL_ID = 0

# ID kênh ghi log. Để 0 thì chỉ ghi log trong console.
LOG_CHANNEL_ID = 0

# ID chủ bot
OWNER_ID = 1356498767788118099

# Độ dài tin nhắn để áp dụng điều kiện bỏ qua
MAX_SHORT_MESSAGE_LENGTH = 30


# ==============================
# DISCORD SETUP
# ==============================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ==============================
# TỪ KHÓA NHẬN DIỆN PHÒNG LQ
# ==============================

ROOM_KEYWORDS = [
    "liên quân",
    "lien quan",
    "lq",
    "id phòng",
    "id phong",
    "mã phòng",
    "ma phong",
    "phòng lq",
    "phong lq",
    "room lq",
    "room",
    "vào phòng",
    "vao phong",
    "join phòng",
    "join phong",
    "custom"
]


# ==============================
# XỬ LÝ LINK
# ==============================

URL_PATTERN = re.compile(
    r"(?:https?://|www\.)\S+",
    re.IGNORECASE
)


def remove_urls(text: str) -> str:
    """
    Loại bỏ URL trước khi quét ID.
    ID nằm bên trong link sẽ không bị bắt.
    """
    return URL_PATTERN.sub(" ", text)


# ==============================
# KIỂM TRA TỪ KHÓA LQ
# ==============================

def has_room_keyword(text: str) -> bool:
    text_lower = text.lower()

    return any(
        keyword in text_lower
        for keyword in ROOM_KEYWORDS
    )


# ==============================
# KIỂM TRA SỐ LẶP
# ==============================

def is_all_same_digits(number: str) -> bool:
    """
    Ví dụ bỏ qua:
    111111
    222222
    7777777
    """
    return len(set(number)) == 1


# ==============================
# KIỂM TRA DÃY LIÊN TIẾP
# ==============================

def is_sequential(number: str) -> bool:
    """
    Bỏ qua dãy tăng hoặc giảm liên tiếp.

    Ví dụ:
    123456
    234567
    654321
    7654321
    """

    digits = [int(char) for char in number]

    increasing = all(
        digits[i + 1] == digits[i] + 1
        for i in range(len(digits) - 1)
    )

    decreasing = all(
        digits[i + 1] == digits[i] - 1
        for i in range(len(digits) - 1)
    )

    return increasing or decreasing


# ==============================
# TÌM ID 6–7 SỐ
# ==============================

ID_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])\d{6,7}(?![A-Za-z0-9])"
)


def find_room_ids(message_content: str):
    """
    Trả về danh sách ID phù hợp trong tin nhắn.
    """

    # Bỏ link trước
    cleaned_text = remove_urls(message_content)

    # Tìm các dãy 6 hoặc 7 số đứng riêng
    matches = ID_PATTERN.findall(cleaned_text)

    valid_ids = []

    for number in matches:

        # Bỏ số lặp hoàn toàn
        if is_all_same_digits(number):
            continue

        # Bỏ dãy tăng/giảm liên tiếp
        if is_sequential(number):
            continue

        valid_ids.append(number)

    return valid_ids


# ==============================
# KIỂM TRA TIN NHẮN
# ==============================

def should_check_message(content: str) -> bool:
    """
    Tin nhắn <= 30 ký tự:
        Có thể kiểm tra ID đứng riêng.

    Tin nhắn > 30 ký tự:
        Chỉ kiểm tra nếu có từ khóa phòng Liên Quân.
    """

    if len(content) <= MAX_SHORT_MESSAGE_LENGTH:
        return True

    if has_room_keyword(content):
        return True

    return False


# ==============================
# GỬI LOG
# ==============================

async def send_log(message: discord.Message, detected_ids):

    log_text = (
        "🚨 **Phát hiện ID phòng có thể là Liên Quân**\n"
        f"👤 Thành viên: {message.author.mention}\n"
        f"📍 Kênh: {message.channel.mention}\n"
        f"🔢 ID phát hiện: `{', '.join(detected_ids)}`\n"
        f"📝 Nội dung: {message.content[:500]}"
    )

    print(log_text)

    if LOG_CHANNEL_ID == 0:
        return

    log_channel = bot.get_channel(LOG_CHANNEL_ID)

    if log_channel is None:
        try:
            log_channel = await bot.fetch_channel(LOG_CHANNEL_ID)
        except Exception:
            return

    try:
        await log_channel.send(log_text)
    except Exception as error:
        print("Không gửi được log:", error)


# ==============================
# ON READY
# ==============================

@bot.event
async def on_ready():

    print("=" * 40)
    print(f"Bot đã đăng nhập: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print("Chức năng: Bắt ID phòng Liên Quân")
    print("=" * 40)

    try:
        synced = await bot.tree.sync()
        print(f"Đã đồng bộ {len(synced)} slash command")
    except Exception as error:
        print("Lỗi đồng bộ command:", error)


# ==============================
# KIỂM TRA TIN NHẮN
# ==============================

@bot.event
async def on_message(message: discord.Message):

    # Bỏ qua tin nhắn bot
    if message.author.bot:
        return

    # Chỉ xử lý trong server
    if message.guild is None:
        return

    # Bỏ qua kênh không được cấu hình
    if WATCH_CHANNEL_ID != 0:
        if message.channel.id != WATCH_CHANNEL_ID:
            return

    content = message.content.strip()

    if not content:
        return

    # Tin nhắn dài hơn 30 ký tự phải có từ khóa LQ
    if not should_check_message(content):
        return

    # Tìm ID
    detected_ids = find_room_ids(content)

    if not detected_ids:
        return

    # Nếu tin nhắn dài hơn 30 ký tự,
    # yêu cầu phải có từ khóa phòng Liên Quân
    if len(content) > MAX_SHORT_MESSAGE_LENGTH:
        if not has_room_keyword(content):
            return

    # Xoá tin nhắn
    try:
        await message.delete()

        print(
            f"[ĐÃ XOÁ] {message.author} | "
            f"ID: {detected_ids}"
        )

    except discord.Forbidden:
        print(
            "Bot không có quyền xoá tin nhắn "
            "trong kênh này."
        )
        return

    except discord.NotFound:
        return

    except Exception as error:
        print("Lỗi xoá tin nhắn:", error)
        return

    # Gửi log
    await send_log(message, detected_ids)

    # Cho phép các command prefix hoạt động nếu có
    await bot.process_commands(message)


# ==============================
# COMMAND KIỂM TRA BOT
# ==============================

@bot.tree.command(
    name="kiemtra",
    description="Kiểm tra bot bắt ID phòng Liên Quân"
)
async def kiemtra(interaction: discord.Interaction):

    await interaction.response.send_message(
        "✅ Bot đang hoạt động và sẵn sàng kiểm tra ID phòng.",
        ephemeral=True
    )


# ==============================
# COMMAND TEST ID
# ==============================

@bot.tree.command(
    name="testid",
    description="Kiểm tra một chuỗi có chứa ID phòng hay không"
)
async def testid(
    interaction: discord.Interaction,
    noidung: str
):

    # Chỉ chủ bot được dùng
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message(
            "Bạn không có quyền sử dụng lệnh này.",
            ephemeral=True
        )
        return

    if not should_check_message(noidung):
        await interaction.response.send_message(
            "Tin nhắn dài hơn 30 ký tự và không có từ khóa phòng LQ.",
            ephemeral=True
        )
        return

    detected_ids = find_room_ids(noidung)

    if not detected_ids:
        await interaction.response.send_message(
            "❌ Không phát hiện ID phù hợp.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"✅ Phát hiện ID: `{', '.join(detected_ids)}`",
        ephemeral=True
    )


# ==============================
# CHẠY BOT
# ==============================

if not TOKEN:
    raise RuntimeError(
        "Chưa thiết lập DISCORD_TOKEN trong Variables."
    )

bot.run(TOKEN)