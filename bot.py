import os
import asyncio
import logging
import tempfile
import fitz

from fastapi import FastAPI
from telegram import Update, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ["BOT_TOKEN"]

app = FastAPI()
bot_app = Application.builder().token(TOKEN).build()

@app.get("/")
async def home():
    return {"status": "PDF JPG Bot ishlayapti!"}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📄 PDF → JPG botiga xush kelibsiz!\n\n"
        "PDF faylingizni yuboring. Har bir sahifani JPG qilib beraman."
    )

async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    doc = msg.document

    if not doc.file_name.lower().endswith(".pdf"):
        await msg.reply_text("Faqat PDF fayl yuboring.")
        return

    if doc.file_size > 20 * 1024 * 1024:
        await msg.reply_text("Fayl hajmi 20 MB dan oshmasligi kerak.")
        return

    status = await msg.reply_text("⏳ PDF o‘zgartirilmoqda...")

    try:
        with tempfile.TemporaryDirectory() as folder:
            pdf_path = os.path.join(folder, "input.pdf")
            tg_file = await context.bot.get_file(doc.file_id)
            await tg_file.download_to_drive(pdf_path)

            pdf = fitz.open(pdf_path)

            if len(pdf) == 0:
                await status.edit_text("PDF fayl bo‘sh.")
                return

            paths = []

            for i, page in enumerate(pdf):
                pix = page.get_pixmap(
                    matrix=fitz.Matrix(2, 2),
                    alpha=False
                )
                path = os.path.join(folder, f"page_{i+1}.jpg")
                pix.save(path, jpg_quality=90)
                paths.append(path)

            pdf.close()

            await status.edit_text(
                f"✅ Tayyor! {len(paths)} ta sahifa."
            )

            for start_index in range(0, len(paths), 10):
                batch = paths[start_index:start_index + 10]

                if len(batch) == 1:
                    with open(batch[0], "rb") as photo:
                        await msg.reply_photo(photo=photo)
                else:
                    files = [open(p, "rb") for p in batch]
                    try:
                        media = [
                            InputMediaPhoto(media=f)
                            for f in files
                        ]
                        await msg.reply_media_group(media=media)
                    finally:
                        for f in files:
                            f.close()

    except Exception:
        logging.exception("Conversion error")
        await status.edit_text("❌ Xatolik! PDF faylni tekshiring.")

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(
    MessageHandler(filters.Document.ALL, convert)
)

@app.on_event("startup")
async def startup():
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()

@app.on_event("shutdown")
async def shutdown():
    await bot_app.updater.stop()
    await bot_app.stop()
    await bot_app.shutdown()