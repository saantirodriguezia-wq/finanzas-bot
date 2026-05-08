import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_sheets_service():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS", "")
    creds_json = creds_json.strip()
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS está vacío")
    try:
        creds_dict = json.loads(creds_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Error parseando JSON: {e} | Primeros 100 chars: {creds_json[:100]}")
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=SCOPES
    )
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
            rango_busqueda = f"'{hoja_nombre}'!A6:A30"
            result = sheet.values().get(
                spreadsheetId=sheet_id,
                range=rango_busqueda
            ).execute()
            valores = result.get("values", [])
            fila_libre = 6 + len(valores)
            if fila_libre > 30:
                fila_libre = 30
            tipo_declarado = "Declarado" if declarado == "si" else "No declarado"
            adelanto = importe if categoria == "Learning Heroes" else 0
            rango = f"'{hoja_nombre}'!A{fila_libre}:G{fila_libre}"
            valores_escribir = [[fecha, concepto, tipo_declarado, importe, adelanto, "", categoria]]
        else:
            rango_busqueda = f"'{hoja_nombre}'!A44:A68"
            result = sheet.values().get(
                spreadsheetId=sheet_id,
                range=rango_busqueda
            ).execute()
            valores = result.get("values", [])
            fila_libre = 44 + len(valores)
            if fila_libre > 68:
                fila_libre = 68
            deducible = "S" if declarado == "si" else "N"
            rango = f"'{hoja_nombre}'!A{fila_libre}:F{fila_libre}"
            valores_escribir = [[fecha, concepto, categoria, importe, deducible, ""]]
        sheet.values().update(
            spreadsheetId=sheet_id,
            range=rango,
            valueInputOption="USER_ENTERED",
            body={"values": valores_escribir}
        ).execute()
    return True
