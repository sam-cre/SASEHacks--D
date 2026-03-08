import random
import os
import pygame
import math
from difflib import SequenceMatcher

# HP bar images — loaded once at module level
_ASSET_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "NONIMPORTEDASSETS")
_ENEMY_SPRITE_DIR = os.path.join(_ASSET_DIR, "sprites-character")
_ENEMY_ANIM_DIR = os.path.join(_ASSET_DIR, "sprite")
_hp_bar_empty = None
_hp_bar_full  = None
_enemy_sprite_cache = {}
_enemy_name_sprite_cache = {}

def _load_hp_images():
    global _hp_bar_empty, _hp_bar_full
    if _hp_bar_empty is None:
        _hp_bar_empty = pygame.image.load(
            os.path.join(_ASSET_DIR, "hp-bar-empty.png")).convert_alpha()
        _hp_bar_full = pygame.image.load(
            os.path.join(_ASSET_DIR, "hp-bar-full.png")).convert_alpha()

def _load_enemy_sprite(path):
    if path not in _enemy_sprite_cache:
        try:
            _enemy_sprite_cache[path] = pygame.image.load(path).convert_alpha()
        except Exception:
            _enemy_sprite_cache[path] = None
    return _enemy_sprite_cache[path]

def _normalize_name(s):
    return "".join(ch.lower() for ch in s if ch.isalnum())

def _pick_enemy_sprite_path(enemy_name):
    norm_name = _normalize_name(enemy_name)
    if norm_name in _enemy_name_sprite_cache:
        return _enemy_name_sprite_cache[norm_name]

    # Explicit matches for known naming gaps.
    overrides = {
        "sludge": "slime1.png",
        "natbat": "bat.png",
        "vexshroom": "vexshrooms.png",
        "tombworm": "worm.png",
        "thewarden": "warden.png",
        "warden": "warden.png",
    }
    if norm_name in overrides:
        p = os.path.join(_ENEMY_SPRITE_DIR, overrides[norm_name])
        _enemy_name_sprite_cache[norm_name] = p if os.path.exists(p) else None
        return _enemy_name_sprite_cache[norm_name]

    # Fallback: choose the most similar .png in sprites-character.
    candidates = []
    if os.path.isdir(_ENEMY_SPRITE_DIR):
        for fname in os.listdir(_ENEMY_SPRITE_DIR):
            if not fname.lower().endswith(".png"):
                continue
            base = _normalize_name(os.path.splitext(fname)[0])
            if base.startswith("walking") or base.startswith("idling"):
                continue
            candidates.append(fname)

    best_path = None
    best_score = 0.0
    for fname in candidates:
        base = _normalize_name(os.path.splitext(fname)[0])
        score = SequenceMatcher(None, norm_name, base).ratio()
        if base in norm_name or norm_name in base:
            score += 0.25
        if score > best_score:
            best_score = score
            best_path = os.path.join(_ENEMY_SPRITE_DIR, fname)

    # Keep rectangle fallback if nothing is reasonably close.
    if best_score < 0.20:
        best_path = None
    _enemy_name_sprite_cache[norm_name] = best_path
    return best_path

