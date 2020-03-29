from math import floor
from random import random

DECK_OF_52 = [{"value": "2", "suit": "♣"}, {"value": "2", "suit": "♦"}, {"value": "2", "suit": "♥"}, {"value": "2", "suit": "♠"}, {"value": "3", "suit": "♣"}, {"value": "3", "suit": "♦"}, {"value": "3", "suit": "♥"}, {"value": "3", "suit": "♠"}, {"value": "4", "suit": "♣"}, {"value": "4", "suit": "♦"}, {"value": "4", "suit": "♥"}, {"value": "4", "suit": "♠"}, {"value": "5", "suit": "♣"}, {"value": "5", "suit": "♦"}, {"value": "5", "suit": "♥"}, {"value": "5", "suit": "♠"}, {"value": "6", "suit": "♣"}, {"value": "6", "suit": "♦"}, {"value": "6", "suit": "♥"}, {"value": "6", "suit": "♠"}, {"value": "7", "suit": "♣"}, {"value": "7", "suit": "♦"}, {"value": "7", "suit": "♥"}, {"value": "7", "suit": "♠"}, {"value": "8", "suit": "♣"}, {"value": "8", "suit": "♦"}, {
    "value": "8", "suit": "♥"}, {"value": "8", "suit": "♠"}, {"value": "9", "suit": "♣"}, {"value": "9", "suit": "♦"}, {"value": "9", "suit": "♥"}, {"value": "9", "suit": "♠"}, {"value": "10", "suit": "♣"}, {"value": "10", "suit": "♦"}, {"value": "10", "suit": "♥"}, {"value": "10", "suit": "♠"}, {"value": "J", "suit": "♣"}, {"value": "J", "suit": "♦"}, {"value": "J", "suit": "♥"}, {"value": "J", "suit": "♠"}, {"value": "Q", "suit": "♣"}, {"value": "Q", "suit": "♦"}, {"value": "Q", "suit": "♥"}, {"value": "Q", "suit": "♠"}, {"value": "K", "suit": "♣"}, {"value": "K", "suit": "♦"}, {"value": "K", "suit": "♥"}, {"value": "K", "suit": "♠"}, {"value": "A", "suit": "♣"}, {"value": "A", "suit": "♦"}, {"value": "A", "suit": "♥"}, {"value": "A", "suit": "♠"}]

BID_SUITS = ["♣", "♦", "♥", "♠", "🚫"]
CARD_SUITS = ["♣", "♦", "♥", "♠"]


def get_value_from_num(num):
    if num == 14:
        return "A"
    elif num == 13:
        return "K"
    elif num == 12:
        return "Q"
    elif num == 11:
        return "J"
    else:
        return str(num)


def get_num_from_value(val):
    if val == "A":
        return 14
    elif val == "K":
        return 13
    elif val == "Q":
        return 12
    elif val == "J":
        return 11
    else:
        return int(val)


# def get_suit_order(val):
#     if val == "♣":
#         return 0
#     elif val == "♦":
#         return 1
#     elif val == "♥":
#         return 2
#     elif val == "♠":
#         return 3


def get_bid_from_num(num):
    # num is an int from 0 to 34, where 0 = 1C, 1 = 1H, 2 = 1S etc.

    suit_num = num % 5
    suit = BID_SUITS[suit_num]
    value = floor(num / 5) + 1
    return str(value) + " " + suit


def get_num_from_bid(bid):
    # bid is a string in the format <number><space><suit> e.g. "1 ♣"
    return (int(bid[0]) - 1) * 5 + BID_SUITS.index(bid[2])


# Durstenfeld Shuffle:
def shuffle(deck):
    for i in range(len(deck)-1, 0, -1):
        j = floor(random() * (i + 1))
        deck[i], deck[j] = deck[j], deck[i]


def get_points(hand):
    points = 0
    count = {
        "♣": 0,
        "♦": 0,
        "♥": 0,
        "♠": 0
    }

    for card in hand:
        count[card["suit"]] += 1
        if card["value"] == "A":
            points += 4
        elif card["value"] == "K":
            points += 3
        elif card["value"] == "Q":
            points += 2
        elif card["value"] == "J":
            points += 1

    for suit in count:
        if count[suit] >= 5:
            points += count[suit] - 4
    return points


def wash_required(hands):
    POINTS_TO_WASH = 4
    for hand in hands:
        if get_points(hand) <= POINTS_TO_WASH:
            return True
    return False


def generate_hands():
    deck = DECK_OF_52.copy()
    hands = []
    temp_hands = []

    shuffle(deck)
    for i in range(0, 52, 13):
        temp_hands.append(deck[i:i+13])

    while wash_required(temp_hands):
        shuffle(deck)
        temp_hands = []
        for i in range(0, 52, 13):
            temp_hands.append(deck[i:i+13])

    # TODO: Sort hand by suit then number
    for i in range(0, 4):
        temp_hand = temp_hands[i]
        hand = {
            "♣": [],
            "♦": [],
            "♥": [],
            "♠": []
        }
        for card in temp_hand:
            suit = card["suit"]
            hand[suit].append(card["value"])
        hands.append(hand)

        for suit in hand:
            hand[suit].sort(key=get_num_from_value, reverse=True)
    return hands


def generate_hand_string(hand):
    card_list = []
    for suit in CARD_SUITS:
        if len(hand[suit]):
            card_list.append(suit + "  -  " + ", ".join(hand[suit]))
        else:
            card_list.append(suit + "  -  🚫")
    return "\n".join(card_list)


def get_valid_suits(hand, trump_suit=None, current_suit=None, trump_broken=False):
    if trump_suit == "🚫":
        trump_suit = None
    valid_suits = []
    if current_suit:
        if hand[current_suit]:
            return [current_suit]
        else:
            for suit in CARD_SUITS:
                if hand[suit]:
                    valid_suits.append(suit)
    else:
        for suit in CARD_SUITS:
            if hand[suit] and (suit != trump_suit or trump_broken):
                valid_suits.append(suit)

        if not valid_suits:
            valid_suits = [trump_suit]

    return valid_suits


def compare_cards(played_cards, current_suit, trump_suit=None):
    if trump_suit == "🚫":
        trump_suit = None
    top_player = 0
    top_card = played_cards[top_player].split()
    for i in range(1, len(played_cards)):
        current_card = played_cards[i].split()
        if (current_card[1] == trump_suit
                and top_card[1] != trump_suit
            or current_card[1] == current_suit
                and top_card[1] != trump_suit
                and top_card[1] != current_suit
            or current_card[1] == top_card[1]
                and get_num_from_value(current_card[0]) > get_num_from_value(top_card[0])):
            top_player = i
            top_card = current_card
    return top_player
