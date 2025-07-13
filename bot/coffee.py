import time
import io
import math
from PIL import Image
import httpx
from telegram import Update
from telegram.ext import ContextTypes
from logger import logger

# Variables for saving analysis and timestamp globally (could also be in confi.py)
_last_analysis = None
_last_analysis_time = 0


async def get_coffee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Returns a picture of the coffeepot at the guildroom.
    Can also be modified to reurn an analysis of the picture and an estimated coffee amount.
    """
    try:
        await get_coffee_analysis()
        with open("kuva.png", "rb") as pic:
            await update.get_bot().send_photo(chat_id=update.message.chat_id, photo=pic)
    except Exception as e:
        await update.message.reply_text(f"Sending photo failed: {e}")


def analyze_coffee(image: Image.Image) -> int:
    """
    Here's a function to analyze the coffeepot picture.
    Returns the result of the analysis, like the proportion of dark pixels.
    """
    # Example: Count the amount of dark pixels
    grayscale = image.convert("L")
    pixels = grayscale.load()
    width, height = image.size
    dark_pixel_count = 0
    for x in range(width):
        for y in range(height):
            if pixels[x, y] < 50:
                dark_pixel_count += 1
    result = min(math.floor(dark_pixel_count/50000),100)
    return result


async def get_coffee_analysis():
    """
    Coffeepot analysis results, can be a picture or an analysis of it via the function above.
    Currently just getting the picture.
    """
    global _last_analysis, _last_analysis_time

    now = time.time()
    # If analysis done under 2 minutes ago, using cache
    if _last_analysis is not None and (now - _last_analysis_time) < 120:
        return

    # Requesting a new pic from the raspberry at the guildroom
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post("http://localhost:6000")
            resp.raise_for_status()
            content = resp.content
    except httpx.RequestError as e:
        raise RuntimeError(f"Could not fetch coffee image: {e}")

    image = Image.open(io.BytesIO(content))
    image.save("kuva.png")
    # Analyze the picture
    #result = analyze_coffee(image)

    # Save the result and a timestamp
    #_last_analysis = result
    _last_analysis = True
    _last_analysis_time = now
    return
    