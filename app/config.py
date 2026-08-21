"""Server-side configuration, read from environment variables.

Kept as one module so nothing else in the app reaches into `os.environ` directly — in
particular, the Mailtrap token lives only here and only on the server. It never goes to the
Android client, which is the whole point of moving e-mail sending into this API.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()  # reads .env in the working directory, if present — no-op in prod where the host injects env vars directly

MAILTRAP_API_URL = os.environ.get("MAILTRAP_API_URL", "https://send.api.mailtrap.io/api/send")
MAILTRAP_API_TOKEN = os.environ.get("MAILTRAP_API_TOKEN", "")
MAILTRAP_SENDER_EMAIL = os.environ.get("MAILTRAP_SENDER_EMAIL", "relatos@urbansense.ai")
MAILTRAP_SENDER_NAME = os.environ.get("MAILTRAP_SENDER_NAME", "UrbanSense AI")

DEFAULT_CITY_HALL_EMAIL = os.environ.get("DEFAULT_CITY_HALL_EMAIL", "marcio.flima@upe.br")
DEFAULT_CITY_HALL_NAME = os.environ.get("DEFAULT_CITY_HALL_NAME", "Prefeitura Municipal de Surubim")
