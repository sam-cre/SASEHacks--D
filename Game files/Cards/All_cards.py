import random
from Cards.Cards import Card

# =============================================
# STARTER CARDS (permanent, randomized pairs)
# =============================================

STARTER_PAIR_A = [
    Card("Sand Throw", 6, 10, "Gator hurls sand at the enemy",
         attack_type="ranged", rarity="starter", permanent=True),
    Card("Rock Throw", 6, 10, "Gator hurls a rock at the enemy",
         attack_type="ranged", rarity="starter", permanent=True),
]

STARTER_PAIR_B = [
    Card("Stick Poke", 8, 12, "Gator pokes the enemy with a stick",
         attack_type="physical", rarity="starter", permanent=True),
    Card("Eye Poke", 8, 12, "Gator pokes the enemy in the eye",
         attack_type="physical", rarity="starter", permanent=True),
]

def get_starter_pair():
    """Returns 2 starter cards — one random pick from each pair."""
    card_a = random.choice(STARTER_PAIR_A)
    card_b = random.choice(STARTER_PAIR_B)
    # Return fresh copies so runtime state doesn't bleed
    return [
        Card(card_a.name, card_a.damage_min, card_a.damage_max, card_a.description,
             card_a.attack_type, card_a.effect, card_a.effect_chance,
             card_a.rarity, card_a.permanent, card_a.charge_turns),
        Card(card_b.name, card_b.damage_min, card_b.damage_max, card_b.description,
             card_b.attack_type, card_b.effect, card_b.effect_chance,
             card_b.rarity, card_b.permanent, card_b.charge_turns),
    ]

# =============================================
# COMMON REWARD POOL
# =============================================

COMMON_CARDS = [
    Card("Tail Whip", 10, 35, "Gator whips with his tail",
         attack_type="physical", rarity="common"),
    Card("Gator Bite", 10, 25, "Gator chomps on the enemy",
         attack_type="physical", rarity="common"),
    Card("Scratch", 10, 20, "Gator scratches the enemy",
         attack_type="physical", rarity="common"),
    Card("Snot Bubble", 10, 20, "Gator spits a bubble of snot — chance of poison",
         attack_type="ranged", effect="poison", effect_chance=0.3, rarity="common"),
    Card("Water Bubble", 10, 25, "Gator spits a bubble of water",
         attack_type="ranged", rarity="common"),
    Card("Barrel Roll", 0, 0, "Gator rolls out of the way — 50% dodge next attack",
         attack_type="defensive", effect="dodge", effect_chance=0.5, rarity="common"),
]

# =============================================
# RARE REWARD POOL
# =============================================

RARE_CARDS = [
    Card("Water Barrage", 10, 25, "Fires Water Bubble 2-3 times in a row",
         attack_type="ranged", effect="multi_hit", effect_chance=1.0, rarity="rare"),
    Card("Death Roll", 35, 55, "Gator rolls on the enemy dealing massive damage",
         attack_type="physical", rarity="rare"),
    Card("Super Whip", 35, 45, "Upgraded Tail Whip — 50% chance to stun",
         attack_type="physical", effect="stun", effect_chance=0.5, rarity="rare"),
]

# =============================================
# SUPER RARE REWARD POOL (1% spawn)
# =============================================

SUPER_RARE_CARDS = [
    Card("Chud Attack", 9999, 9999, "Gator pulls out his laptop and builds a hackathon winner — instakill",
         attack_type="special", effect="instakill", effect_chance=1.0, rarity="super_rare"),
]

# =============================================
# REWARD HELPERS
# =============================================

ALL_REWARD_CARDS = COMMON_CARDS + RARE_CARDS + SUPER_RARE_CARDS

def _copy_card(template):
    """Create a fresh Card copy from a template."""
    return Card(template.name, template.damage_min, template.damage_max,
                template.description, template.attack_type, template.effect,
                template.effect_chance, template.rarity, template.permanent,
                template.charge_turns)

def get_reward_pool(count=3):
    """
    Returns `count` random cards for the reward screen.
    Weighted: 10% super rare, 30% rare, 60% common.
    """
    result = []
    for _ in range(count):
        roll = random.random()
        if roll < 0.10 and SUPER_RARE_CARDS:
            template = random.choice(SUPER_RARE_CARDS)
        elif roll < 0.40 and RARE_CARDS:
            template = random.choice(RARE_CARDS)
        else:
            template = random.choice(COMMON_CARDS)
        result.append(_copy_card(template))
    return result