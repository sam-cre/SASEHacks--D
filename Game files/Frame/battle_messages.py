"""
Pokémon-style battle message queue.
Messages display one at a time with a typewriter effect at the bottom of the screen.
"""
import pygame
import os

# Message types for color coding
MSG_ATTACK  = "attack"
MSG_EFFECT  = "effect"
MSG_HP_LOSS = "hp_loss"
MSG_INFO    = "info"
MSG_MISS    = "miss"

MSG_COLORS = {
    MSG_ATTACK:  (255, 255, 100),   # Yellow
    MSG_EFFECT:  (150, 200, 255),   # Light blue
    MSG_HP_LOSS: (255, 100, 100),   # Red
    MSG_INFO:    (255, 255, 255),   # White
    MSG_MISS:    (180, 180, 180),   # Grey
}

_FONT_CACHE = {}
_PIXEL_FONT_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "PressStart2P-Regular.ttf")
)

def _font(size):
    size = max(8, int(size * 0.72))
    if size not in _FONT_CACHE:
        try:
            _FONT_CACHE[size] = pygame.font.Font(_PIXEL_FONT_PATH, size)
        except Exception:
            _FONT_CACHE[size] = pygame.font.SysFont(None, size)
    return _FONT_CACHE[size]

class BattleMessage:
    def __init__(self, text, msg_type=MSG_INFO, duration=1500):
        self.text = text
        self.msg_type = msg_type
        self.duration = duration          # ms to display
        self.color = MSG_COLORS.get(msg_type, (255, 255, 255))


class MessageQueue:
    def __init__(self):
        self.messages = []                # list of BattleMessage
        self.current_index = 0
        self.char_index = 0               # typewriter position
        self.timer = 0                    # ms since current message started showing fully
        self.typewriter_speed = 30        # ms per character
        self.last_char_time = 0
        self.fully_revealed = False
        self.active = False               # True while messages are being displayed

    def push(self, text, msg_type=MSG_INFO, duration=1500):
        """Add a message to the queue."""
        self.messages.append(BattleMessage(text, msg_type, duration))
        if not self.active:
            self.active = True
            self.current_index = len(self.messages) - 1
            self._reset_typewriter()

    def push_attack(self, attacker, attack_name, damage, is_player=True):
        """Convenience: push an attack message."""
        if is_player:
            self.push(f"You used {attack_name}!  Dealt {damage} damage!", MSG_ATTACK)
        else:
            self.push(f"{attacker} used {attack_name}!  Dealt {damage} damage!", MSG_ATTACK)

    def push_miss(self, attacker, attack_name, is_player=True):
        if is_player:
            self.push(f"You used {attack_name}... but it missed!", MSG_MISS)
        else:
            self.push(f"{attacker} used {attack_name}... but it missed!", MSG_MISS)

    def push_effect(self, text):
        self.push(text, MSG_EFFECT)

    def push_hp(self, text):
        self.push(text, MSG_HP_LOSS)

    def push_info(self, text):
        self.push(text, MSG_INFO)

    def _reset_typewriter(self):
        self.char_index = 0
        self.fully_revealed = False
        self.timer = 0
        self.last_char_time = pygame.time.get_ticks()

    def is_busy(self):
        """True while there are still messages to display."""
        return self.active

    def click_advance(self):
        """Called on mouse click — skip typewriter or advance to next message."""
        if not self.active:
            return
        if not self.fully_revealed:
            # Reveal entire message instantly
            msg = self._current_msg()
            if msg:
                self.char_index = len(msg.text)
                self.fully_revealed = True
                self.timer = pygame.time.get_ticks()
        else:
            # Advance to next message
            self._advance()

    def update(self):
        """Call every frame."""
        if not self.active:
            return

        msg = self._current_msg()
        if not msg:
            self.active = False
            return

        now = pygame.time.get_ticks()

        if not self.fully_revealed:
            # Typewriter tick
            if now - self.last_char_time >= self.typewriter_speed:
                self.char_index += 1
                self.last_char_time = now
                if self.char_index >= len(msg.text):
                    self.char_index = len(msg.text)
                    self.fully_revealed = True
                    self.timer = now
        else:
            # Auto-advance after duration
            if now - self.timer >= msg.duration:
                self._advance()

    def _current_msg(self):
        if 0 <= self.current_index < len(self.messages):
            return self.messages[self.current_index]
        return None

    def _advance(self):
        self.current_index += 1
        if self.current_index >= len(self.messages):
            # All messages shown — reset
            self.messages.clear()
            self.current_index = 0
            self.active = False
        else:
            self._reset_typewriter()

    def draw(self, screen):
        """Draw message box at bottom of screen."""
        if not self.active:
            return

        msg = self._current_msg()
        if not msg:
            return

        # Message box background
        box_rect = pygame.Rect(20, 500, 760, 80)
        pygame.draw.rect(screen, (20, 20, 40), box_rect)
        pygame.draw.rect(screen, (200, 200, 200), box_rect, 2)

        # Typewriter text
        visible_text = msg.text[:self.char_index]
        font = _font(28)
        text_surf = font.render(visible_text, True, msg.color)
        screen.blit(text_surf, (box_rect.x + 15, box_rect.y + 15))

        # "Click to continue" hint when fully revealed
        if self.fully_revealed:
            hint_font = _font(18)
            hint = hint_font.render("▼ click to continue", True, (150, 150, 150))
            screen.blit(hint, (box_rect.x + 600, box_rect.y + 55))