def _get_enemy_anim_paths(enemy_name):
    norm = _normalize_name(enemy_name)
    anim_map = {
        "vexshroom": ("vexshroom_idle.gif", "vexshroom_attack.gif"),
        "tombworm": ("tombworm_idle.gif", "tombworm_attack.gif"),
        "thewarden": ("warden_idle.gif", "warden_attack.gif"),
        "warden": ("warden_idle.gif", "warden_attack.gif"),
    }
    pair = anim_map.get(norm)
    if not pair:
        return None, None
    idle = os.path.join(_ENEMY_ANIM_DIR, pair[0])
    attack = os.path.join(_ENEMY_ANIM_DIR, pair[1])
    return (idle if os.path.exists(idle) else None,
            attack if os.path.exists(attack) else None)

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
        self._hit_shake_until = 0
        self._attack_anim_until = 0
        self._death_anim_start = 0
        self._death_anim_ms = 450

    def is_alive(self):
        return self.hp > 0

    def is_death_animation_done(self):
        if self.hp > 0:
            return False
        if self._death_anim_start == 0:
            return False
        return pygame.time.get_ticks() - self._death_anim_start >= self._death_anim_ms

    def take_damage(self, amount):
        self.hp = max(0, self.hp - amount)
        self._damage_flash_until = pygame.time.get_ticks() + 300  # flash for 300 ms
        self._hit_shake_until = pygame.time.get_ticks() + 180
        if self.hp <= 0 and self._death_anim_start == 0:
            self._death_anim_start = pygame.time.get_ticks()

    def trigger_attack_anim(self, duration_ms=260):
        self._attack_anim_until = pygame.time.get_ticks() + duration_ms

    def _get_enemy_png_sprite(self):
        idle_anim, attack_anim = _get_enemy_anim_paths(self.name)
        if idle_anim or attack_anim:
            now = pygame.time.get_ticks()
            if now < self._attack_anim_until and attack_anim:
                return _load_enemy_sprite(attack_anim)
            if idle_anim:
                return _load_enemy_sprite(idle_anim)

        sprite_path = _pick_enemy_sprite_path(self.name)
        if not sprite_path:
            return None
        return _load_enemy_sprite(sprite_path)

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
        if self.hp <= 0 and self.is_death_animation_done():
            return

        _load_hp_images()
        now = pygame.time.get_ticks()

        shake_x = 0
        if now < self._hit_shake_until:
            shake_x = -4 if ((now // 26) % 2 == 0) else 4
        if self.hp <= 0:
            # Stronger jitter while dying.
            shake_x = -8 if ((now // 20) % 2 == 0) else 8
        # Gentle idle bob while not in attack frame.
        float_y = 0
        if self.hp > 0 and now >= self._attack_anim_until:
            float_y = int(math.sin(now / 380.0) * 4)

        # Enemy body color by tier
        tier_colors = {
            "easy":   (100, 200, 100),
            "medium": (200, 180, 50),
            "hard":   (200, 80, 80),
            "boss":   (180, 50, 200),
        }
        color = tier_colors.get(self.tier, (255, 0, 0))
        draw_rect = self.rect.move(shake_x, float_y)

        enemy_sprite = self._get_enemy_png_sprite()
        if enemy_sprite:
            # Match player-style sizing: scale by target height.
            sh = max(1, draw_rect.height)
            scale = sh / enemy_sprite.get_height()
            sw = max(1, int(enemy_sprite.get_width() * scale))
            sprite = pygame.transform.scale(enemy_sprite, (sw, sh))
            if self.hp <= 0 and self._death_anim_start:
                progress = min(1.0, (now - self._death_anim_start) / self._death_anim_ms)
                tint = pygame.Surface((sw, sh), pygame.SRCALPHA)
                tint.fill((255, 0, 0, int(180 * progress)))
                sprite.blit(tint, (0, 0))
                sprite.set_alpha(max(0, int(255 * (1.0 - progress))))
            sx = draw_rect.centerx - sw // 2
            sy = draw_rect.bottom - sh
            screen.blit(sprite, (sx, sy))
        else:
            if self.hp <= 0 and self._death_anim_start:
                progress = min(1.0, (now - self._death_anim_start) / self._death_anim_ms)
                death_color = (
                    min(255, int(color[0] * (1 - progress) + 255 * progress)),
                    int(color[1] * (1 - progress)),
                    int(color[2] * (1 - progress)),
                )
                tmp = pygame.Surface((draw_rect.width, draw_rect.height), pygame.SRCALPHA)
                tmp.fill((*death_color, max(0, int(255 * (1.0 - progress)))))
                screen.blit(tmp, draw_rect.topleft)
            else:
                pygame.draw.rect(screen, color, draw_rect)

        # Red damage flash overlay
        if now < self._damage_flash_until:
            flash = pygame.Surface((draw_rect.width, draw_rect.height), pygame.SRCALPHA)
            # Intensity fades from 200→0 over the 300 ms window
            alpha = int(200 * (self._damage_flash_until - now) / 300)
            flash.fill((255, 0, 0, alpha))
            screen.blit(flash, draw_rect.topleft)

        # HP bar using images — centred on rect (hide during death effect)
        if self.hp <= 0:
            return
        bar_w, bar_h = 80, 12
        bar_x = draw_rect.centerx - bar_w // 2
        bar_y = draw_rect.top - 18
        hp_ratio = max(0.0, self.hp / self.max_hp)

        empty_scaled = pygame.transform.scale(_hp_bar_empty, (bar_w, bar_h))
        full_scaled  = pygame.transform.scale(_hp_bar_full,  (bar_w, bar_h))
        screen.blit(empty_scaled, (bar_x, bar_y))
        if hp_ratio > 0:
            fill_w = int(bar_w * hp_ratio)
            screen.blit(full_scaled, (bar_x, bar_y),
                        area=pygame.Rect(0, 0, fill_w, bar_h))

        # Name + HP text — white with black outline, anchored to rect
        name_font = pygame.font.SysFont(None, 24)
        hp_font   = pygame.font.SysFont(None, 20)

        def _outlined_enemy(surf, text, fnt, pos):
            ox, oy = pos
            for dx, dy in ((-1,-1),(-1,1),(1,-1),(1,1),(-1,0),(1,0),(0,-1),(0,1)):
                surf.blit(fnt.render(text, True, (0, 0, 0)), (ox+dx, oy+dy))
            surf.blit(fnt.render(text, True, (255, 255, 255)), pos)

        # Put HP numbers on top.
        _outlined_enemy(screen, f"HP: {self.hp}/{self.max_hp}", hp_font,
                        (draw_rect.x, draw_rect.top - 38))
        _outlined_enemy(screen, self.name, name_font, (draw_rect.x, draw_rect.bottom + 5))
