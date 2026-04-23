python bot.py

from telegram import Update, InputMediaPhoto
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from datetime import datetime
from collections import defaultdict
import time
import asyncio

TOKEN = "8662800561:AAGi26Faa8apHIKhua7XtjcfjWIRZUz_-kM"
CHANNEL_ID = -1003475968613

user_last_message = {}
user_warned = {}

media_groups = defaultdict(list)
media_group_locks = set()


async def process_album(context, media_group_id, header):
    # wait para ma-collect lahat ng photos
    await asyncio.sleep(3)

    if media_group_id in media_group_locks:
        return
    media_group_locks.add(media_group_id)

    msgs = media_groups.pop(media_group_id, [])
    if not msgs:
        media_group_locks.discard(media_group_id)
        return

    msgs.sort(key=lambda m: m.message_id)

    extra_caption = ""
    for m in msgs:
        if m.caption:
            extra_caption = f"\n💬 Message:\n{m.caption}"
            break

    media = []
    for i, m in enumerate(msgs):
        if m.photo:
            caption = (header + extra_caption) if i == 0 else None
            media.append(InputMediaPhoto(m.photo[-1].file_id, caption=caption))

    if media:
        try:
            await context.bot.send_media_group(
                chat_id=CHANNEL_ID,
                media=media
            )
        except Exception as e:
            print(f"Album send error: {e}")

    media_group_locks.discard(media_group_id)


async def forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    msg = update.message
    user = msg.from_user
    user_id = user.id if user else 0
    current_time = time.time()

    # ===== ANTI-SPAM — exempt ang album =====
    if not msg.media_group_id:
        if user_id in user_last_message:
            if current_time - user_last_message[user_id] < 120:
                if not user_warned.get(user_id):
                    await msg.reply_text("⏳ Please wait before sending again.")
                    user_warned[user_id] = True
                return
        user_warned[user_id] = False
        user_last_message[user_id] = current_time
    # ========================================

    name = user.first_name if user else "Unknown"
    username = f"@{user.username}" if user and user.username else "No username"
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    header = f"""📩 NEW FEEDBACK

👤 Name: {name}
🔗 User: {username}
🕒 Time: {time_now}
"""

    # ===== ALBUM =====
    if msg.media_group_id:
        is_first = msg.media_group_id not in media_groups and \
                   msg.media_group_id not in media_group_locks

        media_groups[msg.media_group_id].append(msg)
        user_last_message[user_id] = current_time

        # only first message triggers the task
        if is_first:
            asyncio.create_task(
                process_album(context, msg.media_group_id, header)
            )
        return

    # ===== SINGLE IMAGE =====
    if msg.photo:
        text = msg.caption or ""
        await context.bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=msg.photo[-1].file_id,
            caption=header + (f"\n💬 Message:\n{text}" if text else "")
        )

    # ===== TEXT =====
    elif msg.text:
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=header + f"\n💬 Message:\n{msg.text}"
        )

    # ===== VIDEO =====
    elif msg.video:
        text = msg.caption or ""
        await context.bot.send_video(
            chat_id=CHANNEL_ID,
            video=msg.video.file_id,
            caption=header + (f"\n💬 Message:\n{text}" if text else "")
        )

    # ===== FILE =====
    elif msg.document:
        text = msg.caption or ""
        await context.bot.send_document(
            chat_id=CHANNEL_ID,
            document=msg.document.file_id,
            caption=header + (f"\n💬 Message:\n{text}" if text else "")
        )


app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(~filters.COMMAND, forward))

print("Bot running...")
app.run_polling()