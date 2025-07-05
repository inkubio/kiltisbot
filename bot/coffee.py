import time
import io
import math
from PIL import Image
import httpx
from telegram import Update
from telegram.ext import ContextTypes
from logger import logger

# Muuttujat analyysin ja aikaleiman tallentamiseen globaalisti (tai esim. config-tiedostoon)
_last_analysis = None
_last_analysis_time = 0

async def get_coffee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Returns the current coffee level in the guildroom.
    """
    try:
        await get_coffee_analysis()
        with open("kuva.png", "rb") as pic:
            await update.get_bot().send_photo(chat_id=update.message.chat_id, photo=pic)
    except Exception as e:
        await update.message.reply_text(f"Sending photo failed: {e}")

def analyze_coffee(image: Image.Image) -> int:
    """
    Tässä sinun analyysifunktio, joka laskee tumma pikseliä yms.
    Palauttaa analyysin tuloksen (esim. tumma pikselimäärä).
    """
    # Esimerkki: lasketaan tummat pikselit
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
    global _last_analysis, _last_analysis_time

    now = time.time()
    # Jos analyysi on tehty alle 2 min sitten, käytetään välimuistia
    if _last_analysis is not None and (now - _last_analysis_time) < 120:
        return

    # Pyydetään uusi kuva
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post("http://localhost:6000")
            resp.raise_for_status()
            content = resp.content
    except httpx.RequestError as e:
        raise RuntimeError(f"Could not fetch coffee image: {e}")

    image = Image.open(io.BytesIO(content))
    image.save("kuva.png")
    # Analysoidaan kuva
    #result = analyze_coffee(image)

    # Tallennetaan tulos ja aikaleima
    #_last_analysis = result
    _last_analysis = True
    _last_analysis_time = now
    return
    