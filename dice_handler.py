from base_handler import *
import random
import re

COIN_FLIP_REGEX = re.compile('^flip (.+) coins?', flags=re.I)
DICE_ROLL_REGEX = re.compile('^roll.* (\d*)d(\d+)', flags=re.I)

class DiceHandler(BaseHandler):

    def __init__(self, config, messenger):
        super().__init__(config, messenger, "dice", "Dice rolls and coin flips")
     
    def help(self, permission):
        return {
            'summary': "Can roll a die or flip a coin for you.",
            'examples': ["Flip a coin", "Roll a D6", "Roll 3D20", "Flip 5 coins"],
        }

    def matches_message(self, message):
        return (COIN_FLIP_REGEX.match(message) is not None) or (DICE_ROLL_REGEX.match(message) is not None)
    
    def handle(self, message, **kwargs):
        coins = COIN_FLIP_REGEX.match(message)
        if coins is not None:
            return self.coin_flip(coins)
        dice = DICE_ROLL_REGEX.match(message)
        if dice is not None:
            return self.dice_roll(dice)

    def coin_flip(self, match):
        groups = match.groups()
        number = -1
        try:
            number = int(groups[0])
        except:
            pass

        if number < 1:
            number = 1
        if number >= 1000:
            return "You don't really want to do that."


        results = []
        for i in range(number):
            results.append("Heads" if random.getrandbits(1) else "Tails")

        return "Here's your coin flip result:\n\n{}".format(', '.join(results))


    def dice_roll(self, match):
        groups = match.groups()
        amount = -1
        die = -1
        try:
            amount = int(groups[0])
        except:
            pass
        try:
            die = int(groups[1])
        except:
            pass

        if amount < 1:
            amount = 1
        if amount >= 1000:
            return "You don't really want to do that."
        if die < 1:
            return "A Dwhat?"


        results = []
        for i in range(amount):
            results.append(random.randint(1, die))

        if amount == 1:
            return "Here's your D{} dice roll:\n\n{}".format(die, results[0])

        return "Here's your {}D{} dice roll:\n\n{}\n\n= {}".format(amount, die, ' + '.join([str(x) for x in results]), sum(results))
