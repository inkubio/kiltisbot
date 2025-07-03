import time
import io
from PIL import Image
import httpx

# Muuttujat analyysin ja aikaleiman tallentamiseen globaalisti (tai esim. config-tiedostoon)
_last_analysis = None
_last_analysis_time = 0

def analyze_coffee(image: Image.Image) -> int:
    """
    Tässä sinun analyysifunktio, joka laskee tumma pikseliä yms.
    Palauttaa analyysin tuloksen (esim. tumma pikselimäärä).
    """
    # Esimerkki: lasketaan tumma pikseli (dummy)
    grayscale = image.convert("L")
    pixels = grayscale.load()
    width, height = image.size
    dark_pixel_count = 0
    for x in range(width):
        for y in range(height):
            if pixels[x, y] < 50:
                dark_pixel_count += 1
    return dark_pixel_count


async def get_coffee_analysis():
    global _last_analysis, _last_analysis_time

    now = time.time()
    # Jos analyysi on tehty alle 3 min sitten, käytetään välimuistia
    if _last_analysis is not None and (now - _last_analysis_time) < 180:
        return _last_analysis

    # Pyydetään uusi kuva
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post("http://localhost:6000")
            resp.raise_for_status()
            content = resp.content
    except httpx.RequestError as e:
        raise RuntimeError(f"Could not fetch coffee image: {e}")

    image = Image.open(io.BytesIO(content))

    # Analysoidaan kuva
    result = analyze_coffee(image)

    # Tallennetaan tulos ja aikaleima
    _last_analysis = result
    _last_analysis_time = now

    return result