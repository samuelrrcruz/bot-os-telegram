import telebot
from telebot import types
import gspread
from google.oauth2.service_account import Credentials
import re
import threading
from datetime import datetime, timedelta
import time

# ==========================
# FUNÇÃO PARA ESCAPAR MARKDOWN
# ==========================
def escape_markdown(text, version=2):
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

# ==========================
# CONFIGURAÇÕES
# ==========================
TOKEN = "7615917960:AAEFth7tLq4E6FCcqQVC2BFBRa2J56_feLM"
GOOGLE_SHEET_ID = "1dJa0UTDaFKafcP9l-xZcDFlNm9nsw4n7D0NR45-6a8Q"

bot = telebot.TeleBot(TOKEN)
user_data = {}
foto_timer = {}
cache_aux = {}
cache_area = []

# === Conexão com Google Sheets ===
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
client = gspread.authorize(creds)

sheet_botm = client.open_by_key(GOOGLE_SHEET_ID).worksheet("botm")
sheet_cliente = client.open_by_key(GOOGLE_SHEET_ID).worksheet("Casacliente")

# ==========================
# FUNÇÕES DE ATUALIZAÇÃO
# ==========================
def atualizar_cache():
    """Atualiza os dados da aba Aux e area a cada 10 minutos"""
    global cache_aux, cache_area
    try:
        print("🔄 Atualizando cache do Google Sheets...")
        sheet_aux = client.open_by_key(GOOGLE_SHEET_ID).worksheet("Aux")
        sheet_area = client.open_by_key(GOOGLE_SHEET_ID).worksheet("area")

        dados_aux = sheet_aux.get_all_values()
        dados_area = sheet_area.get_all_values()

        cache_aux = {}
        for idx, letra in enumerate("ABCDEFG", start=1):
            coluna = [linha[idx - 1].strip() for linha in dados_aux if len(linha) >= idx and linha[idx - 1].strip()]
            cache_aux[letra] = sorted(set(coluna))

        cache_area = dados_area

        print("✅ Cache atualizado com sucesso!")
    except Exception as e:
        print(f"⚠️ Erro ao atualizar cache: {e}")

    # Atualiza novamente em 10 minutos
    threading.Timer(600, atualizar_cache).start()

# Inicia a primeira atualização
atualizar_cache()

# === Funções auxiliares ===
def carregar_opcoes(coluna):
    """Carrega opções da coluna da aba Aux a partir do cache."""
    return cache_aux.get(coluna, [])

def carregar_armarios_por_area(area):
    """Retorna os armários correspondentes a uma área, com base no cache da aba area."""
    try:
        armarios = [linha[1].strip() for linha in cache_area if len(linha) >= 2 and linha[0].strip().upper() == area.strip().upper()]
        return armarios
    except Exception as e:
        print(f"Erro ao carregar armarios: {e}")
        return []

def gerar_datas():
    hoje = datetime.now()
    datas = []
    for i in range(7, -1, -1):
        dia = hoje - timedelta(days=i)
        datas.append(dia.strftime("%d/%m/%Y"))
    return datas

# === Estrutura de perguntas ===
questions_manutencao = [
    ("ocorrencia", "Ocorrência?"),
    ("fiscal", "Fiscal:"),
    ("endereco", "Endereço:"),
    ("area", "Área:"),
    ("armario", "Armário:"),
    ("splitter", "Splitter:"),
    ("contagem", "Contagem:"),
    ("data", "Data da execução:"),
    ("status", "Status da fiscalização:"),
    ("naoconf", "Não conformidades:"),
    ("relato", "Relato da fiscalização:"),
    ("evidencias", "Envie as evidências (fotos):")
]

questions_cliente = [
    ("os", "Ordem de serviço ou PON:"),
    ("fiscal", "Fiscal:"),
    ("atividade", "Tipo de atividade:"),
    ("idtel", "Idtel do técnico:"),
    ("area", "Área:"),
    ("armario", "Armário:"),
    ("data", "Data da execução:"),
    ("status", "Status da fiscalização:"),
    ("naoconf", "Não conformidades:"),
    ("relato", "Relato da fiscalização:"),
    ("evidencias", "Envie as evidências (fotos):")
]

