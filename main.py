from telegram import Update, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime, timedelta
import os
from zoneinfo import ZoneInfo

BANGLADESH_TZ = ZoneInfo('Asia/Dhaka')

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
    return dt.astimezone(BANGLADESH_TZ).strftime('%I:%M:%S %p')

def ordinal(n):
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    else:
        return f"{n}{['th','st','nd','rd','th','th','th','th','th','th'][n%10]}"

# ---------------- REAL-TIME LIMIT CHECK ----------------
async def check_active_breaks(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(BANGLADESH_TZ)

    for user, u in user_data.items():
        active = u.get("Away")
        if not active:
            continue

        action = active["action"]
        start_time = active["time"]
        elapsed_minutes = (now - start_time).total_seconds() / 60

        if action == "Smoke" and elapsed_minutes >= 5 and not u.get("warning_sent", False):
            await context.bot.send_message(
                chat_id=u["chat_id"],
                text=(
                    f"🚨 @{user}\n\n"
                    f"🚬 <b>Smoke Time Limit Exceeded</b>\n\n"
                    "⚠️ You have exceeded your smoke time limit.\n\n"
                    "👉 Please back to seat immediately or you will get <b>10$ fine</b>."
                ),
                parse_mode=ParseMode.HTML
            )
            u["warning_sent"] = True

        elif action == "Toilet" and elapsed_minutes >= 14 and not u.get("warning_sent", False):
            await context.bot.send_message(
                chat_id=u["chat_id"],
                text=(
                    f"🚨 @{user}\n\n"
                    f"🚻 <b>Toilet Time Limit Exceeded</b>\n\n"
                    "⚠️ You have exceeded your toilet time limit.\n\n"
                    "👉 Please back to seat immediately or you will get <b>10$ fine</b>."
                ),
                parse_mode=ParseMode.HTML
            )
            u["warning_sent"] = True

# ---------------- COMMANDS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.username or update.effective_user.first_name
    if user not in user_data:
        user_data[user] = {"Start Work": [], "Smoke": [], "Toilet": [], "Eat": [], "Back to Seat": [], "Off Work": None, "Away": None, "warning_sent": False, "chat_id": None}

    msg = (
        "✨ <b>Welcome to Work Tracker Bot</b>\n\n"
        "📌 <b>Status:</b> Ready to track your activity\n"
        "📱 Use the buttons below to control your workflow\n\n"
        "🚀 <b>Let’s get productive!</b>"
    )
    await update.message.reply_text(msg, reply_markup=markup, parse_mode=ParseMode.HTML)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for user in user_data:
        for key in ["Start Work","Smoke","Toilet","Eat","Back to Seat","Off Work","Away"]:
            if key in ["Off Work","Away"]:
                user_data[user][key] = None
            else:
                user_data[user][key] = []

    await update.message.reply_text(
        "🔄 <b>System Reset Successful</b>\n\n"
        "🗑 All user activity data has been cleared\n"
        "⚙️ Fresh tracking session is ready",
        parse_mode=ParseMode.HTML
    )

# ---------------- BUTTON HANDLER ----------------
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.username or update.effective_user.first_name
    action = update.message.text
    now = datetime.now(BANGLADESH_TZ)
        
    if user not in user_data:
        user_data[user] = {"Start Work": [], "Smoke": [], "Toilet": [], "Eat": [], "Back to Seat": [], "Off Work": None, "Away": None, "warning_sent": False, "chat_id": None}
    u = user_data[user]
    u["chat_id"] = update.effective_chat.id

    active_break = u["Away"]

    # ---------- PREVENT ACTION BEFORE START WORK ----------
    if action in ["Smoke","Toilet","Eat","Off Work"] and not u["Start Work"]:
        await update.message.reply_text(
            "⚠️ <b>Action Not Allowed!</b>\n"
            "🚫 You cannot click <b>Smoke, Toilet, Eat</b> or <b>Off Work</b> before starting your work.\n"
            "🟢 Please click <b>Start Work</b> to officially begin your workday and enable other buttons.\n"
            "📝 Follow the workflow: Start Work → Breaks → Back to Seat → Off Work.\n"
            "💡 <b>অবশ্যই প্রথমে Start Work ক্লিক করুন। অন্য বাটনগুলো সক্রিয় হবে তার পরেই।</b>\n"
            "📌 প্রফেশনাল নির্দেশনা অনুযায়ী কার্যক্রম অনুসরণ করুন।",
            parse_mode=ParseMode.HTML
        )
        return
    # ---------- DAILY LIMIT CHECK ----------
    if action == "Smoke" and len(u["Smoke"]) >= 5:
        await update.message.reply_text(
            "🚫 <b>Daily Smoke Limit Exceeded</b>\n"
            "💰 You cannot take more than 5 Smoke breaks per day\n"
            "<b>Violation may result in $100 fine</b>",
            parse_mode=ParseMode.HTML
        )
        return

    if action == "Toilet" and len(u["Toilet"]) >= 5:
        await update.message.reply_text(
            "🚫 <b>Daily Toilet Limit Exceeded</b>\n"
            "💰 You cannot take more than 5 Toilet breaks per day\n"
            "<b>Violation may result in $100 fine</b>",
            parse_mode=ParseMode.HTML
        )
        return

    if action == "Eat" and len(u["Eat"]) >= 1:
        await update.message.reply_text(
            "🚫 <b>Daily Eat Limit Exceeded</b>\n"
            "💰 You cannot take more than 1 Eat break per day\n"
            "<b>Violation may result in $100 fine</b>",
            parse_mode=ParseMode.HTML
        )
        return
        
    # ---------- VALIDATION ----------
    if action in ["Smoke","Toilet","Eat"]:
        if not u["Start Work"]:
            await update.message.reply_text(
                "⚠️ <b>Work Not Started</b>\n"
                "👉 Please click <b>Start Work</b> before taking a break",
                parse_mode=ParseMode.HTML)
            return

        if active_break:
            await update.message.reply_text(
                f"🚫 <b>BREAK ALREADY ACTIVE</b>\n\n"
                f"🕒 You are currently on <b>{active_break['action']}</b> break\n\n"
                "⚠️ <b>Action Required:</b>\n"
                "👉 You must click <b>Back to Seat</b> before starting any new activity\n\n"
                "💰 <b>Warning:</b> If you delay returning and do not click Back to Seat on time,\n"
                "a <b>$50 fine</b> may be applied\n\n"
                "🚨 <i>Please follow the process strictly to avoid penalties</i>",
                parse_mode=ParseMode.HTML
            )
            return

    # ---------- BACK TO SEAT ----------
    if action=="Back to Seat":
        if not active_break:
            await update.message.reply_text(
                "⚠️ <b>NO ACTIVE BREAK DETECTED</b>\n\n"
                "🚫 You are not currently on any break\n\n"
                "👉 Please start a valid activity first:\n"
                "<b>Smoke / Eat / Toilet</b>\n\n"
                "💡 After completing your break, always click <b>Back to Seat</b>\n"
                "💰 Late response may result in a <b>$50 fine</b>",
                parse_mode=ParseMode.HTML)
            return

        away_action = active_break["action"]
        start_time = active_break["time"]
        duration = now - start_time

        u["Back to Seat"].append({"action": away_action, "time": now, "duration": duration})
        u[away_action].append(duration)
        u["Away"] = None
        u["warning_sent"] = False

        total_duration = sum(u[away_action], timedelta())
        total_count = len(u[away_action])

        msg = (
            "🪑 <b>Back to Seat Recorded</b>\n\n"
            f"📌 <b>Break Type:</b> {away_action}\n"
            f"⌚ <b>Return Time:</b> {time_str(now)}\n\n"
            f"⏱ <b>Session Duration:</b> {format_duration(duration)}\n"
            f"📊 <b>Total Today:</b> {format_duration(total_duration)}\n"
            f"🔢 <b>Total Count:</b> {total_count}\n\n"
            "⚠️ <i>Do not click Off Work if you are still working</i>"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    # ---------- START WORK ----------
    if action=="Start Work":
        if u["Start Work"] and not u["Off Work"]:
            await update.message.reply_text(
                "⚠️ <b>Work Already Started</b>\n\n"
                "📌 You haven't ended your previous session\n"
                "👉 Click <b>Off Work</b> before starting again",
                parse_mode=ParseMode.HTML
            )
            return

        u["Start Work"].append(now)
        count = ordinal(len(u["Start Work"]))

        msg = (
            "🟢 <b>Work Session Started</b>\n\n"
            f"⌚ <b>Start Time:</b> {time_str(now)}\n"
            f"📊 <b>Session Count:</b> {count}\n\n"
            "💼 Stay focused and productive!"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    # ---------- OFF WORK ----------
    if action=="Off Work":
        if not u["Start Work"]:
            await update.message.reply_text(
                "⚠️ <b>No Active Work Session</b>\n"
                "👉 Click <b>Start Work</b> first",
                parse_mode=ParseMode.HTML)
            return

        u["Off Work"] = now

        summary=""
        total_away_time = timedelta()

        for act in ["Smoke","Toilet","Eat"]:
            count = len(u[act])
            duration = sum(u[act], timedelta())
            total_away_time += duration
            summary+=f"• <b>{act}</b> → Count: {count}, Time: {format_duration(duration)}\n"

        start_times = ', '.join([time_str(t) for t in u["Start Work"]])
        total_working = (now - u["Start Work"][0]) - total_away_time

        msg = (
            "📊 <b>Work Summary Report</b>\n\n"
            "✅ <b>Status:</b> Work Completed\n\n"
            f"🕒 <b>Start Times:</b> {start_times}\n\n"
            f"{summary}\n"
            f"⏱ <b>Net Working Time:</b> {format_duration(total_working)}\n\n"
            "🚀 <i>Click Start Work to begin a new session</i>"
        )

        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    # ---------- BREAKS ----------
    if action=="Eat":
        u["Away"] = {"action": action, "time": now}
        u["warning_sent"] = False
        today_count = len(u[action])
        start_work_time = time_str(u["Start Work"][0])

        msg = (
            "🍽 <b>Break Started: Eat</b>\n\n"
            f"⌚ <b>Start Time:</b> {time_str(now)}\n"
            f"📊 <b>Today's Count:</b> {today_count}\n"
            f"🕒 <b>Work Start:</b> {start_work_time}\n\n"
            "⚠️ <b>Important Notice:</b>\n"
            "👉 You must click <b>Back to Seat</b> immediately after returning\n"
            "⏳ Any delay in response will be strictly monitored\n"
            "💰 <b>Penalty:</b> Late Back to Seat action will result in a <b>$50 fine</b>\n"
            "🚨 <i>Please ensure compliance</i>"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    if action=="Toilet":
        u["Away"] = {"action": action, "time": now}
        u["warning_sent"] = False
        today_count = len(u[action])

        msg = (
            "🚻 <b>Break Started: Toilet</b>\n\n"
            f"⌚ <b>Start Time:</b> {time_str(now)}\n"
            f"📊 <b>Today's Count:</b> {today_count}\n\n"
            "⚠️ <b>Mandatory Action:</b>\n"
            "👉 Click <b>Back to Seat</b> immediately after returning\n"
            "⏳ Delay will be considered a violation\n"
            "💰 <b>$50 fine</b> will be applied for late action\n"
            "🚨 <i>Strict monitoring in place</i>"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    if action=="Smoke":
        u["Away"] = {"action": action, "time": now}
        u["warning_sent"] = False
        today_count = len(u[action])

        msg = (
            "🚬 <b>Break Started: Smoke</b>\n\n"
            f"⌚ <b>Start Time:</b> {time_str(now)}\n"
            f"📊 <b>Today's Count:</b> {today_count}\n\n"
            "⚠️ <b>Important Instruction:</b>\n"
            "👉 You must click <b>Back to Seat</b> as soon as you return\n"
            "⏳ Any delay will be tracked\n"
            "💰 Late update will result in a <b>$50 fine</b>\n"
            "🚨 <i>Avoid penalties by responding on time</i>"
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

app.job_queue.run_repeating(check_active_breaks, interval=30, first=30)

print("Bot is running... ✅")
app.run_polling()
