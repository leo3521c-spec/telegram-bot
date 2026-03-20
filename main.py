from telegram import Update, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime, timedelta
import os

# ---------------- CONFIG ----------------
TOKEN = os.environ.get("TOKEN")  # Replit Secret

# ---------------- KEYBOARD ----------------
keyboard = [
    ["Start Work", "Off Work"],
    ["Smoke", "Toilet", "Eat"],
    ["Back to Seat"]
]
markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ---------------- DATA STORAGE ----------------
user_data = {}

# ---------------- HELPERS ----------------
def format_duration(td: timedelta):
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def time_str(dt: datetime):
    return dt.strftime("%I:%M:%S %p")

def ordinal(n):
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    else:
        return f"{n}{['th','st','nd','rd','th','th','th','th','th','th'][n%10]}"

# ---------------- COMMANDS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    if user not in user_data:
        user_data[user] = {"Start Work": [], "Smoke": [], "Toilet": [], "Eat": [], "Back to Seat": [], "Off Work": None, "Away": None}
    msg = "✅ <b>Welcome!</b> Buttons are ready."
    await update.message.reply_text(msg, reply_markup=markup, parse_mode=ParseMode.HTML)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for user in user_data:
        for key in ["Start Work","Smoke","Toilet","Eat","Back to Seat","Off Work","Away"]:
            if key in ["Off Work","Away"]:
                user_data[user][key] = None
            else:
                user_data[user][key] = []
    await update.message.reply_text("🔄 <b>Manual Reset Done</b>. All user data cleared.")