# === Iniciar escolha de segmento ===
def iniciar_fiscalizacao(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🧰 MANUTENÇÃO VIVO", callback_data="segmento|manutencao"),
        types.InlineKeyboardButton("🏠 CASA CLIENTE (VIVO)", callback_data="segmento|casacliente")
    )
    bot.send_message(chat_id, "Selecione o segmento da fiscalização:", reply_markup=markup)

def iniciar_segmento(chat_id, segmento):
    user_data[chat_id] = {"index": 0, "fotos": [], "segmento": segmento, "multiselecoes": []}
    send_next_question(chat_id)

# === Comandos básicos ===
@bot.message_handler(commands=['reiniciar'])
def comando_reiniciar(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "🔁 Reiniciando a fiscalização...")
    iniciar_fiscalizacao(chat_id)

@bot.message_handler(commands=['finalizar'])
def comando_finalizar(message):
    chat_id = message.chat.id
    user_data.pop(chat_id, None)
    foto_timer.pop(chat_id, None)
    bot.send_message(chat_id, "❌ Fiscalização cancelada.")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🚀 Iniciar Nova Fiscalização", callback_data="acao|iniciar"))
    bot.send_message(chat_id, "Deseja iniciar novamente?", reply_markup=markup)

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_any_text(message):
    chat_id = message.chat.id
    if message.text.startswith("/"):
        return
    if chat_id in user_data:
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🚀 Iniciar Fiscalização", callback_data="acao|iniciar"))
    bot.send_message(chat_id, "Clique abaixo para iniciar a fiscalização, caso queira reiniciar a fiscalização em qualquer momento, digite: /finalizar", reply_markup=markup)

# === Perguntas ===
def send_next_question(chat_id):
    data = user_data[chat_id]
    segmento = data["segmento"]
    questions = questions_manutencao if segmento == "manutencao" else questions_cliente
    idx = data["index"]
    if idx >= len(questions):
        finalizar_fiscalizacao(chat_id)
        return
    key, question = questions[idx]

    # === Carrega opções do cache ===
    opcoes = []
    if key == "fiscal":
        opcoes = carregar_opcoes("A")
    elif key == "status":
        opcoes = carregar_opcoes("C")
    elif key == "area":
        opcoes = carregar_opcoes("D")
    elif key == "armario":
        area = data.get("area", "")
        opcoes = carregar_armarios_por_area(area)
    elif key == "naoconf":
        opcoes = carregar_opcoes("E" if segmento == "manutencao" else "F")
    elif key == "atividade" and segmento == "casacliente":
        opcoes = carregar_opcoes("G")
    elif key == "data":
        opcoes = gerar_datas()

    # Multi-seleção (Não conformidades)
    if key == "naoconf":
        data["multiselecoes"] = []
        markup = types.InlineKeyboardMarkup()
        for nome in opcoes:
            markup.add(types.InlineKeyboardButton(nome, callback_data=f"multi|{nome}"))
        markup.add(types.InlineKeyboardButton("✅ Finalizar seleção", callback_data="multi_finalizar|ok"))
        bot.send_message(chat_id, question, reply_markup=markup)
        return

    # Perguntas com botões
    if opcoes:
        markup = types.InlineKeyboardMarkup(row_width=2)
        for nome in opcoes:
            markup.add(types.InlineKeyboardButton(nome, callback_data=f"{key}|{nome}"))
        bot.send_message(chat_id, question, reply_markup=markup)
        return

    # Perguntas abertas
    if key == "evidencias":
        bot.send_message(chat_id, question + "\nEnvie as fotos.")
        return

    sent = bot.send_message(chat_id, question)
    bot.register_next_step_handler(sent, handle_text)

def handle_text(message):
    chat_id = message.chat.id
    data = user_data[chat_id]
    segmento = data["segmento"]
    questions = questions_manutencao if segmento == "manutencao" else questions_cliente
    idx = data["index"]
    key, _ = questions[idx]
    data[key] = message.text.strip()
    data["index"] += 1
    send_next_question(chat_id)

# === Fotos ===
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    if chat_id not in user_data: return
    fid = message.photo[-1].file_id
    user_data[chat_id]["fotos"].append(fid)
    bot.send_message(chat_id, "📸 Foto recebida, aguarde 5 segundos para finalizar a fiscalização!")
    if chat_id in foto_timer:
        foto_timer[chat_id].cancel()
    t = threading.Timer(5, lambda: mostrar_botoes_fotos(chat_id))
    foto_timer[chat_id] = t
    t.start()

