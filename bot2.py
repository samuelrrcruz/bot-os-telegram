import os
import uuid
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)

# Etapas
NUM_OS, ENDERECO, TECNICO, NAO_CONFORMIDADES, EVIDENCIAS = range(5)

# Criar pasta temporária para fotos
os.makedirs("evidencias", exist_ok=True)

# Google Sheets e Drive setup
SCOPES = ["https://www.googleapis.com/auth/drive", "https://spreadsheets.google.com/feeds"]
SERVICE_ACCOUNT_FILE = "credenciais.json"

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

# Google Sheets
client = gspread.authorize(creds)
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1SVtg2Vca2gI1Asj2rNhfviW4DmwbK1UGi56YlWE4zw4/edit?gid=0#gid=0")
worksheet = sheet.sheet1

# Google Drive
drive_service = build("drive", "v3", credentials=creds)

# Upload para o Google Drive e retornar link
def upload_to_drive(file_path):
    file_metadata = {
        "name": os.path.basename(file_path),
        "parents": ["1-eJ2nxYXk8cZEY4dVlAhrD5DZ2BTwlFh"]  # opcional: envie para pasta específica
    }
    media = MediaFileUpload(file_path, mimetype="image/jpeg")
    file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()

    # Torna o arquivo público
    drive_service.permissions().create(
        fileId=file.get("id"),
        body={"type": "anyone", "role": "reader"},
    ).execute()

    file_id = file.get("id")
    return f"https://drive.google.com/uc?id={file_id}"

# Início
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Digite o Número da OS:")
    return NUM_OS

async def get_num_os(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['num_os'] = update.message.text
    await update.message.reply_text("Digite o Endereço:")
    return ENDERECO

async def get_endereco(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['endereco'] = update.message.text
    await update.message.reply_text("Digite o Nome do Técnico:")
    return TECNICO

async def get_tecnico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['tecnico'] = update.message.text
    await update.message.reply_text("Descreva as Não Conformidades:")
    return NAO_CONFORMIDADES

async def get_nao_conformidades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['nao_conformidades'] = update.message.text
    context.user_data['fotos_links'] = []
    await update.message.reply_text("Envie as evidências (fotos). Quando terminar, digite /fim")
    return EVIDENCIAS

async def get_evidencias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_id = str(uuid.uuid4())
    file_path = f"evidencias/{file_id}.jpg"
    await file.download_to_drive(file_path)

    # Envia para o Google Drive e obtém o link
    link = upload_to_drive(file_path)
    context.user_data['fotos_links'].append(link)

    await update.message.reply_text("Foto recebida. Envie mais ou digite /fim.")
    return EVIDENCIAS

async def fim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    row = [
        context.user_data['num_os'],
        context.user_data['endereco'],
        context.user_data['tecnico'],
        context.user_data['nao_conformidades'],
        "\n".join(context.user_data['fotos_links'])
    ]
    worksheet.append_row(row)
    await update.message.reply_text("Dados e fotos salvos com sucesso na planilha e no Google Drive!")
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelado.")
    return ConversationHandler.END

def main():
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    app = ApplicationBuilder().token("8495988623:AAFFViwueVrUCuwFFAS6U0qbXUuU4u96yP0").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NUM_OS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_num_os)],
            ENDERECO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_endereco)],
            TECNICO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tecnico)],
            NAO_CONFORMIDADES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nao_conformidades)],
            EVIDENCIAS: [
                MessageHandler(filters.PHOTO, get_evidencias),
                CommandHandler("fim", fim),
            ],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == '__main__':
    main()
