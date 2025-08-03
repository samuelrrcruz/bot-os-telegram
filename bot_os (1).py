
import os
import uuid
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)

# Etapas
NUM_OS, ENDERECO, TECNICO, NAO_CONFORMIDADES, EVIDENCIAS = range(5)

# Criar pasta para fotos
os.makedirs("evidencias", exist_ok=True)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credenciais.json", scope)
client = gspread.authorize(creds)
# Use o link completo da planilha abaixo:
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1SVtg2Vca2gI1Asj2rNhfviW4DmwbK1UGi56YlWE4zw4/edit?gid=0#gid=0")
worksheet = sheet.sheet1

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
    context.user_data['fotos'] = []
    await update.message.reply_text("Envie as evidências (fotos). Quando terminar, digite /fim")
    return EVIDENCIAS

async def get_evidencias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_id = str(uuid.uuid4())
    file_path = f"evidencias/{file_id}.jpg"
    await file.download_to_drive(file_path)
    context.user_data['fotos'].append(file_path)
    await update.message.reply_text("Foto recebida. Envie mais ou digite /fim.")
    return EVIDENCIAS

async def fim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    row = [
        context.user_data['num_os'],
        context.user_data['endereco'],
        context.user_data['tecnico'],
        context.user_data['nao_conformidades'],
        ", ".join(context.user_data['fotos'])
    ]
    worksheet.append_row(row)
    await update.message.reply_text("Dados salvos com sucesso na planilha online!")
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
