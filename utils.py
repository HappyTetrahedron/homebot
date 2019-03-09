import random


AFFIRMATIONS = [
    "Cool",
    "Nice",
    "Doing great",
    "Awesome",
    "Okey dokey",
    "Neat",
    "Whoo",
    "Wonderful",
    "Splendid",
]

GENERIC_RESPONSES = [
    "I see.",
    "Oh yeah.",
    "Okay",
    "Oh, I see",
    "So it has come to this...",
    "lol",
    "Whoa",
    "Really?",
    "Tell me more about that",
    "and then what happened?",
]


def get_affirmation():
    return random.choice(AFFIRMATIONS)


def get_generic_response():
    return random.choice(GENERIC_RESPONSES)
