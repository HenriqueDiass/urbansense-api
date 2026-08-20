"""Builds and sends the occurrence-notification e-mail through the Mailtrap Send API.

Moved server-side on purpose: the Mailtrap API token is a secret, and the Android app used to
carry it in SharedPreferences — extractable from any debug build via `adb backup` or a rooted
device. Here it only ever lives in this process's environment.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape as _escape
from pathlib import Path
from typing import Optional

import requests

from app import config

GREEN_DEEP = "#295C33"
GREEN_ACTION = "#37703F"
GREEN_SOFT_BG = "#E6F1E1"
TEXT_MUTED = "#5B6B5E"
TEXT_DARK = "#1A1A1A"

# System-font stack, not a web font: Gmail, Outlook and most mail clients strip <link>/@font-face,
# so a custom font silently falls back to Times New Roman there. This stack instead resolves to
# each platform's own modern UI face — San Francisco on iOS/macOS Mail, Segoe UI on Outlook/Windows,
# Roboto on Gmail/Android — which is what makes transactional e-mail look "designed" rather than
# hand-typed, without depending on anything the client might block.
FONT_STACK = (
    "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif"
)

REPORT_PHOTO_CID = "report-photo"
LOGO_CID = "urbansense-logo"
LOGO_PATH = Path(__file__).resolve().parent / "assets" / "logo.png"


def _logo_base64() -> str:
    return base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")


@dataclass
class ReportEmailData:
    report_id: str
    latitude: float
    longitude: float
    accuracy: Optional[float]
    timestamp_iso: Optional[str]
    trigger_label: str
    device_id: Optional[str]
    city_hall_name: str
    detection_result: Optional[str] = None


@dataclass
class EmailResult:
    success: bool
    status_code: int
    message: Optional[str]


def _format_timestamp(iso_timestamp: Optional[str]) -> str:
    if not iso_timestamp:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        local = dt.astimezone()
        return local.strftime("%d/%m/%Y às %H:%M:%S")
    except ValueError:
        return iso_timestamp


def _metadata_row(label: str, value: str) -> str:
    return f"""
        <tr>
          <td style="padding:8px 0;font-size:13px;color:{TEXT_MUTED};width:150px;border-bottom:1px solid #EEF2ED;">{_escape(label)}</td>
          <td style="padding:8px 0;font-size:13px;color:{TEXT_DARK};font-weight:600;border-bottom:1px solid #EEF2ED;">{_escape(value)}</td>
        </tr>
    """


def build_subject(data: ReportEmailData) -> str:
    return "UrbanSense AI — Nova ocorrência de descarte irregular detectada"


def build_html(data: ReportEmailData) -> str:
    """Table-based HTML — e-mail clients render with a 2005-era engine, not a browser one."""
    maps_url = (
        f"https://www.openstreetmap.org/?mlat={data.latitude}&mlon={data.longitude}"
        f"#map=18/{data.latitude}/{data.longitude}"
    )
    gps = f"{data.latitude:.5f}, {data.longitude:.5f}"
    accuracy_text = f"±{data.accuracy:.0f} m" if data.accuracy is not None else "—"
    when_text = _format_timestamp(data.timestamp_iso)
    badge_label = data.detection_result or "DESCARTE IRREGULAR DETECTADO"

    detection_row = _metadata_row("Detecção da IA", data.detection_result) if data.detection_result else ""

    return f"""
        <!doctype html>
        <html lang="pt-BR">
        <body style="margin:0;padding:0;background:#EEF2ED;font-family:{FONT_STACK};-webkit-font-smoothing:antialiased;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#EEF2ED;padding:32px 0;">
            <tr><td align="center">
              <table role="presentation" width="560" cellpadding="0" cellspacing="0" style="background:#FFFFFF;border-radius:14px;overflow:hidden;box-shadow:0 1px 3px rgba(20,38,26,0.08);">

                <tr>
                  <td style="background:{GREEN_DEEP};padding:28px 32px;">
                    <table role="presentation" cellpadding="0" cellspacing="0"><tr>
                      <td style="vertical-align:middle;padding-right:12px;">
                        <img src="cid:{LOGO_CID}" width="40" height="40" alt="UrbanSense AI"
                             style="display:block;border-radius:9px;" />
                      </td>
                      <td style="vertical-align:middle;">
                        <span style="color:#FFFFFF;font-size:18px;font-weight:600;letter-spacing:-0.2px;">UrbanSense AI</span><br/>
                        <span style="color:#B9D4B2;font-size:12.5px;letter-spacing:0.1px;">Monitoramento urbano via Meta Ray-Ban</span>
                      </td>
                    </tr></table>
                  </td>
                </tr>

                <tr>
                  <td style="padding:28px 32px 8px 32px;">
                    <span style="display:inline-block;background:{GREEN_SOFT_BG};color:{GREEN_ACTION};font-size:11px;font-weight:600;letter-spacing:0.4px;padding:5px 11px;border-radius:6px;text-transform:uppercase;">
                      {_escape(badge_label)}
                    </span>
                    <h1 style="margin:16px 0 6px 0;font-size:20px;font-weight:600;letter-spacing:-0.3px;color:{TEXT_DARK};">Nova ocorrência registrada por um cidadão</h1>
                    <p style="margin:0;font-size:14px;color:{TEXT_MUTED};line-height:1.6;">
                      Um usuário do aplicativo UrbanSense AI flagrou e enviou o registro abaixo à
                      <b style="color:{TEXT_DARK};">{_escape(data.city_hall_name)}</b> para providências.
                    </p>
                  </td>
                </tr>

                <tr>
                  <td style="padding:16px 32px;">
                    <img src="cid:{REPORT_PHOTO_CID}" alt="Foto da ocorrência"
                         width="496" style="width:100%;max-width:496px;border-radius:10px;border:1px solid #E5EAE3;display:block;" />
                  </td>
                </tr>

                <tr>
                  <td style="padding:8px 32px 28px 32px;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
                      {detection_row}
                      {_metadata_row("Data e hora", when_text)}
                      {_metadata_row("Coordenadas GPS", gps)}
                      {_metadata_row("Precisão do sinal", accuracy_text)}
                      {_metadata_row("Tipo de captura", data.trigger_label)}
                      {_metadata_row("Dispositivo", data.device_id or "—")}
                      {_metadata_row("ID do registro", data.report_id)}
                    </table>
                    <a href="{maps_url}" style="display:inline-block;margin-top:20px;background:{GREEN_ACTION};color:#FFFFFF;text-decoration:none;font-size:14px;font-weight:600;padding:12px 22px;border-radius:8px;letter-spacing:0.1px;">
                      Ver localização no mapa →
                    </a>
                  </td>
                </tr>

                <tr>
                  <td style="background:#FAFBF9;padding:18px 32px;border-top:1px solid #EEF2ED;">
                    <p style="margin:0;font-size:12px;color:{TEXT_MUTED};line-height:1.6;">
                      E-mail gerado automaticamente pelo <b style="color:{GREEN_ACTION};">UrbanSense AI</b> a partir de uma
                      ocorrência capturada em campo. Não é necessário responder a esta mensagem.
                    </p>
                  </td>
                </tr>

              </table>
            </td></tr>
          </table>
        </body>
        </html>
    """


def send_report_email(
    data: ReportEmailData,
    to_email: str,
    image_bytes: bytes,
    image_filename: str = "ocorrencia.jpg",
) -> EmailResult:
    if not config.MAILTRAP_API_TOKEN or not to_email:
        return EmailResult(
            success=False,
            status_code=-1,
            message="Token do Mailtrap ou e-mail de destino não configurado no servidor",
        )

    payload = {
        "from": {"email": config.MAILTRAP_SENDER_EMAIL, "name": config.MAILTRAP_SENDER_NAME},
        "to": [{"email": to_email}],
        "subject": build_subject(data),
        "html": build_html(data),
        "category": "UrbanSense - Ocorrência",
        "attachments": [
            {
                "content": base64.b64encode(image_bytes).decode("ascii"),
                "filename": image_filename,
                "type": "image/jpeg",
                "disposition": "inline",
                "content_id": REPORT_PHOTO_CID,
            },
            {
                "content": _logo_base64(),
                "filename": "urbansense-logo.png",
                "type": "image/png",
                "disposition": "inline",
                "content_id": LOGO_CID,
            },
        ],
    }

    try:
        response = requests.post(
            config.MAILTRAP_API_URL,
            json=payload,
            headers={"Api-Token": config.MAILTRAP_API_TOKEN, "Content-Type": "application/json"},
            timeout=20,
        )
        return EmailResult(
            success=response.ok,
            status_code=response.status_code,
            message=None if response.ok else response.text[:500],
        )
    except requests.RequestException as exc:
        return EmailResult(success=False, status_code=-1, message=str(exc))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
