import logging
import random
import string
from datetime import datetime, time, timedelta, timezone

from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (BaseFilter, CallbackQueryHandler, CommandHandler,
                          Filters, MessageHandler, Updater)

import bridge
import keyboards

# -----DEBUG-----
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
# -----DEBUG-----

updater = Updater(
    token='##TOKEN##',
    use_context=True
)
dispatcher = updater.dispatcher
# TODO: implement timeouts for actions
# job_queue = updater.job_queue

game_data = {}

# No. of players in a bridge game, SET TO 1 FOR DEBUGGING PURPOSES
PLAYERS = 4


class BidFilter(BaseFilter):
    def filter(self, message):
        return (len(message.text) == 3
                and ord(message.text[0]) >= ord("1")
                and ord(message.text[0]) <= ord("7")
                and message.text[1] == " "
                and message.text[2] in bridge.BID_SUITS
                or message.text == "⏭ Pass!"
                or message.text == "▪")


class CardFilter(BaseFilter):
    def filter(self, message):
        arg_list = message.text.split()
        return (message.text == "▪"
                or len(arg_list) == 2
                and (arg_list[0].isdigit()
                     and int(arg_list[0]) >= 2
                     and int(arg_list[0]) <= 10
                     or arg_list[0] in ["A", "K", "Q", "J"])
                and arg_list[1] in bridge.CARD_SUITS)


def random_string(string_length=10):
    return ''.join(random.choice(string.ascii_letters+string.digits) for i in range(string_length))


def stop_game(context):
    if not "game_id" in context.chat_data:
        return

    game_id = context.chat_data["game_id"]

    if game_data[game_id]["mode"] != "lobby":
        for i in range(0, PLAYERS):
            context.bot.edit_message_text(
                chat_id=game_data[game_id]["players_chat_id"][i],
                message_id=game_data[game_id]["hand_message_id"][i],
                parse_mode="markdown",
                text="🃏 Game in _" +
                game_data[game_id]["chat_title"] + "_ has ended! 🃏"
            )

    context.bot.edit_message_text(
        chat_id=game_data[game_id]["chat_id"],
        message_id=game_data[game_id]["initial_message_id"],
        parse_mode="markdown",
        text="Bridge game has ended!\n\n🃏 Use '/start' to start a new game 🃏"
    )

    del game_data[game_id]
    del context.chat_data["game_id"]


