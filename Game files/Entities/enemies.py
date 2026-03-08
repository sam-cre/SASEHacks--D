import random
import os
import pygame

# HP bar images — loaded once at module level
_ASSET_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "NONIMPORTEDASSETS")
_hp_bar_empty = None
_hp_bar_full  = None

def _load_hp_images():
    global _hp_bar_empty, _hp_bar_full
    if _hp_bar_empty is None:
        _hp_bar_empty = pygame.image.load(
            os.path.join(_ASSET_DIR, "hp-bar-empty.png")).convert_alpha()
        _hp_bar_full = pygame.image.load(
            os.path.join(_ASSET_DIR, "hp-bar-full.png")).convert_alpha()

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

        # Damage flash: timestamp (ms) of last hit, 0 = no flash
        self._damage_flash_until = 0

    def is_alive(self):
        return self.hp > 0

    def take_damage(self, amount):
        self.hp = max(0, self.hp - amount)
        self._damage_flash_until = pygame.time.get_ticks() + 300  # flash for 300 ms

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

        _load_hp_images()

        # Enemy body color by tier
        tier_colors = {
            "easy":   (100, 200, 100),
            "medium": (200, 180, 50),
            "hard":   (200, 80, 80),
            "boss":   (180, 50, 200),
        }
        color = tier_colors.get(self.tier, (255, 0, 0))
        pygame.draw.rect(screen, color, self.rect)

        # Red damage flash overlay
        now = pygame.time.get_ticks()
        if now < self._damage_flash_until:
            flash = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            # Intensity fades from 200→0 over the 300 ms window
            alpha = int(200 * (self._damage_flash_until - now) / 300)
            flash.fill((255, 0, 0, alpha))
            screen.blit(flash, self.rect.topleft)

        # HP bar using images
        bar_w, bar_h = 80, 12
        bar_x = self.x - (bar_w - self.rect.width) // 2
        bar_y = self.y - 18
        hp_ratio = max(0.0, self.hp / self.max_hp)

        empty_scaled = pygame.transform.scale(_hp_bar_empty, (bar_w, bar_h))
        full_scaled  = pygame.transform.scale(_hp_bar_full,  (bar_w, bar_h))
        screen.blit(empty_scaled, (bar_x, bar_y))
        if hp_ratio > 0:
            fill_w = int(bar_w * hp_ratio)
            screen.blit(full_scaled, (bar_x, bar_y),
                        area=pygame.Rect(0, 0, fill_w, bar_h))

        # Name + HP text — white with black outline
        name_font = pygame.font.SysFont(None, 24)
        hp_font   = pygame.font.SysFont(None, 20)

        def _outlined_enemy(surf, text, fnt, pos):
            ox, oy = pos
            for dx, dy in ((-1,-1),(-1,1),(1,-1),(1,1),(-1,0),(1,0),(0,-1),(0,1)):
                surf.blit(fnt.render(text, True, (0, 0, 0)), (ox+dx, oy+dy))
            surf.blit(fnt.render(text, True, (255, 255, 255)), pos)

        _outlined_enemy(screen, self.name, name_font, (self.x, self.y - 38))
        _outlined_enemy(screen, f"HP: {self.hp}/{self.max_hp}", hp_font,
                        (self.x, self.y + 55))