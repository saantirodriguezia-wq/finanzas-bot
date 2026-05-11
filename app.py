import os
import json
import base64
import httpx
from flask import Flask, request
import anthropic
from twilio.rest import Client
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
Analiza mensajes o imágenes de extractos bancarios y extrae movimientos financieros.
Responde SOLO con JSON válido, sin texto adicional, sin markdown, sin backticks.
Formato exacto:
{"movimientos":[{"fecha":"DD/MM/YYYY","concepto":"descripcion","tipo":"gasto o ingreso","importe":numero,"categoria":"Vivienda o Alimentacion o Transporte o Ocio/restauracion o Suscripciones/software o Gastos profesionales o Prestamo o Otros o Learning Heroes o Management DJ o Alquiler temporal","declarado":"si o no"}],"resumen":"texto breve"}
Reglas de categorización:
- Learning Heroes o comision o nomina → categoria Learning Heroes, declarado si
- Management DJ → categoria Management DJ, declarado no  
- Alquiler piso → categoria Alquiler temporal, declarado no
- Supermercado, comida → Alimentacion
- Cuota autonomo, gestor → Gastos profesionales
- Pago prestamo → Prestamo
Si no hay fecha clara usa hoy. Responde SOLO el JSON."""

MESES = {
    "January":"Enero","February":"Febrero","March":"Marzo","April":"Abril",
    "May":"Mayo","June":"Junio","July":"Julio","August":"Agosto",
    "September":"Septiembre","October":"Octubre","November":"Noviembre","December":"Diciembre"
}

def enviar_whatsapp(destinatario, mensaje):
    twilio_client.messages.create(
        body=mensaje, from_=TWILIO_WHATSAPP_NUMBER, to=destinatario
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
            {"type":"image","source":{"type":"base64","media_type":imagen_tipo,"data":imagen_data}},
            {"type":"text","text":"Analiza este extracto bancario y devuelve el JSON con los movimientos."}
        ]
    else:
        content = texto
    message = anthropic_client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role":"user","content":content}]
    )
    return message.content[0].text.strip()

@app.route("/webhook", methods=["POST"])
def webhook():
    remitente = request.form.get("From")
    texto = request.form.get("Body", "").strip()
    num_media = int(request.form.get("NumMedia", 0))
    try:
        if num_media > 0:
            media_url = request.form.get("MediaUrl0")
            media_type = request.form.get("MediaContentType0", "image/jpeg")
            enviar_whatsapp(remitente, "📸 Analizando el extracto... un momento.")
            image_data, image_type = procesar_imagen(media_url)
            respuesta_raw = analizar_con_claude(imagen_data=image_data, imagen_tipo=image_type)
        elif texto:
            respuesta_raw = analizar_con_claude(texto=texto)
        else:
            enviar_whatsapp(remitente, "Mandame una foto de tu extracto o describí un movimiento. Ej: 'Gasté 45€ en supermercado hoy'")
            return "", 200

        respuesta_raw = respuesta_raw.strip()
        if respuesta_raw.startswith("```"):
            respuesta_raw = respuesta_raw.split("```")[1]
            if respuesta_raw.startswith("json"):
                respuesta_raw = respuesta_raw[4:]
        respuesta_raw = respuesta_raw.strip()

        datos = json.loads(respuesta_raw)
        movimientos = datos.get("movimientos", [])
        resumen = datos.get("resumen", "")

        if not movimientos:
            enviar_whatsapp(remitente, "No encontré movimientos. Intentá con otra imagen o describí el movimiento en texto.")
            return "", 200

        mes_actual = datetime.now().strftime("%B")
        mes_es = MESES.get(mes_actual, mes_actual)

        escribir_en_sheet(SHEET_ID, movimientos, mes_es)

        msg = f"✅ {resumen}\n\n"
        msg += f"📋 Registré {len(movimientos)} movimiento(s) en *{mes_es}*:\n\n"
        for m in movimientos:
            emoji = "💸" if m["tipo"] == "gasto" else "💰"
            msg += f"{emoji} {m['concepto']}: *{m['importe']}€*\n"
            msg += f"   📁 {m['categoria']}\n"
        msg += "\n📊 Revisá tu Google Sheet para ver el detalle."

        enviar_whatsapp(remitente, msg)

    except json.JSONDecodeError as e:
        enviar_whatsapp(remitente, f"Error procesando la respuesta. Intentá de nuevo.")
        print(f"JSON Error: {e}")
    except Exception as e:
        enviar_whatsapp(remitente, f"Error inesperado. Intentá de nuevo.")
        print(f"Error: {e}")

    return "", 200

@app.route("/", methods=["GET"])
def health():
    return "Bot de finanzas funcionando ✅", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
