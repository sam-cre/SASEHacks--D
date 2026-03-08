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

        # ── Turn-based state ──
        self.player_turn = True         # True = player's turn, False = enemy's turn
        self.waiting_for_messages = False  # True = messages are playing, block input
        self.turn_phase = "player"      # "player", "enemy", "done"

    # -------------------------
    # PLAYER ACTIONS
    # -------------------------

    def player_attack(self, card):
        """
        Player plays a card.
        Applies damage_modifier from debuffs.
        Returns (damage_dealt, card_name).
        """
        raw_damage = card.roll_damage()

        # Apply player damage modifier (from enemy debuffs like Disgust, Rotate)
        modifier = self.game_state.player_damage_modifier
        damage = int(raw_damage * modifier)

        target = self.get_active_enemy()

        if target:
            target.take_damage(damage)
            self.last_player_damage = damage

            if modifier < 1.0:
                self.battle_log.append(
                    f"You played {card.name} and dealt {damage} damage! (debuffed)"
                )
            else:
                self.battle_log.append(
                    f"You played {card.name} and dealt {damage} damage to {target.name}!"
                )

            if not target.is_alive():
                self.battle_log.append(f"{target.name} was defeated!")
                self.game_state.monsters_defeated += 1

        # Reset damage modifier after it's been used
        self.game_state.player_damage_modifier = 1.0

        return damage

    # -------------------------
    # ENEMY ACTIONS
    # -------------------------

    def enemy_attack(self):
        """
        Active enemy picks and executes a random attack.
        Returns (attack_dict, final_damage, missed, effect_applied).
        """
        enemy = self.get_active_enemy()

        if not enemy:
            return None, 0, False, None

        attack, raw_damage, missed = enemy.execute_attack()

        if missed:
            self.battle_log.append(
                f"{enemy.name} used {attack['name']}... but it missed!"
            )
            return attack, 0, True, None

        # Apply game_state damage_multiplier (from failed question waves)
        multiplier = self.game_state.damage_multiplier
        final_damage = int(raw_damage * multiplier)

        # Check dodge
        if self.game_state.dodge_active:
            if random.random() < 0.5:
                self.battle_log.append(
                    f"{enemy.name} used {attack['name']}, but you dodged!"
                )
                self.game_state.dodge_active = False
                return attack, 0, True, None
            else:
                self.game_state.dodge_active = False

        # Apply damage to player
        if final_damage > 0:
            self.player.hp = max(0, self.player.hp - final_damage)
            self.last_enemy_damage = final_damage

        # Log the attack
        if multiplier > 1:
            self.battle_log.append(
                f"{enemy.name} used {attack['name']} for {final_damage} damage! "
                f"(x{multiplier} penalty active)"
            )
        elif final_damage > 0:
            self.battle_log.append(
                f"{enemy.name} used {attack['name']} for {final_damage} damage!"
            )

        # Apply status effects
        effect_applied = None
        effect = attack.get("effect")
        effect_value = attack.get("effect_value")

        if effect == "skip_turn" and effect_value:
            self.game_state.player_skip_turns = effect_value
            effect_applied = f"You are stunned for {effect_value} turn(s)!"
            self.battle_log.append(effect_applied)

        elif effect == "attack_debuff" and effect_value:
            self.game_state.player_damage_modifier = effect_value
            effect_applied = "Your attack power was reduced!"
            self.battle_log.append(effect_applied)

        elif effect == "half_damage" and effect_value:
            self.game_state.player_damage_modifier = 0.5
            effect_applied = "Your attacks will deal half damage next turn!"
            self.battle_log.append(effect_applied)

        elif effect == "drain" and effect_value:
            heal_amount = effect_value
            enemy.heal(heal_amount)
            effect_applied = f"{enemy.name} drained {heal_amount} HP!"
            self.battle_log.append(effect_applied)

        return attack, final_damage, False, effect_applied

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
            "enemy_attack": None,
            "enemy_missed": False,
            "effect_applied": None,
            "player_skipped": False,
        }

        # Check if player must skip
        if self.game_state.player_skip_turns > 0:
            self.game_state.player_skip_turns -= 1
            self.battle_log.append("You can't move!")
            results["player_skipped"] = True

            # Enemy still attacks even when player skips
            if self.get_active_enemy():
                attack, dmg, missed, effect = self.enemy_attack()
                results["enemy_attack"] = attack
                results["enemy_damage"] = dmg
                results["enemy_missed"] = missed
                results["effect_applied"] = effect

            results["battle_lost"] = self.check_loss()
            results["player_defeated"] = self.check_loss()
            return results

        # Player attacks
        results["player_damage"] = self.player_attack(card)
        results["enemy_defeated"] = not self.get_active_enemy_including_just_defeated()

        # Enemy only attacks back if still alive
        if self.get_active_enemy():
            attack, dmg, missed, effect = self.enemy_attack()
            results["enemy_attack"] = attack
            results["enemy_damage"] = dmg
            results["enemy_missed"] = missed
            results["multiplier"] = self.game_state.damage_multiplier
            results["effect_applied"] = effect

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