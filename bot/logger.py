import logging

# Basic format and level
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Don't log every httpx GET/POST-request
logging.getLogger("httpx").setLevel(logging.WARNING)

# Create a logger that other files can use
logger = logging.getLogger("kiltisbot")
