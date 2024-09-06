from itertools import filterfalse
from trace import Trace

import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import threading
import random

bot = telebot.TeleBot("TOKEN HERE")

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


def get_alive_players_list():
    alive_players = []
    for player_id, player_info in game_state["players"].items():
        if player_info["alive"]:
            alive_players.append(f"{len(alive_players) + 1}. [{player_info['name']}](tg://user?id={player_id})")
    return "\n".join(alive_players)


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
    if len(game_state["players"]) < 4:
        bot.send_message(chat_id, "Not enough players to start the game. You need at least 4 players.")
        return

    game_state["registration_active"] = False

    player_ids = list(game_state["players"].keys())
    player_count = len(player_ids)

    roles = []
    if player_count == 4:
        roles = ["Mafia", "Peaceful Person", "Peaceful Person", "Doctor"]
    elif 4 < player_count <= 7:
        roles = ["Mafia", "Doctor"] + ["Peaceful Person"] * (player_count - 2)
    elif player_count > 7:
        # HERE TWO MAFIA NEEDS TO HANDLE GROUP CHOICE LOGIC
        roles = ["Mafia", "Mafia", "Doctor", "Sheriff"] + ["Peaceful Person"] * (player_count - 4)
    random.shuffle(player_ids)
    random.shuffle(roles)

    for i, player_id in enumerate(player_ids):
        # role = game_state["roles"][i % len(game_state["roles"])]
        # game_state["players"][player_id]["role"] = role
        game_state["players"][player_id]["role"] = roles[i]
        bot.send_message(player_id, f"Your role is: {roles[i]}")

    bot.send_message(chat_id, "Registration is complete! Roles have been assigned!")

    start_night(chat_id)


def start_night(chat_id):
    # bot.send_message(chat_id, open('night.jpg', 'rb'), caption="The night starts!")
    alive_players_list = get_alive_players_list()
    bot.send_message(chat_id, f"The night starts!\n\nAlive players:\n{alive_players_list}", parse_mode="Markdown")

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
        bot.answer_callback_query(call.id, "You have made your choice!")
        bot.send_message(call.message.chat.id, f"Mafia has made their choice!")
    elif role == "Doctor":
        game_state["doctor_choice"] = target_id
        bot.answer_callback_query(call.id, "You have made your choice!")
        bot.send_message(call.message.chat.id, f"Doctor has made their choice!")
    elif role == "Sheriff":
        game_state["sheriff_choice"] = target_id
        bot.answer_callback_query(call.id)

        #add sheriff kill/check action (inlineKeyboardMarkup) +handler if action "Kill" change choosed player "alive": False, if check: send privately to Sheriff in chat is choiced player mafia or not
        #here must be markup
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Kill", callback_data="SheriffAction_Kill"))
        markup.add(InlineKeyboardButton("Check Player", callback_data="SheriffAction_Check"))
        bot.send_message(call.from_user.id, "Do you want to Kill or Check the player?", reply_markup=markup)

    # if all([game_state["mafia_choice"], game_state["doctor_choice"], game_state["sheriff_choice"]]):
    #     process_night_choices(call.message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("SheriffAction_"))
def handle_sheriff_action(call):
    action = call.data.split("_")[1]

    sheriff_target = game_state["sheriff_choice"]
    sheriff_target_info = game_state["players"][sheriff_target]

    if action == "Kill":
        # send directly to group chat
        sheriff_target_info["alive"] = False
        bot.send_message(call.message.chat.id, f"Sheriff has made their choice!")
    elif action == "Check":
        # send privately to Sheriff chat
        is_mafia = sheriff_target_info["role"] == "Mafia"
        bot.send_message(call.from_user.id, f"{sheriff_target_info["name"]} is {"Mafia" if is_mafia else "not Mafia"}!")

    bot.answer_callback_query(call.id, "You has made your choice!")

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

    alive_players = [player for player in game_state["players"].values() if player["alive"]]
    alive_mafia = any(player["role"] == "Mafia" and player["alive"] for player in game_state["players"].values())

    if len(alive_players) == 1 and alive_mafia:
        bot.send_message(chat_id, f"The Mafia wins! Only one player remains!")
        reset_game()
        return

    start_day(chat_id)


def reset_game():
    game_state["players"].clear()
    game_state["mafia_choice"] = None
    game_state["doctor_choice"] = None
    game_state["sheriff_choice"] = None
    game_state["registration_active"] = True


def start_day(chat_id):
    alive_players_list = get_alive_players_list()
    bot.send_message(chat_id, f"The day starts!\n\nAlive players:\n{alive_players_list}", parse_mode="Markdown")

    bot.send_message(chat_id, "Discuss and prepare to vote! You have 45 seconds.")
    threading.Timer(45.0, start_day_vote, [chat_id]).start()


def start_day_vote(chat_id):
    alive_players = [player_info["name"] for player_info in game_state["players"].values() if player_info["alive"]]
    poll_mgs = bot.send_poll(
        chat_id=chat_id,
        question="Who is the Mafia?",
        options=alive_players,
        is_anonymous=True
    )
    bot.register_next_step_handler(poll_mgs, handle_day_vote)


def handle_day_vote(poll):
    winning_option = max(poll.options, key=lambda opt: opt.voter_count).text
    losing_player = None

    for player_id, player_info in game_state["players"].items():
        if player_info["name"] == winning_option:
            losing_player = player_id
            break

    game_state["players"][losing_player]["alive"] = False

    if game_state["players"][losing_player]["role"] == "Mafia":
        bot.send_message(poll.chat.id, f"{winning_option} was a Mafia! Peaceful people win the game!")
    else:
        bot.send_message(poll.chat.id, f"{winning_option} has been voted out but he/she was a {game_state["players"][losing_player]["role"]}!")
        start_night(poll.chat.id)

#booting bot
bot.polling()