# ---------------- BUTTON HANDLER ----------------
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    action = update.message.text
    now = datetime.now()

    if user not in user_data:
        user_data[user] = {"Start Work": [], "Smoke": [], "Toilet": [], "Eat": [], "Back to Seat": [], "Off Work": None, "Away": None}
    u = user_data[user]

    # ---------- VALIDATION FOR ACTIVE BREAK ----------
    active_break = u["Away"]
    if action in ["Smoke","Toilet","Eat"]:
        if not u["Start Work"]:
            await update.message.reply_text("⚠️ <b>Work Not Started</b>\nClick Start Work first.", parse_mode=ParseMode.HTML)
            return
        if active_break:
            await update.message.reply_text(
                f"⚠️ <b>Break Already Active</b>\nYou are currently on {active_break['action']} break.\n"
                "Please click on Back to Seat before starting a new activity.",
                parse_mode=ParseMode.HTML
            )
            return

    # ---------- BACK TO SEAT ----------
    if action=="Back to Seat":
        if not active_break:
            await update.message.reply_text(
                "⚠️ <b>No Active Break</b>\nYou are not on a break yet. Click Smoke/Toilet/Eat first.",
                parse_mode=ParseMode.HTML
            )
            return
        away_action = active_break["action"]
        start_time = active_break["time"]
        duration = now - start_time
        u["Back to Seat"].append({"action": away_action, "time": now, "duration": duration})
        u[away_action].append(duration)
        u["Away"] = None
        total_duration = sum(u[away_action], timedelta())
        total_count = len(u[away_action])
        msg = (
            f"🪑 <b>Back to Seat</b> from {away_action}\n"
            f"⌚ Back to seat time: {time_str(now)}\n"
            f"⏱ Total {away_action} time now: {format_duration(duration)}\n"
            f"⏱ Total {away_action} Time today: {format_duration(total_duration)} | Total {away_action}: {total_count}\n\n"
            "⚠️ Please do not click on Off Work if you are still in work."
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    # ---------- START WORK ----------
    if action=="Start Work":
        if u["Start Work"] and not u["Off Work"]:
            await update.message.reply_text(
                "⚠️ <b>You have already started your work today!</b>\n"
                "You did not click on Off Work yet.\n"
                "If you completed your work please click on Off Work.\n"
                "Then click Start Work again for further work.",
                parse_mode=ParseMode.HTML
            )
            return
        u["Start Work"].append(now)
        count = ordinal(len(u["Start Work"]))
        msg = (
            f"🟢 <b>Work Started</b>\n"
            f"⌚ Starting time: {time_str(now)}\n"
            f"📊 Total count: {count}\n"
            "💡 Please do not click on Off Work if you are still doing work."
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    # ---------- OFF WORK ----------
    if action=="Off Work":
        if not u["Start Work"]:
            await update.message.reply_text("⚠️ <b>Work Not Started</b>\nClick Start Work first.", parse_mode=ParseMode.HTML)
            return
        u["Off Work"] = now
        summary=""
        total_working = timedelta()
        total_away_time = timedelta()
        for act in ["Smoke","Toilet","Eat"]:
            count = len(u[act])
            duration = sum(u[act], timedelta())
            total_away_time += duration
            summary+=f"- {act} count: {count}, total duration: {format_duration(duration)}\n"
        start_times = ', '.join([time_str(t) for t in u["Start Work"]])
        summary=f"- Start Work times: {start_times}\n"+summary
        total_working = (now - u["Start Work"][0]) - total_away_time
        msg = (
            "📊 <b>Off Work summary</b>\n\n"
            "You have completed your work today\n\n"
            f"{summary}"
            f"Total Working Hours (excluding Smoke/Toilet/Eat): {format_duration(total_working)}\n\n"
            "💡 When you will start work again please click on Start Work."
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    # ---------- BREAKS ----------
    if action=="Eat":
        u["Away"] = {"action": action, "time": now}
        today_count = len(u[action])
        start_work_time = time_str(u["Start Work"][0])
        msg = (
            f"🍽 <b>Eat Started</b>\n"
            f"⌚ Starting Time: {time_str(now)}\n"
            f"📊 Total Eat today: {today_count}\n"
            f"⌛ Start work time: {start_work_time}\n\n"
            "⚠️ Please click on Back to Seat when you get back from Eat. Failure to click on time will impose $50 fine."
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    if action=="Toilet":
        u["Away"] = {"action": action, "time": now}
        today_count = len(u[action])
        msg = (
            f"🚻 <b>Toilet Started</b>\n"
            f"⌚ Starting time: {time_str(now)}\n"
            f"📊 Total Toilet count today: {today_count}\n"
            f"⏱ Total toilet time use today: \n\n"
            "⚠️ Please click on Back to Seat when you are back from Toilet to avoid $50 fine. Thank you."
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    if action=="Smoke":
        u["Away"] = {"action": action, "time": now}
        today_count = len(u[action])
        msg = (
            f"🚬 <b>Smoke Started</b>\n"
            f"⌚ Starting time: {time_str(now)}\n"
            f"📊 Total Smoke count today: {today_count}\n"
            f"⏱ Total smoke time use today: \n\n"
            "⚠️ Please click on Back to Seat when you are back from Smoke to avoid $50 fine. Thank you."
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

# ---------------- REPORT ----------------
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report_text="📊 <b>Attendance Report</b>\n"
    for user,u in user_data.items():
        report_text+=f"\n👤 <b>{user}</b>\n"
        if u["Start Work"]:
            report_text+=f"- Start Work times: {', '.join([time_str(t) for t in u['Start Work']])}\n"
        for act in ["Smoke","Toilet","Eat"]:
            if u[act]:
                total_duration=sum(u[act], timedelta())
                report_text+=f"- {act} count: {len(u[act])}, total duration: {format_duration(total_duration)}\n"
        if u["Off Work"]:
            report_text+=f"- Off Work: {time_str(u['Off Work'])}\n"
    await update.message.reply_text(report_text, parse_mode=ParseMode.HTML)

# ---------------- BOT RUN ----------------
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("report", report))
app.add_handler(CommandHandler("reset", reset))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button))

print("Bot is running... ✅")
app.run_polling()
