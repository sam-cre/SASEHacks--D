import random

QUESTIONS_PER_WAVE = 10
PASS_THRESHOLD = 0.5
MAX_DAMAGE_MULTIPLIER = 4

class BattleLogic:
    def __init__(self, player, enemies, game_state):
        self.player = player
        self.enemies = enemies
        self.game_state = game_state

        self.turn_count = 0
        self.battle_log = []            # list of strings describing what happened
        self.last_player_damage = 0    # last damage player dealt — for renderer
        self.last_enemy_damage = 0     # last damage enemy dealt — for renderer
        self.last_multiplier = 1       # tracks if penalty was active — for renderer

    # -------------------------
    # PLAYER ACTIONS
    # -------------------------

    def player_attack(self, card):
        """
        Player plays a card.
        Rolls damage from the card, applies it to the active enemy.
        Returns the damage dealt.
        """
        damage = card.roll_damage()
        target = self.get_active_enemy()

        if target:
            target.take_damage(damage)
            self.last_player_damage = damage
            self.battle_log.append(
                f"You played {card.name} and dealt {damage} damage to {target.name}!"
            )

            if not target.is_alive():
                self.battle_log.append(f"{target.name} was defeated!")
                self.game_state.monsters_defeated += 1

        return damage

    # -------------------------
    # ENEMY ACTIONS
    # -------------------------

    def enemy_attack(self):
        """
        Active enemy attacks the player.
        Applies game_state.damage_multiplier if player failed question wave.
        Returns (final_damage, multiplier_used) tuple for renderer to display.
        """
        enemy = self.get_active_enemy()

        if not enemy:
            return 0, 1

        raw_damage = enemy.roll_attack()
        reduced_damage = max(0, raw_damage - self.player.defense)
        multiplier = self.game_state.damage_multiplier
        final_damage = reduced_damage * multiplier

        self.player.hp = max(0, self.player.hp - final_damage)
        self.last_enemy_damage = final_damage
        self.last_multiplier = multiplier

        if multiplier > 1:
            self.battle_log.append(
                f"{enemy.name} attacks for {final_damage} damage! "
                f"(x{multiplier} penalty active)"
            )
        else:
            self.battle_log.append(
                f"{enemy.name} attacks for {final_damage} damage!"
            )

        return final_damage, multiplier

    # -------------------------
    # TURN RESOLUTION
    # -------------------------

    def resolve_turn(self, card):
        """
        Resolves a full turn in one call:
        1. Player attacks with chosen card
        2. Enemy attacks back (only if still alive)
        3. Increments turn counter
        Returns a dict of everything that happened this turn for the renderer.
        """
        self.turn_count += 1
        results = {
            "turn": self.turn_count,
            "player_damage": 0,
            "enemy_damage": 0,
            "multiplier": 1,
            "enemy_defeated": False,
            "player_defeated": False,
            "battle_won": False,
            "battle_lost": False,
        }

        # Player attacks
        results["player_damage"] = self.player_attack(card)
        results["enemy_defeated"] = not self.get_active_enemy_including_just_defeated()

        # Enemy only attacks back if still alive
        if self.get_active_enemy():
            dmg, mult = self.enemy_attack()
            results["enemy_damage"] = dmg
            results["multiplier"] = mult

        # Check end conditions
        results["battle_won"] = self.check_win()
        results["battle_lost"] = self.check_loss()
        results["player_defeated"] = self.check_loss()

        return results

    # -------------------------
    # WIN / LOSS CONDITIONS
    # -------------------------

    def check_win(self):
        """Returns True when every enemy in the wave is dead"""
        return all(not e.is_alive() for e in self.enemies)

    def check_loss(self):
        """Returns True when player HP hits 0"""
        return self.player.hp <= 0

    # -------------------------
    # ENEMY TARGETING
    # -------------------------

    def get_active_enemy(self):
        """Returns the first enemy still alive — current battle target"""
        for enemy in self.enemies:
            if enemy.is_alive():
                return enemy
        return None

    def get_active_enemy_including_just_defeated(self):
        """
        Used immediately after player_attack to check if the enemy
        we just hit is still alive. Prevents enemy attacking after death.
        """
        return self.get_active_enemy()

    # -------------------------
    # BATTLE LOG
    # -------------------------

    def get_recent_log(self, lines=4):
        """
        Returns the last N lines of the battle log.
        Pass this into your renderer to display recent events.
        """
        return self.battle_log[-lines:]

    def clear_log(self):
        self.battle_log = []

    # -------------------------
    # STATE SNAPSHOTS FOR RENDERER
    # -------------------------

    def get_render_state(self):
        """
        Returns everything the renderer needs in one clean dict.
        Call this every frame in draw() — zero logic in renderer needed.
        """
        active_enemy = self.get_active_enemy()
        return {
            "player_hp": self.player.hp,
            "player_max_hp": self.player.max_hp,
            "player_defense": self.player.defense,
            "enemy_hp": active_enemy.hp if active_enemy else 0,
            "enemy_max_hp": active_enemy.max_hp if active_enemy else 0,
            "enemy_name": active_enemy.name if active_enemy else "Defeated",
            "last_player_damage": self.last_player_damage,
            "last_enemy_damage": self.last_enemy_damage,
            "damage_multiplier": self.game_state.damage_multiplier,
            "turn_count": self.turn_count,
            "recent_log": self.get_recent_log(),
            "battle_won": self.check_win(),
            "battle_lost": self.check_loss(),
        }