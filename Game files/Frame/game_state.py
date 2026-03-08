from Cards.All_cards import get_starter_pair
from Entities.enemy_registry import get_encounter_order

class GameState:
    def __init__(self, player):
        self.player = player
        self.monsters_defeated = 0
        self.damage_multiplier = 1.0
        # Randomized starter cards (permanent)
        self.cards_in_deck = get_starter_pair()
        self.cards_in_hand = []

        # Battle effect state
        self.dodge_active = False
        self.poison_active = False
        self.poison_turns = 0
        self.poison_damage = 5
        self.charging_card = None

        # Turn-based combat state
        self.player_skip_turns = 0
        self.player_damage_modifier = 1.0

        # Progressive enemy encounters
        self.current_enemy_index = 0
        self.encounter_order = get_encounter_order()

        # Selected flashcard deck
        self.selected_deck_path = None

        # ── Revival system ──
        self.all_wrong_questions = []    # all wrong Qs across all quizzes
        self.has_revived = False          # True after first revival (can only revive once)
        self.revival_available = True     # False after using revival
        self.saved_deck_snapshot = []     # snapshot of cards_in_deck at death for revival
        self.saved_hp = 100              # HP at death (restored on revival)

        # ── Stacking debuffs (from 0/3 quiz) ──
        self.blindness_chance = 0.0      # extra miss chance on player attacks, caps at 0.6
        self.confusion_chance = 0.0      # chance to skip turn involuntarily, caps at 0.6

        # ── Global Reward Tracking ──
        self.seen_reward_cards = set()

    def get_next_enemy_template(self):
        """Return the next enemy template, or None if all defeated."""
        if self.current_enemy_index < len(self.encounter_order):
            return self.encounter_order[self.current_enemy_index]
        return None

    def advance_enemy(self):
        """Move to the next enemy in the progression."""
        self.current_enemy_index += 1
        self.monsters_defeated += 1

    def reset_battle_effects(self):
        """Reset per-battle status effects."""
        self.dodge_active = False
        self.poison_active = False
        self.poison_turns = 0
        self.charging_card = None
        self.player_skip_turns = 0
        self.player_damage_modifier = 1.0

    def all_enemies_defeated(self):
        """True if player has beaten every enemy in the encounter order."""
        return self.current_enemy_index >= len(self.encounter_order)

    def snapshot_for_revival(self):
        """Save current state for potential revival."""
        self.saved_deck_snapshot = self.cards_in_deck.copy()
        self.saved_hp = self.player.hp

    def revive_player(self):
        """Restore player to pre-death state. Can only be used once."""
        self.player.hp = max(50, self.saved_hp)  # At least 50 HP on revive
        self.cards_in_deck = self.saved_deck_snapshot.copy()
        self.has_revived = True
        self.revival_available = False
        self.all_wrong_questions = []

    def apply_quiz_debuff(self):
        """
        Called when player gets 0/3 on quiz.
        Stacks one random debuff type, up to its cap.
        """
        import random
        debuff_types = ["damage", "blindness", "confusion"]
        chosen = random.choice(debuff_types)

        if chosen == "damage":
            # Double damage (caps at 4x)
            self.damage_multiplier = min(4.0, self.damage_multiplier * 2)
        elif chosen == "blindness":
            # Blindness: +20% miss chance (caps at 60%)
            self.blindness_chance = min(0.6, self.blindness_chance + 0.2)
        elif chosen == "confusion":
            # Confusion: +20% skip chance (caps at 60%)
            self.confusion_chance = min(0.6, self.confusion_chance + 0.2)

