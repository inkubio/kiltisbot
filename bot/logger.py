import logging

# Perusformaatti ja taso
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Älä loggaa jokaista httpx GET/POST-pyyntöä
logging.getLogger("httpx").setLevel(logging.WARNING)

# Luo logger, jota muut tiedostot voivat käyttää
logger = logging.getLogger("kiltisbot")