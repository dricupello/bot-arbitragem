import asyncio
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import datetime

TELEGRAM_TOKEN = "8094480450:AAE5LPJNHJUPLdXbIqwnvps2HLN-tox4xvc"
TELEGRAM_USER_ID = 65399567

# ========== Funções de Preço ==========
async def get_price_binance():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return float(data["price"])

async def get_price_bybit():
    url = "https://api.bybit.com/v5/market/tickers?category=inverse"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            for ticker in data["result"]["list"]:
                if ticker["symbol"] == "BTCUSD":
                    return float(ticker["lastPrice"])
    raise ValueError("BTCUSD not found in Bybit data")

async def get_price_coinex():
    url = "https://api.coinex.com/perpetual/v1/market/ticker?market=BTCUSD"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return float(data["data"]["ticker"]["last"])

# ========== Comandos ==========
async def preco(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price_binance = await get_price_binance()
        price_bybit = await get_price_bybit()
        price_coinex = await get_price_coinex()
        mensagem = (
            f"💰 *Preços Atuais:*\n\n"
            f"🔸 Binance: ${price_binance:,.2f}\n"
            f"🔹 Bybit:   ${price_bybit:,.2f}\n"
            f"🔸 CoinEx:  ${price_coinex:,.2f}"
        )
        await context.bot.send_message(chat_id=update.effective_chat.id, text=mensagem, parse_mode="Markdown")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Erro ao obter preços: {e}")

async def gap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        b = await get_price_binance()
        y = await get_price_bybit()
        c = await get_price_coinex()

        g1 = calcular_diferenca(b, y)
        g2 = calcular_diferenca(b, c)
        g3 = calcular_diferenca(y, c)

        mensagem = (
            f"📊 *Diferença de Preço (%):*\n\n"
            f"🔸 Binance vs Bybit: {g1:.2f}%\n"
            f"🔸 Binance vs CoinEx: {g2:.2f}%\n"
            f"🔸 Bybit vs CoinEx: {g3:.2f}%"
        )
        await context.bot.send_message(chat_id=update.effective_chat.id, text=mensagem, parse_mode="Markdown")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Erro ao calcular gaps: {e}")

# ========== Monitoramento ==========
def calcular_diferenca(p1, p2):
    return abs(p1 - p2) / ((p1 + p2) / 2) * 100

async def enviar_alerta(bot, mensagem):
    try:
        await bot.send_message(chat_id=TELEGRAM_USER_ID, text=mensagem)
    except Exception as e:
        print("Erro ao enviar alerta:", e)

async def monitorar(bot):
    while True:
        try:
            b = await get_price_binance()
            y = await get_price_bybit()
            c = await get_price_coinex()

            diff_bin_y = calcular_diferenca(b, y)
            diff_bin_c = calcular_diferenca(b, c)
            diff_y_c = calcular_diferenca(y, c)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{timestamp} | Binance: {b} | Bybit: {y} | CoinEx: {c}")

            async def checar(diff, nome1, nome2):
                if diff >= 4:
                    await enviar_alerta(bot, f"🚨 Diferença > 4% entre {nome1} e {nome2}!")
                elif diff >= 2:
                    await enviar_alerta(bot, f"⚠️ Diferença > 2% entre {nome1} e {nome2}.")
                elif diff >= 1:
                    await enviar_alerta(bot, f"📊 Diferença > 1% entre {nome1} e {nome2}.")
                elif diff >= 0.5:
                    await enviar_alerta(bot, f"🔍 Diferença > 0.5% entre {nome1} e {nome2}.")

            await checar(diff_bin_y, "Binance", "Bybit")
            await checar(diff_bin_c, "Binance", "CoinEx")
            await checar(diff_y_c, "Bybit", "CoinEx")

            # Sinais inteligentes
            if b > c and calcular_diferenca(b, c) >= 0.5:
                pct = calcular_diferenca(b, c)
                await enviar_alerta(bot, f"💡 *Oportunidade detectada!*\nCoinEx está {pct:.2f}% abaixo da Binance.\nPossível entrada antecipada.")

            if y > c and calcular_diferenca(y, c) >= 0.5:
                pct = calcular_diferenca(y, c)
                await enviar_alerta(bot, f"💡 *Oportunidade detectada!*\nCoinEx está {pct:.2f}% abaixo da Bybit.\nPossível entrada antecipada.")

        except Exception as e:
            print("Erro no monitoramento:", e)

        await asyncio.sleep(5)

# ========== Inicialização ==========
async def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("preco", preco))
    application.add_handler(CommandHandler("gap", gap))

    await application.initialize()
    await application.start()
    print("✅ Bot iniciado com sucesso!")

    asyncio.create_task(monitorar(application.bot))
    await application.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
