import os
import json
import base64
import httpx
from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import anthropic
from sheets import escribir_en_sheet
from datetime import datetime

app = Flask(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
SHEET_ID = os.environ.get("SHEET_ID")

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

SYSTEM_PROMPT = """Eres un asistente de finanzas personales para un autónomo en España.

Tu tarea es analizar mensajes o imágenes de extractos bancarios y extraer movimientos financieros.

REGLAS:
1. Si recibes una imagen de extracto bancario, extrae TODOS los movimientos que veas.
2. Si recibes texto describiendo un gasto o ingreso, extráelo.
3. Siempre responde en JSON con este formato exacto:

{
  "movimientos": [
    {
      "fecha": "DD/MM/YYYY",
      "concepto": "descripción del movimiento",
      "tipo": "gasto" o "ingreso",
      "importe": número positivo,
      "categoria": "una de: Vivienda / Alimentación / Transporte / Ocio/restauración / Suscripciones/software / Gastos profesionales / Préstamo / Otros / Learning Heroes / Management DJ / Alquiler temporal",
      "declarado": "si" o "no"
    }
  ],
  "resumen": "texto breve confirmando lo que encontraste"
}

CATEGORIZACIÓN:
- Nómina o comisión de Learning Heroes → categoria: Learning Heroes, declarado: si
- Management de DJs → categoria: Management DJ, declarado: no
- Alquiler de pisos → categoria: Alquiler temporal, declarado: no
- Supermercado, restaurante → categoria: Alimentación o Ocio/restauración
- Cuota autónomo, gestor → categoria: Gastos profesionales
- Pago de préstamo → categoria: Préstamo

Si la fecha no se ve claramente, usa la fecha de hoy.
Responde SOLO con el JSON, sin texto adicional."""


def enviar_whatsapp(destinatario, mensaje):
    twilio_client.messages.create(
        body=mensaje,
        from_=TWILIO_WHATSAPP_NUMBER,
        to=destinatario
    )


def procesar_imagen(media_url):
    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    response = httpx.get(media_url, auth=auth)
    image_data = base64.standard_b64encode(response.content).decode("utf-8")
    content_type = response.headers.get("content-type", "image/jpeg")
    return image_data, content_type


def analizar_con_claude(texto=None, imagen_data=None, imagen_tipo=None):
    if imagen_data:
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": imagen_tipo,
                    "data": imagen_data,
                },
            },
            {
                "type": "text",
                "text": "Analiza este extracto bancario y extrae todos los movimientos en formato JSON."
            }
        ]
    else:
        content = texto

    message = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}]
    )
    return message.content[0].text


@app.route("/webhook", methods=["POST"])
def webhook():
    remitente = request.form.get("From")
    texto = request.form.get("Body", "").strip()
    num_media = int(request.form.get("NumMedia", 0))

    try:
        if num_media > 0:
            media_url = request.form.get("MediaUrl0")
            media_type = request.form.get("MediaContentType0", "image/jpeg")
            enviar_whatsapp(remitente, "📸 Imagen recibida, analizando el extracto... un momento.")
            image_data, image_type = procesar_imagen(media_url)
            respuesta_json = analizar_con_claude(imagen_data=image_data, imagen_tipo=image_type)
        elif texto:
            respuesta_json = analizar_con_claude(texto=texto)
        else:
            enviar_whatsapp(remitente, "Mandame una foto de tu extracto o describí un movimiento. Ej: 'Gasté 45€ en supermercado hoy'")
            return "", 200

        datos = json.loads(respuesta_json)
        movimientos = datos.get("movimientos", [])
        resumen = datos.get("resumen", "")

        if not movimientos:
            enviar_whatsapp(remitente, "No encontré movimientos claros. Intentá con otra imagen o texto.")
            return "", 200

        meses = {
            "January": "Enero", "February": "Febrero", "March": "Marzo",
            "April": "Abril", "May": "Mayo", "June": "Junio",
            "July": "Julio", "August": "Agosto", "September": "Septiembre",
            "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
        }
        mes_actual = datetime.now().strftime("%B")
        mes_es = meses.get(mes_actual, mes_actual)

        escribir_en_sheet(SHEET_ID, movimientos, mes_es)

        msg = f"✅ *{resumen}*\n\n"
        msg += f"📋 Registré {len(movimientos)} movimiento(s) en *{mes_es}*:\n\n"
        for m in movimientos:
            emoji = "💸" if m["tipo"] == "gasto" else "💰"
            msg += f"{emoji} {m['concepto']}: *{m['importe']}€*\n"
            msg += f"   📁 {m['categoria']}\n"
        msg += f"\n📊 Revisá tu Google Sheet para ver el detalle."

        enviar_whatsapp(remitente, msg)

    except Exception as e:
        print(f"Error: {e}")
        enviar_whatsapp(remitente, "Error inesperado. Intentá de nuevo.")

    return "", 200


@app.route("/", methods=["GET"])
def health():
    return "Bot de finanzas funcionando ✅", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