def start(update, context):
    # START A GAME (IN A GROUP)
    if (update.effective_chat.type == "group" or update.effective_chat.type == "supergroup"):
        if "game_id" in context.chat_data:
            # TODO: check if the initial game message has been deleted
            #       if so, delete the initial gamedata and reset the game
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                reply_to_message_id=game_data[context.chat_data["game_id"]
                                              ]["initial_message_id"],
                parse_mode="markdown",
                text="❌ A game has already been started!"
            )
            return
        game_id = random_string(string_length=10)
        while game_id in game_data:
            game_id = random_string(string_length=10)

        keyboard = [[InlineKeyboardButton(
            "▶ Join game", url="https://t.me/sg_bridge_bot?start="+game_id)]]

        initial_message = context.bot.send_message(
            chat_id=update.effective_chat.id,
            parse_mode="markdown",
            text=f"♣♦ *Bridge game started* ♥♠\n\n_Waiting for {PLAYERS} players to join..._",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        game_data[game_id] = {
            "initial_message_id": initial_message.message_id,
            "chat_id": update.effective_chat.id,
            "chat_title": update.effective_chat.title,
            "players": [],
            "players_chat_id": [],
            "hand_message_id": [None] * PLAYERS,
            "mode": "lobby",  # or bid, partner, play
            "turn": 0,
            "bidder": -1,
            "bid": -1,
            "hands": bridge.generate_hands(),
            "played_cards": [None] * PLAYERS,
            "sets": [0] * PLAYERS,
            "sets_needed": -1,
            "trump_broken": False,
            "first_player": False,
            "current_suit": None
        }

        context.chat_data["game_id"] = game_id

    # JOIN A GAME
    elif update.effective_chat.type == "private":
        if not context.args or not context.args[0] in game_data:
            keyboard = [[InlineKeyboardButton(
                "👥 Choose a group", url="https://t.me/sg_bridge_bot?startgroup=_")]]

            context.bot.send_message(
                chat_id=update.effective_chat.id,
                parse_mode="markdown",
                text="Add me to a group to start playing! 🃏",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            game_id = context.args[0]

            if update.effective_user in game_data[game_id]["players"]:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    parse_mode="markdown",
                    text="❌ You have already joined the game in _"
                    + game_data[game_id]["chat_title"] + "_!"
                )
                return
            elif len(game_data[game_id]["players"]) == PLAYERS:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    parse_mode="markdown",
                    text="❌ The game in _"
                    + game_data[game_id]["chat_title"] + "_ is already full!"
                )
                return

            game_data[game_id]["players"].append(update.effective_user)
            game_data[game_id]["players_chat_id"].append(
                update.effective_chat.id)

            player_names = []
            for player in game_data[game_id]["players"]:
                player_names.append("🃏 " + player.mention_markdown())
            player_names = '\n'.join(player_names)

            context.bot.send_message(
                chat_id=update.effective_chat.id,
                parse_mode="markdown",
                text="✅ Successfully joined game in _"
                + game_data[game_id]["chat_title"] + "_!"
            )

            if len(game_data[game_id]["players"]) < PLAYERS:
                keyboard = [[InlineKeyboardButton(
                    "▶ Join game", url="https://t.me/sg_bridge_bot?start="+game_id)]]

                context.bot.edit_message_text(
                    chat_id=game_data[game_id]["chat_id"],
                    message_id=game_data[game_id]["initial_message_id"],
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="markdown",
                    text="♣♦ *Bridge game started* ♥♠\n\n*Players*\n"
                    + player_names
                    + "\n\n_Waiting for "
                    + str(PLAYERS - len(game_data[game_id]["players"]))
                    + " more player(s) to join..._"
                )

            else:
                context.bot.edit_message_text(
                    chat_id=game_data[game_id]["chat_id"],
                    message_id=game_data[game_id]["initial_message_id"],
                    parse_mode="markdown",
                    text="♣♦ *Bridge game started* ♥♠\n\n*Players*\n"
                    + player_names
                    + "\n\n✅ Game has begun! Check your PMs to see your cards."
                )

                game_data[game_id]["mode"] = "bid"

                keyboard = keyboards.bid_keyboard()

                for i in range(0, PLAYERS):
                    hand_message = context.bot.send_message(
                        chat_id=game_data[game_id]["players_chat_id"][i],
                        parse_mode="markdown",
                        text="🃏 *Your hand* 🃏\n"
                        + "(for _" +
                        game_data[game_id]["chat_title"] + "_)\n\n"
                        + str(game_data[game_id]["sets"][i])
                        + " set(s) 👑 won\n\n"
                        + bridge.generate_hand_string(game_data[game_id]["hands"][i]))
                    game_data[game_id]["hand_message_id"][i] = hand_message.message_id

                context.bot.send_message(
                    chat_id=game_data[game_id]["chat_id"],
                    parse_mode="markdown",
                    text=game_data[game_id]["players"][0].mention_markdown()
                    + ", start the bid!",
                    reply_markup=ReplyKeyboardMarkup(keyboard, selective=True, one_time_keyboard=True, resize_keyboard=True))


