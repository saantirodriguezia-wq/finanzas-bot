import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_sheets_service():
    private_key = os.environ.get("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n")
    creds_dict = {
        "type": "service_account",
        "project_id": os.environ.get("GOOGLE_PROJECT_ID"),
        "private_key_id": os.environ.get("GOOGLE_PRIVATE_KEY_ID"),
        "private_key": private_key,
        "client_email": os.environ.get("GOOGLE_CLIENT_EMAIL"),
        "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/finanzas-bot%40finanzas-bot-495615.iam.gserviceaccount.com",
        "universe_domain": "googleapis.com"
    }
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)

def escribir_en_sheet(sheet_id, movimientos, mes):
    service = get_sheets_service()
    sheet = service.spreadsheets()
    hoja_nombre = f"📅 {mes}"
    for mov in movimientos:
        tipo = mov.get("tipo", "gasto")
        categoria = mov.get("categoria", "Otros")
        fecha = mov.get("fecha", "")
        concepto = mov.get("concepto", "")
        importe = float(mov.get("importe", 0))
        declarado = mov.get("declarado", "no")
        if tipo == "ingreso":
            result = sheet.values().get(spreadsheetId=sheet_id, range=f"'{hoja_nombre}'!A6:A30").execute()
            fila_libre = min(6 + len(result.get("values", [])), 30)
            tipo_declarado = "Declarado" if declarado == "si" else "No declarado"
            adelanto = importe if categoria == "Learning Heroes" else 0
            sheet.values().update(
                spreadsheetId=sheet_id,
                range=f"'{hoja_nombre}'!A{fila_libre}:G{fila_libre}",
                valueInputOption="USER_ENTERED",
                body={"values": [[fecha, concepto, tipo_declarado, importe, adelanto, "", categoria]]}
            ).execute()
        else:
            result = sheet.values().get(spreadsheetId=sheet_id, range=f"'{hoja_nombre}'!A44:A68").execute()
            fila_libre = min(44 + len(result.get("values", [])), 68)
            deducible = "S" if declarado == "si" else "N"
            sheet.values().update(
                spreadsheetId=sheet_id,
                range=f"'{hoja_nombre}'!A{fila_libre}:F{fila_libre}",
                valueInputOption="USER_ENTERED",
                body={"values": [[fecha, concepto, categoria, importe, deducible, ""]]}
            ).execute()
    return True
