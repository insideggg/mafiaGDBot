from itertools import filterfalse
from trace import Trace

import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import threading
import random

bot = telebot.TeleBot("7444461797:AAHP48qoahuBElUVZGTE8dQXJ4ia-X0hAEQ")

game_state = {
    "players": {},
    "roles": ["Mafia", "Doctor", "Sheriff", "Peaceful Person"],
    "registration_active": True,
    "mafia_choice": None,
    "sheriff_choice": None,
    "doctor_choice": None,
}

def handle_register(call):
    user_id = call.from_user.id
    if user_id not in game_state["players"]:
        game_state["players"][user_id] = {
            "name": call.from_user.first_name,
            "role": None,
            "alive": True
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

    start_night(chat_id)


def start_night(chat_id):
    bot.send_message(chat_id, open('night.jpg', 'rb'), caption="The night starts!")

    for player_id, player_info in game_state["players"].items():
        if player_info["role"] in ["Mafia", "Sheriff", "Doctor"] and player_info["alive"]:
            send_night_choice(player_id, player_info["role"], player_info["name"])


def send_night_choice(player_id, role, name):
    markup = InlineKeyboardMarkup()
    for target_id, target_info in game_state["players"].items():
        if target_id != player_id and target_info["alive"]:
            markup.add(InlineKeyboardButton(target_info["name"], callback_data=f"{role}_{target_id}"))

    bot.send_message(player_id, f"Choose your target, {name}:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def handle_night_choice(call):
    role, target_id = call.data.split("_")
    target_id = int(target_id)

    if role == "Mafia":
        game_state["mafia_choice"] = target_id
        bot.answer_callback_query(call.id, "Mafia has made their choice!")
    elif role == "Doctor":
        game_state["doctor_choice"] = target_id
        bot.answer_callback_query(call.id, "Doctor has made his choice!")
    elif role == "Sheriff":
        game_state["sheriff_choice"] = target_id
        bot.answer_callback_query(call.id, "Sheriff has made his choice!")

        #add sheriff kill/check action +handler

    if all([game_state["mafia_choice"], game_state["doctor_choice"], game_state["sheriff_choice"]]):
        process_night_choices(call.message.chat.id)


def process_night_choices(chat_id):
    mafia_target = game_state["mafia_choice"]
    doctor_target = game_state["doctor_choice"]
    sheriff_target = game_state["sheriff_choice"]

    if mafia_target != doctor_target:
        game_state["players"][mafia_target]["alive"] = False
        bot.send_message(chat_id, f"{game_state["players"][mafia_target]["name"]} was killed by Mafia!")
    if mafia_target == doctor_target:
        bot.send_message(chat_id, f"{game_state["players"][mafia_target]["name"]} was saved by a Doctor!")

    if mafia_target == sheriff_target:
        bot.send_message(chat_id, f"{game_state["players"][mafia_target]["name"]} was saved by a Sheriff while Mafia tried to kill him/her!")

    #end game conditions and bad choices
    if game_state["players"][mafia_target]["roles"] == "Sheriff":
        bot.send_message(chat_id, f"{game_state["players"][mafia_target]["name"]} was killed by Mafia, he/she was a Sheriff!")
        #"alive" param changed in first IF iteration

    if game_state["players"][mafia_target]["roles"] == "Doctor":
        bot.send_message(chat_id, f"{game_state["players"][mafia_target]["name"]} was killed by Mafia, he/she was a Doctor!")
        #"alive" param changed in first IF iteration

    if game_state["players"][sheriff_target]["roles"] == "Mafia" and game_state["players"][sheriff_target]["alive"] == False:
        bot.send_message(chat_id, f"{game_state["players"][sheriff_target]["name"]} was killed by Sheriff, he/she was a Mafia! Peaceful people win in the game!")
        #"alive" param changed in first IF iteration
        reset_game()
        return


def reset_game():
    game_state["players"].clear()
    game_state["mafia_choice"] = None
    game_state["doctor_choice"] = None
    game_state["sheriff_choice"] = None
    game_state["registration_active"] = True


bot.polling()