def stop(update, context):
    if (update.effective_chat.type == "group" or update.effective_chat.type == "supergroup") and "game_id" in context.chat_data:
        game_id = context.chat_data["game_id"]
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            parse_mode="markdown",
            text="❌ No game has been started!\n\nUse '/start' to start a new game 🃏"
        )
        return

    # TODO: implement stopping of game

    keyboard = [[InlineKeyboardButton("✅ Stop game", callback_data="stop")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        parse_mode="markdown",
        reply_to_message_id=game_data[game_id]["initial_message_id"],
        text="⚠ Are you sure you want to stop this bridge game?",
        reply_markup=reply_markup)


def inline_button(update, context):
    query = update.callback_query
    if query.data == "stop":
        if not "game_id" in context.chat_data:
            return
        game_id = context.chat_data["game_id"]
        context.bot.send_message(
            chat_id=game_data[game_id]["chat_id"],
            message_id=game_data[game_id]["initial_message_id"],
            parse_mode="markdown",
            text="Bridge game has ended!\n\n🃏 Use '/start' to start a new game 🃏"
        )
        stop_game(context)
        query.edit_message_text(
            text="The game has been stopped successfully ⛔", parse_mode="markdown")

    elif query.data == 'cancel':
        query.edit_message_text(
            text="This game will continue! 🃏", parse_mode="markdown")


def card(update, context):
    if (update.effective_chat.type == "group" or update.effective_chat.type == "supergroup") and "game_id" in context.chat_data:
        game_id = context.chat_data["game_id"]
    else:
        return

    # PARTNER MODE
    if (game_data[game_id]["mode"] == "partner"
            and update.effective_user == game_data[game_id]["players"][game_data[game_id]["turn"]]):

        partner_card = update.message.text.split()

        game_data[game_id]["partner_card"] = update.message.text
        for i in range(0, 4):
            if partner_card[0] in game_data[game_id]["hands"][i][partner_card[1]]:
                game_data[game_id]["partner"] = i
                break

        partner = game_data[game_id]["partner"]
        bidder = game_data[game_id]["bidder"]

        if partner == bidder:
            context.bot.send_message(
                chat_id=game_data[game_id]["players_chat_id"][partner],
                parse_mode="markdown",
                text="💬 Psst... you picked *yourself* as partner 👥 !")
        # This check exists to make sure that the program doesn't crash when im debugging with <4 players
        elif partner < PLAYERS:
            context.bot.send_message(
                chat_id=game_data[game_id]["players_chat_id"][partner],
                parse_mode="markdown",
                text="💬 Psst... you are *" +
                game_data[game_id]["players"][bidder].full_name
                + "'s* partner 👥 !")
        else:
            # Either I'm debugging and the partner picked isn't a actual player (bc i have <4 players)
            # or shit has gone down
            context.bot.send_message(
                chat_id=game_data[game_id]["players_chat_id"][game_data[game_id]["turn"]],
                parse_mode="markdown",
                text="⚠ DEBUG: Actually, the partner you picked isn't playing... ("
                + str(partner) + ")")
            partner = game_data[game_id]["partner"] = bidder

        context.bot.send_message(
            chat_id=game_data[game_id]["chat_id"],
            parse_mode="markdown",
            text=update.effective_user.mention_markdown() + "'s partner 👥 is *" +
            update.message.text + "*",
            reply_markup=ReplyKeyboardRemove())

        game_data[game_id]["mode"] = "play"

        if game_data[game_id]["trump_suit"] == "🚫":
            hand = game_data[game_id]["hands"][game_data[game_id]["bidder"]]
            keyboard = keyboards.hand_keyboard(hand)

            game_data[game_id]["first_player"] = game_data[game_id]["turn"]

            context.bot.send_message(
                chat_id=game_data[game_id]["chat_id"],
                parse_mode="markdown",
                text="Winning bid is *No Trump* 🚫:\nBidder, " +
                update.effective_user.mention_markdown() + ", will start",
                reply_markup=ReplyKeyboardMarkup(keyboard, selective=True, one_time_keyboard=True, resize_keyboard=True))
        else:
            game_data[game_id]["turn"] += 1
            game_data[game_id]["turn"] %= PLAYERS
            game_data[game_id]["first_player"] = game_data[game_id]["turn"]

            hand = game_data[game_id]["hands"][game_data[game_id]["turn"]]
            valid_suits = bridge.get_valid_suits(
                hand, trump_suit=game_data[game_id]["trump_suit"])
            keyboard = keyboards.hand_keyboard(hand, valid_suits)

            context.bot.send_message(
                chat_id=game_data[game_id]["chat_id"],
                parse_mode="markdown",
                text=game_data[game_id]["players"][game_data[game_id]
                                                   ["turn"]].mention_markdown() + " will start",
                reply_markup=ReplyKeyboardMarkup(keyboard, selective=True, one_time_keyboard=True, resize_keyboard=True))

    # PLAYING MODE
    elif (game_data[game_id]["mode"] == "play"
            and update.effective_user == game_data[game_id]["players"][game_data[game_id]["turn"]]):
        turn = game_data[game_id]["turn"]
        first_player = game_data[game_id]["first_player"]
        played_cards = game_data[game_id]["played_cards"]
        # first_card = played_cards[first_player]
        trump_suit = game_data[game_id]["trump_suit"]
        trump_broken = game_data[game_id]["trump_broken"]
        current_suit = game_data[game_id]["current_suit"]

        current_card = update.message.text.split()

        # check if play is valid
        hand = game_data[game_id]["hands"][turn]
        valid_suits = bridge.get_valid_suits(hand,
                                             trump_suit=trump_suit,
                                             current_suit=current_suit,
                                             trump_broken=trump_broken)

        if current_card[0] == '▪':
            keyboard = keyboards.hand_keyboard(hand, valid_suits)

            context.bot.send_message(
                chat_id=game_data[game_id]["chat_id"],
                parse_mode="markdown",
                text="❌ "
                + game_data[game_id]["players"][turn].mention_markdown()
                + ", that was an invalid card... Pick again!",
                reply_markup=ReplyKeyboardMarkup(keyboard, selective=True, one_time_keyboard=True, resize_keyboard=True))
            return

        if not (current_card[1] in valid_suits
                and current_card[0] in game_data[game_id]["hands"][turn][current_card[1]]):
            return

        game_data[game_id]["played_cards"][turn] = update.message.text
        game_data[game_id]["hands"][turn][
            current_card[1]].remove(current_card[0])

        context.bot.edit_message_text(
            chat_id=game_data[game_id]["players_chat_id"][turn],
            message_id=game_data[game_id]["hand_message_id"][turn],
            parse_mode="markdown",
            text="🃏 *Your hand* 🃏\n"
            + "(for _" + game_data[game_id]["chat_title"] + "_)\n\n"
            + str(game_data[game_id]["sets"][turn]) + " set(s) 👑 won\n\n"
            + bridge.generate_hand_string(game_data[game_id]["hands"][turn])
        )

        if first_player == turn:
            game_data[game_id]["current_suit"] = current_suit = current_card[1]

        if current_card[1] == trump_suit:
            game_data[game_id]["trump_broken"] = True
            trump_broken = True

        game_data[game_id]["turn"] += 1
        game_data[game_id]["turn"] %= PLAYERS
        turn = game_data[game_id]["turn"]

        played_cards_string_list = []

        # for i in range(0, PLAYERS):
        #     played_cards_string_list.append("\n")
        #     if i == game_data[game_id]["turn"] and not game_data[game_id]["played_cards"][i]:
        #         played_cards_string_list.append("❇️ ")
        #     else:
        #         played_cards_string_list.append("🃏 ")
        #     played_cards_string_list.append(
        #         game_data[game_id]["players"][i].full_name)
        #     played_cards_string_list.append(
        #         " (" + str(game_data[game_id]["sets"][i]) + " 👑) - ")
        #     if game_data[game_id]["played_cards"][i]:
        #         played_cards_string_list.append(
        #             game_data[game_id]["played_cards"][i])
        #     else:
        #         played_cards_string_list.append("▪")

        for i in range(first_player, first_player+PLAYERS):
            played_cards_string_list.append("\n")
            i %= PLAYERS
            if i == game_data[game_id]["turn"] and not game_data[game_id]["played_cards"][i]:
                played_cards_string_list.append("❇️ ")
            else:
                played_cards_string_list.append("🃏 ")
            played_cards_string_list.append(
                game_data[game_id]["players"][i].full_name)
            played_cards_string_list.append(
                " (" + str(game_data[game_id]["sets"][i]) + " 👑) - ")
            if game_data[game_id]["played_cards"][i]:
                played_cards_string_list.append(
                    game_data[game_id]["played_cards"][i])
            else:
                played_cards_string_list.append("▪")

        played_cards_string = "".join(played_cards_string_list)

        context.bot.send_message(
            chat_id=game_data[game_id]["chat_id"],
            parse_mode="markdown",
            text="🌟 *Bid:* "
            + game_data[game_id]["players"][game_data[game_id]
                                            ["bidder"]].full_name
            + " - " + bridge.get_bid_from_num(game_data[game_id]["bid"])
            + "\n👥 *Partner:* " + game_data[game_id]["partner_card"]
            + "\n" + played_cards_string,
            reply_markup=ReplyKeyboardRemove())

        # All players have played a card, i.e. end of set
        if turn == first_player:
            winner = bridge.compare_cards(
                played_cards, current_suit, trump_suit=trump_suit)
            game_data[game_id]["sets"][winner] += 1

            game_data[game_id]["turn"] = winner
            game_data[game_id]["first_player"] = winner
            game_data[game_id]["current_suit"] = None
            game_data[game_id]["played_cards"] = [None] * PLAYERS

            # TODO: check if winner + partner has enough sets, if so declare a win
            #       also check if two non partners have enough sets

            bidder = game_data[game_id]["bidder"]
            partner = game_data[game_id]["partner"]
            sets = game_data[game_id]["sets"]
            sets_needed = game_data[game_id]["sets_needed"]
            if partner == bidder:
                bidder_sets = sets[bidder]
            else:
                bidder_sets = sets[bidder] + sets[partner]

            if bidder_sets == sets_needed:
                # TODO: clear all the hand messages, send a win message and delete game object
                context.bot.send_message(
                    chat_id=game_data[game_id]["chat_id"],
                    parse_mode="markdown",
                    text=game_data[game_id]["players"][winner].mention_markdown()
                    + ", you have won this set 👑 !\n\n"
                    + "You now have *"
                    + str(game_data[game_id]["sets"][winner])
                    + " set(s)* 👑\n\n")
                if bidder == partner:
                    context.bot.send_message(
                        chat_id=game_data[game_id]["chat_id"],
                        parse_mode="markdown",
                        text="🏅 The bidder, "
                        + game_data[game_id]["players"][bidder].mention_markdown()
                        + ", has won the game alone! 🏅\n\n"
                        + "Use '/start' to start a new game 🃏")
                else:
                    context.bot.send_message(
                        chat_id=game_data[game_id]["chat_id"],
                        parse_mode="markdown",
                        text="🏅 The bidder, "
                        + game_data[game_id]["players"][bidder].mention_markdown()
                        + ", and partner, "
                        + game_data[game_id]["players"][partner].mention_markdown()
                        + ", have won the game! 🏅\n\n"
                        + "Use '/start' to start a new game 🃏")

                stop_game(context)
                return
            elif sum(sets) - bidder_sets == 14 - sets_needed:
                winner_list = []
                for i in range(0, PLAYERS):
                    if i != partner and i != bidder:
                        winner_list.append(
                            game_data[game_id]["players"][i].mention_markdown())

                context.bot.send_message(
                    chat_id=game_data[game_id]["chat_id"],
                    parse_mode="markdown",
                    text=game_data[game_id]["players"][winner].mention_markdown()
                    + ", you have won this set 👑 !\n\n"
                    + "You now have *"
                    + str(game_data[game_id]["sets"][winner])
                    + " set(s)* 👑\n\n")

                if len(winner_list) == 3:
                    winner_string = (winner_list[0] + ", " + winner_list[1]
                                     + " and " + winner_list[2])
                else:
                    winner_string = " and ".join(winner_list)

                context.bot.send_message(
                    chat_id=game_data[game_id]["chat_id"],
                    parse_mode="markdown",
                    text="🏅 "
                    + winner_string
                    + " have won the game! 🏅\n\n"
                    + "Use '/start' to start a new game 🃏")
                stop_game(context)
                return

            winner_hand = game_data[game_id]["hands"][winner]
            valid_suits = bridge.get_valid_suits(
                winner_hand, trump_suit=trump_suit, trump_broken=trump_broken)
            keyboard = keyboards.hand_keyboard(winner_hand, valid_suits)

            context.bot.send_message(
                chat_id=game_data[game_id]["chat_id"],
                parse_mode="markdown",
                text=game_data[game_id]["players"][winner].mention_markdown()
                + ", you have won this set 👑 !\n\n"
                + "You now have *"
                + str(game_data[game_id]["sets"][winner])
                + " set(s)* 👑\n\n"
                + "Pick a card to start the next set!",
                reply_markup=ReplyKeyboardMarkup(keyboard, selective=True, one_time_keyboard=True, resize_keyboard=True))
        else:
            next_hand = game_data[game_id]["hands"][turn]
            valid_suits = bridge.get_valid_suits(
                next_hand, trump_suit=trump_suit, trump_broken=trump_broken, current_suit=current_suit)
            keyboard = keyboards.hand_keyboard(next_hand, valid_suits)

            context.bot.send_message(
                chat_id=game_data[game_id]["chat_id"],
                parse_mode="markdown",
                text=game_data[game_id]["players"][turn].mention_markdown()
                + ", it's your turn ❇️ !",
                reply_markup=ReplyKeyboardMarkup(keyboard, selective=True, one_time_keyboard=True, resize_keyboard=True))


def bid(update, context):
    if (update.effective_chat.type == "group" or update.effective_chat.type == "supergroup") and "game_id" in context.chat_data:
        game_id = context.chat_data["game_id"]
    else:
        return

    # HANDLE OVERLAPS IN BID/CARD FILTERS
    if ((game_data[game_id]["mode"] == "partner"
            or game_data[game_id]["mode"] == "play")
            and CardFilter.filter(None, update.message)):
        card(update, context)

    elif (game_data[game_id]["mode"] == "bid"
            and update.effective_user == game_data[game_id]["players"][game_data[game_id]["turn"]]):
        if update.message.text == "⏭ Pass!":
            context.bot.send_message(
                chat_id=game_data[game_id]["chat_id"],
                parse_mode="markdown",
                text=update.effective_user.mention_markdown() + " *passed* ⏭ this turn",
                reply_markup=ReplyKeyboardRemove())

        elif update.message.text == "▪":
            keyboard = keyboards.bid_keyboard(game_data[game_id]["bid"])
            context.bot.send_message(
                chat_id=game_data[game_id]["chat_id"],
                parse_mode="markdown",
                text=("*Current bid:* "
                      + game_data[game_id]["players"]
                      [game_data[game_id]["bidder"]].full_name
                      + " - "
                      + bridge.get_bid_from_num(game_data[game_id]["bid"])
                      if game_data[game_id]["bidder"] + 1 else "")
                + "\n\n"
                + game_data[game_id]["players"][game_data[game_id]
                                                ["turn"]].mention_markdown()
                + ", it's your turn to bid!",
                reply_markup=ReplyKeyboardMarkup(keyboard, selective=True, one_time_keyboard=True, resize_keyboard=True))
            return

        else:

            bid = update.message.text
            bid_num = bridge.get_num_from_bid(bid)

            if bid_num <= game_data[game_id]["bid"] or bid_num > 34:
                return

            game_data[game_id]["bid"] = bid_num
            game_data[game_id]["trump_suit"] = bid[2]
            game_data[game_id]["sets_needed"] = int(bid[0]) + 6
            game_data[game_id]["bidder"] = game_data[game_id]["turn"]

            context.bot.send_message(
                chat_id=game_data[game_id]["chat_id"],
                parse_mode="markdown",
                text=update.effective_user.mention_markdown() + " bidded *" + bid + "*",
                reply_markup=ReplyKeyboardRemove())

        game_data[game_id]["turn"] += 1
        game_data[game_id]["turn"] %= PLAYERS

        # TODO: handle 4 passes in a row
        # if (game_data[game_id]["bid"] == -1
        #        and game_data[game_id]["bidder"] == -1
        #        and game_data[game_id]["turn"] == 0):
        #     perform wash...
        # -- recommend to refactor card shuffling and issuing (aka wash) into a reusable function --

        if game_data[game_id]["bidder"] == game_data[game_id]["turn"] or game_data[game_id]["bid"] == 34:

            context.bot.send_message(
                chat_id=game_data[game_id]["chat_id"],
                parse_mode="markdown",
                text=game_data[game_id]["players"][game_data[game_id]
                                                   ["bidder"]].mention_markdown()
                + ", you have won the bid 🌟 of *"
                + bridge.get_bid_from_num(game_data[game_id]["bid"]) + "*!\n\n"
                + "You and your partner need a total of *"
                + str(game_data[game_id]["sets_needed"])
                + " sets* 👑 to win",
                reply_markup=ReplyKeyboardRemove())

            game_data[game_id]["mode"] = "partner"
            game_data[game_id]["turn"] = game_data[game_id]["bidder"]

            keyboard = keyboards.partner_keyboard()

            context.bot.send_message(
                chat_id=game_data[game_id]["chat_id"],
                parse_mode="markdown",
                text=game_data[game_id]["players"][game_data[game_id]
                                                   ["bidder"]].mention_markdown()
                + ", choose your partner 👥",
                reply_markup=ReplyKeyboardMarkup(keyboard, selective=True, one_time_keyboard=True, resize_keyboard=True))
        else:
            keyboard = keyboards.bid_keyboard(game_data[game_id]["bid"])

            context.bot.send_message(
                chat_id=game_data[game_id]["chat_id"],
                parse_mode="markdown",
                text=("*Current bid:* "
                      + game_data[game_id]["players"]
                      [game_data[game_id]["bidder"]].full_name
                      + " - "
                      + bridge.get_bid_from_num(game_data[game_id]["bid"])
                      if game_data[game_id]["bidder"] + 1 else "")
                + "\n\n"
                + game_data[game_id]["players"][game_data[game_id]
                                                ["turn"]].mention_markdown()
                + ", it's your turn to bid!",
                reply_markup=ReplyKeyboardMarkup(keyboard, selective=True, one_time_keyboard=True, resize_keyboard=True))


dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('stop', stop))
dispatcher.add_handler(CallbackQueryHandler(inline_button))
dispatcher.add_handler(MessageHandler(Filters.text & BidFilter(), bid))
dispatcher.add_handler(MessageHandler(Filters.text & CardFilter(), card))

updater.start_polling()
