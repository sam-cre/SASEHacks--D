"""
Enemy Registry — defines all enemies, their stats, and unique attacks.
Each enemy has a list of attacks with: name, damage, miss_chance, and effect.
Effects: skip_turn(N), half_damage, attack_debuff, drain, None
"""
import random

# ─────────────────────────────────────────────
#  ATTACK DEFINITIONS
# ─────────────────────────────────────────────

def make_attack(name, damage, miss_chance=0.0, effect=None, effect_value=None, description=""):
    return {
        "name": name,
        "damage": damage,
        "miss_chance": miss_chance,       # 0.0–1.0
        "effect": effect,                 # None, "skip_turn", "half_damage", "attack_debuff", "drain"
        "effect_value": effect_value,     # e.g. turns to skip, drain amount
        "description": description,
    }

# ─────────────────────────────────────────────
#  ENEMY TEMPLATES
# ─────────────────────────────────────────────

ENEMY_TEMPLATES = [
    # ── EASY ──
    {
        "name": "Sludge",
        "description": "A slimeball with one eye",
        "tier": "easy",
        "hp_range": (20, 20),
        "attacks": [
            make_attack("Slime Throw", 12, effect="skip_turn", effect_value=1,
                        description="Throws slime, halting you for one turn!"),
            make_attack("Disgust", 0, effect="attack_debuff", effect_value=0.5,
                        description="Disgusts you, halving your attack next turn!"),
        ],
    },
    {
        "name": "Natbat",
        "description": "A fast bat",
        "tier": "easy",
        "hp_range": (25, 25),
        "attacks": [
            make_attack("Sky Dive", 15, miss_chance=0.20,
                        description="Dives from the sky!"),
            make_attack("Bite", 10, miss_chance=0.20,
                        description="Bites you with sharp fangs!"),
        ],
    },

    # ── MEDIUM ──
    {
        "name": "Vexshroom",
        "description": "A mushroom with legs that can cast spells",
        "tier": "medium",
        "hp_range": (35, 35),
        "attacks": [
            make_attack("Doze", 0, effect="skip_turn", effect_value=1,
                        description="Casts a sleep spell — you skip a turn!"),
            make_attack("Vine Drain", 0, effect="drain_percent", effect_value=0.15,
                        description="Vines drain 15% of your life and heal the enemy!"),
        ],
    },
    {
        "name": "Tombworm",
        "description": "A worm with burrowing ability",
        "tier": "medium",
        "hp_range": (40, 40),
        "attacks": [
            make_attack("Coffin Slam", 25,
                        description="Crashes a segment into you!"),
            make_attack("Confusion", 0, effect="skip_turn", effect_value=2,
                        description="You become confused and can't move for 2 turns!"),
        ],
    },

    # ── HARD ──
    {
        "name": "The Warden",
        "description": "An armored guard that wields keys as a weapon",
        "tier": "hard",
        "hp_range": (120, 120),
        "attacks": [
            make_attack("Iron Maiden", 35,
                        description="Summons an iron maiden!"),
            make_attack("Key Throw", 20,
                        description="Throws keys at you!"),
        ],
    },

    # ── BOSS ──
    {
        "name": "The Cube",
        "description": "Nobody knows what it is. Nobody asks.",
        "tier": "boss",
        "hp_range": (180, 180),
        "attacks": [
            make_attack("Corner Jab", 40,
                        description="Strikes with a sharp edge!"),
            make_attack("Flatten", 50, miss_chance=0.30,
                        description="Slowly rolls toward you — massive but slow!"),
            make_attack("Rotate", 0, effect="half_damage", effect_value=1,
                        description="Rotates mysteriously — your attacks deal half damage next turn!"),
        ],
    },
]

# ─────────────────────────────────────────────
#  ENCOUNTER ORDER  (progressive difficulty)
# ─────────────────────────────────────────────

def get_encounter_order():
    """
    Returns a list of enemy template dicts in order:
      Easy1 → Easy2 → Medium1 → Medium2 → Hard → Boss
    Shuffles within each tier so variety changes per run.
    """
    easy = [e for e in ENEMY_TEMPLATES if e["tier"] == "easy"]
    medium = [e for e in ENEMY_TEMPLATES if e["tier"] == "medium"]
    hard = [e for e in ENEMY_TEMPLATES if e["tier"] == "hard"]
    boss = [e for e in ENEMY_TEMPLATES if e["tier"] == "boss"]

    random.shuffle(easy)
    random.shuffle(medium)

    return easy + medium + hard + boss


def spawn_enemy_from_template(template, x=600, y=300):
    """Create an Enemy instance from a registry template."""
    from Entities.enemies import Enemy
    hp = random.randint(*template["hp_range"])
    return Enemy(
        name=template["name"],
        hp=hp,
        max_hp=hp,
        attack=0,          # unused — attacks come from attack list
        x=x, y=y,
        attacks=template["attacks"],
        description=template["description"],
        tier=template["tier"],
    )
