import os
import pygame
import math

_SPRITE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "NONIMPORTEDASSETS", "sprites-character")
_ASSET_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "NONIMPORTEDASSETS")

# Module-level cache so images are only loaded once.
_hp_bar_empty = None
_hp_bar_full = None
_mascot_sprite = None


def _load_assets():
    global _hp_bar_empty, _hp_bar_full, _mascot_sprite
    if _hp_bar_empty is None:
        _hp_bar_empty = pygame.image.load(
            os.path.join(_ASSET_DIR, "hp-bar-empty.png")
        ).convert_alpha()
        _hp_bar_full = pygame.image.load(
            os.path.join(_ASSET_DIR, "hp-bar-full.png")
        ).convert_alpha()

    if _mascot_sprite is None:
        _mascot_sprite = pygame.image.load(
            os.path.join(_ASSET_DIR, "homeMascot.png")
        ).convert_alpha()


class Player:
    DISPLAY_H = 160

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.max_hp = 100
        self.hp = 100
        self.defense = 0
        self.rect = pygame.Rect(self.x, self.y, 48, 48)

        self.mode = "walk"  # "walk" | "battle"

        # Damage reaction state.
        self._last_hp_seen = self.hp
        self._hurt_shake_until = 0

    def set_mode(self, mode):
        self.mode = mode

    def draw(self, screen):
        _load_assets()
        now = pygame.time.get_ticks()

        # Trigger a short shake when HP drops.
        if self.hp < self._last_hp_seen:
            self._hurt_shake_until = now + 220
        self._last_hp_seen = self.hp

        shake_x = 0
        if now < self._hurt_shake_until:
            shake_x = -4 if ((now // 28) % 2 == 0) else 4
        bob_y = 0
        if self.mode == "walk":
            bob_y = int(math.sin(now / 180.0) * 4)

        if _mascot_sprite is None:
            pygame.draw.rect(screen, (0, 255, 0), self.rect)
        else:
            scale = self.DISPLAY_H / _mascot_sprite.get_height()
            disp_w = int(_mascot_sprite.get_width() * scale)
            disp_h = self.DISPLAY_H
            sprite = pygame.transform.scale(_mascot_sprite, (disp_w, disp_h))

            sx = self.rect.centerx - disp_w // 2 + shake_x
            sy = self.rect.bottom - disp_h + bob_y
            screen.blit(sprite, (sx, sy))

        # Only show the sprite HP bar while in battle.
        if self.mode == "battle":
            bar_w, bar_h = 60, 12
            bar_x = self.rect.centerx - bar_w // 2 + shake_x
            bar_y = self.rect.bottom - self.DISPLAY_H - 16
            hp_ratio = max(0.0, self.hp / self.max_hp)

            empty_scaled = pygame.transform.scale(_hp_bar_empty, (bar_w, bar_h))
            full_scaled = pygame.transform.scale(_hp_bar_full, (bar_w, bar_h))
            screen.blit(empty_scaled, (bar_x, bar_y))
            if hp_ratio > 0:
                fill_w = int(bar_w * hp_ratio)
                screen.blit(
                    full_scaled,
                    (bar_x, bar_y),
                    area=pygame.Rect(0, 0, fill_w, bar_h),
                )
