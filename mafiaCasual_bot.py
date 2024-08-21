from itertools import filterfalse

import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import threading
import random

bot = telebot.TeleBot("7444461797:AAHP48qoahuBElUVZGTE8dQXJ4ia-X0hAEQ")

game_state = {
    "players": {},
    "roles": ["Mafia", "Doctor", "Sheriff", "Peaceful Person"],
    "registration_active": True
}

def handle_register(call):
    user_id = call.from_user.id
    if user_id not in game_state["players"]:
        game_state["players"][user_id] = {
            "name": call.from_user.first_name,
            "role": None
        }
        bot.answer_callback_query(call.id, 'You have registered for the game')

@bot.message_handler(commands=['start_game'])
def start_game(message):
    markup = InlineKeyboardMarkup()
    button = InlineKeyboardButton("Join", callback_data="registered")
    markup.add(button)

    bot.send_message(message.chat.id, "Click the button to join the game!", reply_markup=markup)
    threading.Timer(30.0, end_registration, [message.chat.id]).start()


@bot.callback_query_handler(func=lambda call: call.data == "registered" and game_state["registration_active"])
def register_player(call):
    handle_register(call)


def end_registration(chat_id):
    game_state["registration_active"] = False

    player_ids = list(game_state["players"].keys())
    random.shuffle(player_ids)
    random.shuffle(game_state["roles"])

    for i, player_id in enumerate(player_ids):
        role = game_state["roles"][i % len(game_state["roles"])]
        game_state["players"][player_id]["role"] = role

        bot.send_message(player_id, f"Your role is: {role}")

    bot.send_message(chat_id, "Registration is complete! Roles have been assigned!")




bot.polling()