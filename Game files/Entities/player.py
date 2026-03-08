import pygame
import os

_SPRITE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "NONIMPORTEDASSETS", "sprites-character")
_ASSET_DIR  = os.path.join(os.path.dirname(__file__), "..", "..", "NONIMPORTEDASSETS")

# Module-level cache so images are only loaded once
_hp_bar_empty = None
_hp_bar_full  = None
_walk_frames  = []   # walking_01 – walking_04
_idle_frames  = []   # idling_01  – idling_04

def _load_assets():
    global _hp_bar_empty, _hp_bar_full, _walk_frames, _idle_frames
    if _hp_bar_empty is None:
        _hp_bar_empty = pygame.image.load(
            os.path.join(_ASSET_DIR, "hp-bar-empty.png")).convert_alpha()
        _hp_bar_full  = pygame.image.load(
            os.path.join(_ASSET_DIR, "hp-bar-full.png")).convert_alpha()

    if not _walk_frames:
        for i in range(1, 6):
            _walk_frames.append(
                pygame.image.load(
                    os.path.join(_SPRITE_DIR, f"walking_0{i}.png")
                ).convert_alpha()
            )

    if not _idle_frames:
        for i in range(1, 5):
            _idle_frames.append(
                pygame.image.load(
                    os.path.join(_SPRITE_DIR, f"idling_0{i}.png")
                ).convert_alpha()
            )


class Player:
    DISPLAY_H = 80

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.max_hp  = 100
        self.hp      = 100
        self.defense = 0
        self.rect    = pygame.Rect(self.x, self.y, 48, 48)

        self.mode         = "walk"   # "walk" | "battle"
        self._frame_idx   = 0
        self._frame_timer = 0
        self._frame_ms    = 140      # ms per animation frame

    def set_mode(self, mode):
        if mode != self.mode:
            self.mode       = mode
            self._frame_idx = 0

    def draw(self, screen):
        _load_assets()

        frames = _walk_frames if self.mode == "walk" else _idle_frames
        if not frames:
            pygame.draw.rect(screen, (0, 255, 0), self.rect)
        else:
            # Advance animation — simple forward loop
            now = pygame.time.get_ticks()
            if now - self._frame_timer >= self._frame_ms:
                self._frame_timer = now
                self._frame_idx = (self._frame_idx + 1) % len(frames)

            raw = frames[self._frame_idx]
            # Scale to DISPLAY_H, preserve aspect ratio
            scale  = self.DISPLAY_H / raw.get_height()
            disp_w = int(raw.get_width() * scale)
            disp_h = self.DISPLAY_H
            sprite = pygame.transform.scale(raw, (disp_w, disp_h))

            # Draw centred on rect, bottom-aligned
            sx = self.rect.centerx - disp_w // 2
            sy = self.rect.bottom  - disp_h
            screen.blit(sprite, (sx, sy))

        # HP bar using images, centred above the sprite
        bar_w, bar_h = 60, 12
        bar_x = self.rect.centerx - bar_w // 2
        bar_y = self.rect.bottom - self.DISPLAY_H - 16
        hp_ratio = max(0.0, self.hp / self.max_hp)

        empty_scaled = pygame.transform.scale(_hp_bar_empty, (bar_w, bar_h))
        full_scaled  = pygame.transform.scale(_hp_bar_full,  (bar_w, bar_h))
        screen.blit(empty_scaled, (bar_x, bar_y))
        if hp_ratio > 0:
            fill_w = int(bar_w * hp_ratio)
            screen.blit(full_scaled, (bar_x, bar_y),
                        area=pygame.Rect(0, 0, fill_w, bar_h))
