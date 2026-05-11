import os
import base64
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_sheets_service():
    creds_b64 = os.environ.get("GOOGLE_CREDENTIALS_B64", "")
    creds_json = base64.b64decode(creds_b64).decode("utf-8")
    creds_dict = json.loads(creds_json)
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
