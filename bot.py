import os
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")  # Pega o token do ambiente
DATA_PATH = "Power Bi.xlsx"
df = pd.read_excel(DATA_PATH, sheet_name="Planilha1")

for col in ["PLACA", "IDTEL", "FUNCIONÁRIO", "SUPERVISOR", "COORDENADOR",
            "CORPORATIVO FUNCIONÁRIO", "GERENTE", "SITUAÇÃO"]:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip().str.upper()

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip().upper()

    # IDTEL
    if texto in df["IDTEL"].values:
        row = df.loc[df["IDTEL"] == texto].iloc[0]
        await update.message.reply_text(
            f"🔑 IDTEL: {row['IDTEL']}\n"
            f"👤 Funcionário: {row['FUNCIONÁRIO']}\n"
            f"🏢 Corporativo: {row['CORPORATIVO FUNCIONÁRIO']}\n"
            f"🚗 Placa: {row['PLACA']}\n"
            f"👨‍💼 Supervisor: {row['SUPERVISOR']}\n"
            f"👔 Coordenador: {row['COORDENADOR']}\n"
            f"👨‍⚖️ Gerente: {row['GERENTE']}\n"
            f"📌 Situação: {row['SITUAÇÃO']}"
        )
        return

    # PLACA
    if texto in df["PLACA"].values:
        row = df.loc[df["PLACA"] == texto].iloc[0]
        await update.message.reply_text(
            f"🚗 Placa: {row['PLACA']}\n"
            f"👤 Funcionário: {row['FUNCIONÁRIO']}\n"
            f"🏢 Corporativo: {row['CORPORATIVO FUNCIONÁRIO']}\n"
            f"🔑 IDTEL: {row['IDTEL']}\n"
            f"👨‍💼 Supervisor: {row['SUPERVISOR']}\n"
            f"👔 Coordenador: {row['COORDENADOR']}\n"
            f"👨‍⚖️ Gerente: {row['GERENTE']}\n"
            f"📌 Situação: {row['SITUAÇÃO']}"
        )
        return

    # NOME (pode repetir)
    encontrados = df.loc[df["FUNCIONÁRIO"] == texto]
    if not encontrados.empty:
        for _, row in encontrados.iterrows():
            await update.message.reply_text(
                f"👤 Funcionário: {row['FUNCIONÁRIO']}\n"
                f"🏢 Corporativo: {row['CORPORATIVO FUNCIONÁRIO']}\n"
                f"🔑 IDTEL: {row['IDTEL']}\n"
                f"🚗 Placa: {row['PLACA']}\n"
                f"👨‍💼 Supervisor: {row['SUPERVISOR']}\n"
                f"👔 Coordenador: {row['COORDENADOR']}\n"
                f"👨‍⚖️ Gerente: {row['GERENTE']}\n"
                f"📌 Situação: {row['SITUAÇÃO']}"
            )
        return

    await update.message.reply_text("❌ Não encontrei esse IDTEL, NOME ou PLACA.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))
    print("🤖 Bot rodando no Render...")
    app.run_polling()

if __name__ == "__main__":
    main()

