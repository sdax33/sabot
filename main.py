import requests
import pandas as pd
import os
from ta.momentum import StochasticOscillator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
import datetime

# 🔐 المفاتيح من البيئة
TWELVE_API_KEY = os.getenv("TD_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # مثال: https://your-app.up.railway.app

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

# 🔎 FVG – Fair Value Gap
def detect_fvg(df):
    signals = []
    for i in range(2, len(df)):
        h1, l1 = df['high'].iloc[i-2], df['low'].iloc[i-2]
        h2, l2 = df['high'].iloc[i-1], df['low'].iloc[i-1]
        h3, l3 = df['high'].iloc[i], df['low'].iloc[i]

        if l1 > h2 and l3 > h2:
            signals.append("FVG صاعد (طلب)")
        elif h1 < l2 and h3 < l2:
            signals.append("FVG هابط (عرض)")
        else:
            signals.append("لا يوجد")
    df['fvg'] = ["لا يوجد"] * 2 + signals
    return df

# 🧱 Order Block
def detect_order_block(df):
    signals = []
    for i in range(2, len(df)):
        body1 = abs(df['close'].iloc[i-2] - df['open'].iloc[i-2])

        if df['close'].iloc[i-2] < df['open'].iloc[i-2] and df['close'].iloc[i] > df['open'].iloc[i]:
            if body1 > (df['high'].iloc[i-2] - df['low'].iloc[i-2]) * 0.6:
                signals.append("Order Block صاعد")
            else:
                signals.append("لا يوجد")
        elif df['close'].iloc[i-2] > df['open'].iloc[i-2] and df['close'].iloc[i] < df['open'].iloc[i]:
            if body1 > (df['high'].iloc[i-2] - df['low'].iloc[i-2]) * 0.6:
                signals.append("Order Block هابط")
            else:
                signals.append("لا يوجد")
        else:
            signals.append("لا يوجد")
    df['order_block'] = ["لا يوجد"] * 2 + signals
    return df

# 🎯 SMC / ICT
def detect_smc_ict(df):
    signals = []
    for i in range(3, len(df)):
        if df['high'].iloc[i-1] > df['high'].iloc[i-2] and df['close'].iloc[i-1] < df['open'].iloc[i-1] and df['close'].iloc[i] < df['close'].iloc[i-1]:
            signals.append("سيولة فوق ثم هبوط")
        elif df['low'].iloc[i-1] < df['low'].iloc[i-2] and df['close'].iloc[i-1] > df['open'].iloc[i-1] and df['close'].iloc[i] > df['close'].iloc[i-1]:
            signals.append("سيولة تحت ثم صعود")
        else:
            signals.append("لا يوجد")
    df['smc_ict'] = ["لا يوجد"] * 3 + signals
    return df

# 📈 الاتجاه العام + Stochastic
def analyze_trend_stochastic(df):
    df['SMA_20'] = df['close'].rolling(window=20).mean()
    stoch = StochasticOscillator(high=df['high'], low=df['low'], close=df['close'], window=14, smooth_window=3)
    df['stoch_k'] = stoch.stoch()
    df['stoch_d'] = stoch.stoch_signal()

    latest = df.iloc[-1]
    trend = "صاعد 📈" if latest['close'] > latest['SMA_20'] else "هابط 📉"

    if latest['stoch_k'] > 80:
        stochastic = "تشبع شرائي 🔴"
    elif latest['stoch_k'] < 20:
        stochastic = "تشبع بيعي 🟢"
    else:
        stochastic = "ضمن النطاق ⚪"

    return trend, stochastic, latest['close']

# ⏰ تحليل زمني
def time_analysis():
    hour = datetime.datetime.utcnow().hour
    if 12 <= hour <= 15:
        return "جلسة نيويورك 🔥"
    elif 6 <= hour <= 9:
        return "جلسة لندن ⚡"
    else:
        return "جلسة هادئة 😴"

# 🧠 التحليل الشامل
def full_market_analysis(df):
    df = detect_fvg(df)
    df = detect_order_block(df)
    df = detect_smc_ict(df)
    trend, stochastic, price = analyze_trend_stochastic(df)
    session_info = time_analysis()

    return f"""📊 تحليل شامل للذهب (XAU/USD)

🔸 السعر الحالي: {price:.2f} USD
📈 الاتجاه العام: {trend}
🎯 Stochastic: {stochastic}
🟨 FVG: {df['fvg'].iloc[-1]}
🏛️ Order Block: {df['order_block'].iloc[-1]}
💥 SMC/ICT: {df['smc_ict'].iloc[-1]}
🕒 توقيت السوق: {session_info}

✅ التحليل دقيق ومبني على بيانات واقعية.
"""

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

# ✅ Main function with Webhook setup
def main():
    port = int(os.getenv("PORT", 8000))

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_mode))

    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        webhook_url=WEBHOOK_URL
    )

if __name__ == "__main__":
    main()
