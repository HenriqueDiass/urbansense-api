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

# Email Testing (Sandbox) via SMTP — usado pra demo/pitch: nada é entregue de verdade, a
# mensagem só aparece no inbox de teste do painel do Mailtrap. Ver "My Sandbox" > Integration.
MAILTRAP_SMTP_HOST = os.environ.get("MAILTRAP_SMTP_HOST", "sandbox.smtp.mailtrap.io")
MAILTRAP_SMTP_PORT = int(os.environ.get("MAILTRAP_SMTP_PORT", "2525"))
MAILTRAP_SMTP_USERNAME = os.environ.get("MAILTRAP_SMTP_USERNAME", "")
MAILTRAP_SMTP_PASSWORD = os.environ.get("MAILTRAP_SMTP_PASSWORD", "")

MAILTRAP_SENDER_EMAIL = os.environ.get("MAILTRAP_SENDER_EMAIL", "relatos@urbansense.ai")
MAILTRAP_SENDER_NAME = os.environ.get("MAILTRAP_SENDER_NAME", "UrbanSense AI")

# True quando há credenciais suficientes pra mandar por qualquer um dos dois caminhos (API de
# Sending ou SMTP do Sandbox). main.py usa isso pra decidir se tenta notificar por e-mail.
EMAIL_CONFIGURED = bool(MAILTRAP_API_TOKEN) or bool(MAILTRAP_SMTP_USERNAME and MAILTRAP_SMTP_PASSWORD)

DEFAULT_CITY_HALL_EMAIL = os.environ.get("DEFAULT_CITY_HALL_EMAIL", "marcio.flima@upe.br")
DEFAULT_CITY_HALL_NAME = os.environ.get("DEFAULT_CITY_HALL_NAME", "Prefeitura Municipal de Surubim")
