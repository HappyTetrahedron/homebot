import random
from unicodedata import normalize


PERM_OWNER = 100
PERM_ADMIN = 50
PERM_USER = 10

PERMISSIONS = [
    PERM_OWNER,
    PERM_ADMIN,
    PERM_USER,
]


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
    "Splendiferous",
    "Superb",
    "Brilliant",
    "Cool beans",
    "Sweet",
]

EXCLAMATIONS = [
    "Oh no!",
    "Yikes!",
    "Aww...",
    "Damn...",
    "Aw no!",
    ">.<",
    "Whoopsie!",
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
    "Oh, can you repeat that?",
    "No way!",
    "I knew it!",
]


def get_affirmation():
    return random.choice(AFFIRMATIONS)

def get_exclamation():
    return random.choice(EXCLAMATIONS)

def get_generic_response():
    return random.choice(GENERIC_RESPONSES)


def fuzzy_match(query, items, name_getter, min_words=2, min_chars_first_word=3, min_chars_subseq_words=2, min_chars_total=5):
    matches_found = []
    query_parts = to_words(query, ",")
    for part_index, part in enumerate(query_parts):
        query_words = part.strip().lower().split(' ')
        for item in items:
            name_words = to_words(name_getter(item))
            for q, query_word in enumerate(query_words):
                for n, name_word in enumerate(name_words):
                    match = len(commonprefix(query_word, name_word))
                    # Heuristic. Start scan from X matching characters onward.
                    if match >= min(min_chars_first_word, len(name_word)):
                        matches = []
                        for nn, next_name_word in enumerate(name_words[n:]):
                            if q+nn < len(query_words):
                                match = len(commonprefix(next_name_word, query_words[q+nn]))
                                # Heuristic. Consider it a match if at least X characters match
                                if match >= min(min_chars_subseq_words, len(next_name_word)):
                                    matches.append(match)
                        # Heuristic. If the product has multiple words, at least X must match.
                        if len(matches) >= min(min_words, len(name_words)):
                            # Heuristic. In total, at least X characters must match (if the product has that many).
                            if sum(matches) >= min(sum([len(w) for w in name_words]), min_chars_total):
                                if not any([match['item'] == item for match in matches_found]):
                                    matches_found.append({
                                        'len': len(matches),
                                        'sum': sum(matches),
                                        'part': part_index,
                                        'word': q,
                                        'item': item,
                                    })

    matches_found.sort(key=lambda m: (m['len'], m['sum']), reverse=True)
    return matches_found


def to_words(string, split_at=" "):
    return normalize('NFD', string.lower()).encode('ascii', 'ignore').decode('ascii').split(split_at)


def commonprefix(a, b):
    if a > b:
        return commonprefix(b, a)
    for i, c in enumerate(a):
        if c != b[i]:
            return a[:i]
    return a

