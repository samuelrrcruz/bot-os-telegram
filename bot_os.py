import os
import uuid
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)
from fpdf import FPDF
from PIL import Image

# Etapas
NUM_OS, ENDERECO, TECNICO, NAO_CONFORMIDADES, EVIDENCIAS = range(5)

# Criar pastas para salvar arquivos
os.makedirs("evidencias", exist_ok=True)
os.makedirs("pdfs", exist_ok=True)

# Google Sheets setup
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SERVICE_ACCOUNT_FILE = "credenciais.json"
creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)
client = gspread.authorize(creds)
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1SVtg2Vca2gI1Asj2rNhfviW4DmwbK1UGi56YlWE4zw4/edit?gid=0#gid=0")
worksheet = sheet.sheet1

def gerar_pdf(dados, imagens):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(10, 40, 90)  # azul escuro
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, f"OS: {dados['Número da OS']} - Endereço: {dados['Endereço']}", ln=True, fill=True)
    pdf.cell(0, 10, f"Executor: {dados['Técnico']}", ln=True, fill=True)
    pdf.multi_cell(0, 10, f"Não conformidades: {dados['Não Conformidades']}", fill=True)

    # Imagens lado a lado
    pdf.ln(5)
    pdf.set_text_color(0, 0, 0)

    width_total = 270
    margin = 10
    image_width = (width_total - 2 * margin) / 3 - 5
    image_height = 70

    y_start = pdf.get_y()
    x_positions = [margin + i * (image_width + 5) for i in range(3)]

    for i, imagem in enumerate(imagens):
        if i % 3 == 0:
            pdf.set_y(y_start + (i // 3) * (image_height + 10))
        x = x_positions[i % 3]
        pdf.image(imagem, x=x, y=pdf.get_y(), w=image_width, h=image_height)

    pdf_path = f"pdfs/relatorio_{uuid.uuid4()}.pdf"
    pdf.output(pdf_path)
    return pdf_path

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
    context.user_data['fotos_paths'] = []
    await update.message.reply_text("Envie as evidências (fotos). Quando terminar, digite /fim")
    return EVIDENCIAS

async def get_evidencias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_id = str(uuid.uuid4())
    file_path = f"evidencias/{file_id}.jpg"
    await file.download_to_drive(file_path)
    context.user_data['fotos_links'].append(file_path)
    context.user_data['fotos_paths'].append(file_path)
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

    dados_para_pdf = {
        "Número da OS": context.user_data['num_os'],
        "Endereço": context.user_data['endereco'],
        "Técnico": context.user_data['tecnico'],
        "Não Conformidades": context.user_data['nao_conformidades']
    }

    pdf_path = gerar_pdf(dados_para_pdf, context.user_data['fotos_paths'])
    with open(pdf_path, 'rb') as pdf_file:
        await update.message.reply_document(document=InputFile(pdf_file), filename=os.path.basename(pdf_path))

    await update.message.reply_text("Dados e fotos salvos com sucesso na planilha e no PDF!")
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
