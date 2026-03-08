import random
import pygame

class Enemy:
    def __init__(self, name, hp, max_hp, attack, x=600, y=300,
                 attacks=None, description="", tier="easy"):
        self.name = name
        self.hp = hp
        self.max_hp = max_hp
        self.attack = attack          # legacy fallback
        self.x = x
        self.y = y
        self.rect = pygame.Rect(self.x, self.y, 50, 50)
        self.description = description
        self.tier = tier

        # Per-enemy attack list  (list of dicts from enemy_registry)
        self.attacks = attacks or []

    def is_alive(self):
        return self.hp > 0

    def take_damage(self, amount):
        self.hp = max(0, self.hp - amount)

    def heal(self, amount):
        """Heal up to max_hp."""
        self.hp = min(self.max_hp, self.hp + amount)

    # ── NEW: unique attack system ──

    def choose_attack(self):
        """Pick a random attack from this enemy's attack list."""
        if not self.attacks:
            # Fallback for legacy enemies with no attack list
            return {
                "name": "Basic Attack",
                "damage": self.attack,
                "miss_chance": 0.0,
                "effect": None,
                "effect_value": None,
                "description": "Attacks!",
            }
        return random.choice(self.attacks)

    def execute_attack(self, attack=None):
        """
        Execute an attack. Returns (attack_dict, damage_dealt, missed).
        If attack is None, picks one randomly.
        """
        if attack is None:
            attack = self.choose_attack()

        # Miss check
        if attack["miss_chance"] > 0 and random.random() < attack["miss_chance"]:
            return attack, 0, True  # missed

        damage = attack["damage"]
        return attack, damage, False  # hit

    # ── Legacy method kept for backward compat ──

    def roll_attack(self):
        return max(1, self.attack + random.randint(-2, 2))

    # ── Drawing ──

    def draw(self, screen):
        if not self.is_alive():
            return

        # Enemy body color by tier
        tier_colors = {
            "easy":   (100, 200, 100),
            "medium": (200, 180, 50),
            "hard":   (200, 80, 80),
            "boss":   (180, 50, 200),
        }
        color = tier_colors.get(self.tier, (255, 0, 0))
        pygame.draw.rect(screen, color, self.rect)

        # HP bar
        hp_ratio = self.hp / self.max_hp
        pygame.draw.rect(screen, (255, 0, 0), (self.x, self.y - 10, 50, 5))
        pygame.draw.rect(screen, (0, 255, 0), (self.x, self.y - 10, 50 * hp_ratio, 5))

        # Name + HP text
        font = pygame.font.SysFont(None, 24)
        name_text = font.render(f"{self.name}", True, (255, 255, 255))
        screen.blit(name_text, (self.x, self.y - 30))
        hp_text = pygame.font.SysFont(None, 20).render(f"HP: {self.hp}/{self.max_hp}", True, (255, 255, 255))
        screen.blit(hp_text, (self.x, self.y + 55))