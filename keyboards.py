import bridge

# from telegram import KeyboardButton


def bid_keyboard(current_bid=-1):
    keyboard = [["⏭ Pass!"]]
    for value in range(1, 8):
        row = []

        max_bid = (value - 1) * 5 + 4
        if max_bid <= current_bid:
            continue

        for suit in range(0, 5):
            bid = (value - 1) * 5 + suit
            if bid > current_bid:
                row.append(bridge.get_bid_from_num(bid))
            else:
                row.append("▪")
        keyboard.append(row)
    return keyboard


def partner_keyboard():
    keyboard = []
    for value in range(14, 1, -1):
        row = []
        for suit in ["♣", "♦", "♥", "♠"]:
            row.append(bridge.get_value_from_num(value) + " " + suit)
        keyboard.append(row)
    return keyboard


def hand_keyboard(hand, valid_suits=bridge.CARD_SUITS):
    CARDS_PER_ROW = 4

    keyboard = []
    # card_list = []
    # for suit in valid_suits:
    #     for value in hand[suit]:
    #         card_list.append(value + " " + suit)

    # while len(card_list) % CARDS_PER_ROW:
    #     card_list.append("▪")

    # for i in range(0, len(card_list), CARDS_PER_ROW):
    #     row = []
    #     for j in range(0, CARDS_PER_ROW):
    #         row.append(card_list[i+j])
    #     keyboard.append(row)

    for suit in valid_suits:
        # keyboard.append([suit])
        card_list = hand[suit].copy()
        while len(card_list) % CARDS_PER_ROW:
            card_list.append("▪")

        for i in range(0, len(card_list), CARDS_PER_ROW):
            row = []
            for j in range(0, CARDS_PER_ROW):
                if card_list[i+j] == "▪":
                    row.append(card_list[i+j])
                else:
                    row.append(card_list[i+j] + " " + suit)
            keyboard.append(row)

    return keyboard
