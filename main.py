import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()

bot_token = os.getenv("Telegram_Bot_Token")
secret_token = os.getenv("Telegram_Secret_Token")
DATABASE_URL = os.getenv("DATABASE_URL")

if not bot_token:
    raise ValueError("Telegram_Bot_Token belum diatur di file .env!")

print(f"Bot Token berhasil dimuat: {bot_token[:10]}...")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)

#connect to database
def get_latest_telemetry():
    #data cadangan (fallback)
    default_data = {
        "panel": {"voltage": 0.0, "current": 0.0, "power": 0.0},
        "beban": {"voltage": 0.0, "current": 0.0, "power": 0.0},
        "baterai": {"voltage": 0.0, "current": 0.0, "power": 0.0}
    }
    
    if not DATABASE_URL:
        print("Warning: DATABASE_URL belum diatur di file .env")
        return default_data

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT * FROM telemetry ORDER BY id DESC LIMIT 1;"
        cursor.execute(query)
        row = cursor.fetchone()
        
        cursor.close()
        conn.close()

        if row:
            return {
                "panel": {
                    "voltage": float(row.get("load_voltage_panel") or 0.0),
                    "current": float(row.get("current_panel") or 0.0),
                    "power": float(row.get("power_panel") or 0.0)
                },
                "beban": {
                    "voltage": float(row.get("load_voltage_beban") or 0.0),
                    "current": float(row.get("current_beban") or 0.0),
                    "power": float(row.get("power_beban") or 0.0)
                },
                "baterai": {
                    "voltage": float(row.get("load_voltage_baterai") or 0.0),
                    "current": float(row.get("current_baterai") or 0.0),
                    "power": float(row.get("power_baterai") or 0.0)
                }
            }
        return default_data

    except Exception as e:
        print(f"Error Database: {e}")
        return default_data

#button
def get_status_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("☀️ Solar Panel", callback_data="status_panel"),
            InlineKeyboardButton("💡 Load (Beban)", callback_data="status_load"),
        ],
        [
            InlineKeyboardButton("🔋 Battery", callback_data="status_battery"),
            InlineKeyboardButton("📊 All Metrics", callback_data="status_all"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# /start (Welcome Message)
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_text = (
        f"Hello, {user_name}! 👋\n\n"
        f"Welcome to PLTS PMLD Monitoring Bot ☀️⚡\n"
        f"This bot provides real-time telemetry monitoring for solar panel, load, and battery performance.\n\n"
        f"📌 Available Commands:\n"
        f"• /status - Check real-time metrics (Panel, Load, Battery)\n"
        f"• /help - Usage guide & system documentation\n\n"
        f"Use the menu button [/] next to the chat box for quick access."
    )
    await update.message.reply_text(welcome_text)

# /help (User Guide & Documentation)
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "ℹ️ PLTS Monitoring System Guide\n\n"
        "1. /status\n"
        "Displays real-time electrical telemetry parameters:\n"
        "• Solar Panel: Voltage, Input Current, Generated Power.\n"
        "• Load: Output Voltage, Current Consumption, Power Draw.\n"
        "• Battery: Voltage, Charge/Discharge Current, Battery Power.\n\n"
        "2. Automated Alerts\n"
        "The system automatically issues warning notifications during critical events.\n\n"
        "📞 For technical support, contact the system administrator."
    )
    await update.message.reply_text(help_text)

# /status (display button)
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "PLTS PMLD Telemetry Menu\nSelect the parameter category you want to check:"
    await update.message.reply_text(text, reply_markup=get_status_keyboard())

#callback
async def button_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  
    
    data = get_latest_telemetry()
    choice = query.data

    #formatting variabel:
    p_v = data["panel"]["voltage"]
    p_i = data["panel"]["current"] / 1000.0
    p_w = data["panel"]["power"]
    
    l_v = data["beban"]["voltage"]
    l_i = data["beban"]["current"] / 1000.0
    l_w = data["beban"]["power"]
    
    b_v = data["baterai"]["voltage"]
    b_i = data["baterai"]["current"] / 1000.0
    b_w = data["baterai"]["power"]
    
    b_status = "Discharging 🔋" if b_i < 0 else "Charging ⚡"

    if choice == "status_panel":
        response_text = (
            "SOLAR PANEL METRICS\n"
            f"• Voltage : {p_v:.2f} V\n"
            f"• Current : {p_i:.2f} A ({data['panel']['current']:.1f} mA)\n"
            f"• Power   : {p_w:.2f} W\n"
            "Status: Active"
        )
    elif choice == "status_load":
        response_text = (
            "LOAD (BEBAN) METRICS\n"
            f"• Voltage : {l_v:.2f} V\n"
            f"• Current : {l_i:.2f} A ({data['beban']['current']:.1f} mA)\n"
            f"• Power   : {l_w:.2f} W\n"
            "Status: Active"
        )
    elif choice == "status_battery":
        response_text = (
            "BATTERY METRICS\n"
            f"• Voltage : {b_v:.2f} V\n"
            f"• Current : {b_i:.2f} A ({data['baterai']['current']:.1f} mA)\n"
            f"• Power   : {b_w:.2f} W\n"
            f"• Status  : {b_status}\n"
            "Status: Normal"
        )
    elif choice == "status_all":
        response_text = (
            "ALL REAL-TIME METRICS\n\n"
            "SOLAR PANEL\n"
            f"• Voltage : {p_v:.2f} V\n"
            f"• Current : {p_i:.2f} A ({data['panel']['current']:.1f} mA)\n"
            f"• Power   : {p_w:.2f} W\n\n"
            "LOAD\n"
            f"• Voltage : {l_v:.2f} V\n"
            f"• Current : {l_i:.2f} A ({data['beban']['current']:.1f} mA)\n"
            f"• Power   : {l_w:.2f} W\n\n"
            "BATTERY\n"
            f"• Voltage : {b_v:.2f} V\n"
            f"• Current : {b_i:.2f} A ({data['baterai']['current']:.1f} mA)\n"
            f"• Power   : {b_w:.2f} W\n"
            f"• Status  : {b_status}\n\n"
            "System Operating Normally"
        )

    await query.edit_message_text(
        text=response_text, 
        reply_markup=get_status_keyboard()
    )

#main program
if __name__ == "__main__":
    print("Starting PLTS Monitoring Telegram Bot...")
    
    app = ApplicationBuilder().token(bot_token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CallbackQueryHandler(button_click_handler))
    
    app.run_polling()