def mostrar_botoes_fotos(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Finalizar Fiscalização", callback_data="acao|finalizar"),
        types.InlineKeyboardButton("🔁 Reiniciar", callback_data="acao|reiniciar")
    )
    bot.send_message(chat_id, "📷 Todas as fotos recebidas. Escolha:", reply_markup=markup)

# === Finalizar ===
def finalizar_fiscalizacao(chat_id):
    data = user_data[chat_id]
    seg = data["segmento"]
    fotos = data.get("fotos", [])
    conformidades = data.get("naoconf", "")
    lista_conf = conformidades.split("; ") if conformidades else [""]
    carimbo = datetime.now().strftime("%d/%m/%Y %H:%M")

    planilha = sheet_botm if seg == "manutencao" else sheet_cliente

    texto_final = f"📋 *Fiscalização - {seg.upper()}*\n\n"
    for k, v in data.items():
        if k not in ["segmento", "fotos", "index", "multiselecoes", "naoconf", "fiscal"]:
            texto_final += f"{k.capitalize()}: {v}\n"
    texto_final += "\n🔎 *Não conformidades:*\n" + "\n".join([f"- {c}" for c in lista_conf if c])

    bot.send_message(chat_id, escape_markdown(texto_final, 2), parse_mode="MarkdownV2")
    for f in fotos:
        bot.send_photo(chat_id, f)

    try:
        for conf in lista_conf:
            linha = [v for k, v in data.items() if k not in ["segmento", "fotos", "index", "multiselecoes", "naoconf"]]
            linha.append(conf)
            linha.append(carimbo)
            planilha.append_row(linha)
        bot.send_message(chat_id, "✅ Dados enviados ao Google Sheets.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Erro Sheets: {e}")

    user_data.pop(chat_id, None)
    foto_timer.pop(chat_id, None)

# === CALLBACK ===
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    chat_id = call.message.chat.id
    k, v = call.data.split("|", 1)

    if k == "acao":
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
        if v == "iniciar":
            bot.send_message(chat_id, "🚀 Iniciando fiscalização...")
            iniciar_fiscalizacao(chat_id)
        elif v == "finalizar":
            finalizar_fiscalizacao(chat_id)
        elif v == "reiniciar":
            bot.send_message(chat_id, "🔁 Reiniciando formulário...")
            iniciar_fiscalizacao(chat_id)
        return

    if k == "segmento":
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
        if v == "manutencao":
            bot.send_message(chat_id, "🧰 Segmento selecionado: MANUTENÇÃO VIVO")
        elif v == "casacliente":
            bot.send_message(chat_id, "🏠 Segmento selecionado: CASA CLIENTE (VIVO)")
        iniciar_segmento(chat_id, v)
        return

    if k == "multi":
        data = user_data.get(chat_id)
        if not data:
            bot.answer_callback_query(call.id, "Erro interno. Reinicie com /reiniciar.")
            return
        if v in data["multiselecoes"]:
            data["multiselecoes"].remove(v)
            bot.answer_callback_query(call.id, f"❌ Removido: {v}")
        else:
            data["multiselecoes"].append(v)
            bot.answer_callback_query(call.id, f"✅ Selecionado: {v}")
        return

    if k == "multi_finalizar":
        data = user_data.get(chat_id)
        if not data:
            bot.answer_callback_query(call.id, "Erro interno. Reinicie com /reiniciar.")
            return
        selecionados = data["multiselecoes"]
        data["naoconf"] = "; ".join(selecionados)
        bot.send_message(chat_id, f"✅ Seleções finalizadas: {', '.join(selecionados)}")
        data["index"] += 1
        send_next_question(chat_id)
        return

    data = user_data.get(chat_id)
    if not data:
        return
    user_data[chat_id][k] = v
    bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
    bot.send_message(chat_id, f"✅ {k.capitalize()}: {v}")
    user_data[chat_id]["index"] += 1
    send_next_question(chat_id)

print("🤖 Bot ativo — lendo dados da planilha e atualizando automaticamente a cada 10 minutos...")
bot.infinity_polling()
