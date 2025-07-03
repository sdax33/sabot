import requests
import pandas as pd
import os
from ta.momentum import StochasticOscillator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
import datetime

# 🔐 المفاتيح من المتغيرات البيئية في Railway
TWELVE_API_KEY = os.getenv("TD_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # مثلاً: https://your-app.up.railway.app

# 🟡 جلب بيانات الذهب من Twelve Data
def fetch_gold_data():
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=1day&outputsize=500&apikey={TWELVE_API_KEY}"
    res = requests.get(url).json()

    if "values" not in res:
        print("📛 Twelve Data API response:", res)
        return None

    df = pd.DataFrame(res["values"])
    df = df.rename(columns={
        "datetime": "date",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
    })
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)
    df = df.sort_values("date").reset_index(drop=True)
    return df

# باقي الدوال (detect_fvg, detect_order_block, detect_smc_ict, analyze_trend_stochastic, time_analysis, full_market_analysis)
# ... انسخها كما هي من كودك الأصلي بدون تغيير ...

# 🚀 Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("اسكالب ⚡", callback_data="scalp"),
        InlineKeyboardButton("سوينغ 🐢", callback_data="swing")
    ]]
    await update.message.reply_text("ابدأ تحليلك مع بوت S A (gold mafia)", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    df = fetch_gold_data()
    if df is None:
        await query.edit_message_text("❌ فشل في جلب بيانات الذهب.")
        return

    mode = query.data

    if mode == "scalp":
        df = df.tail(7)
        analysis = full_market_analysis(df)
        analysis = "📍 وضع: اسكالب ⚡\n\n" + analysis

    elif mode == "swing":
        df = df.tail(60)
        analysis = full_market_analysis(df)
        analysis = "📍 وضع: سوينغ 🐢\n\n" + analysis

    await query.edit_message_text(analysis)

def main():
    port = int(os.getenv("PORT", 8000))

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_mode))

    # تفعيل webhook مع رابطك في Railway أو غيره
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        webhook_url=WEBHOOK_URL,
        webhook_path="/",  # أو path خاص لو حابب
    )

if __name__ == "__main__":
    main()
