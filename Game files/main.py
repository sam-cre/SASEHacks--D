import pygame
import os
import sys

# Initialize pygame before font operations inside components
pygame.init()
pygame.mixer.init()

# Resolution — set by the Qt launcher via env vars, fallback to 800x600 standalone
WIN_W = int(os.environ.get("PYGAME_WIN_W", 800))
WIN_H = int(os.environ.get("PYGAME_WIN_H", 600))

from Frame.stage_manager import StageManager, Stage
from Frame.scroll_engine import ScrollEngine
from Frame.game_state import GameState
from Frame.battle_messages import MessageQueue, MSG_ATTACK, MSG_EFFECT, MSG_HP_LOSS, MSG_INFO, MSG_MISS
from Frame.deck_selector import DeckSelector
from Frame.core import BattleLogic
from Entities.player import Player
from Entities.enemies import Enemy
from Entities.enemy_registry import spawn_enemy_from_template
from Cards.Cards import Card
from Cards.All_cards import get_reward_pool, COMMON_CARDS, RARE_CARDS, SUPER_RARE_CARDS, _copy_card
from question_wave.question_controller import QuestionScreen
import random

screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.RESIZABLE)
pygame.display.set_caption("SASEHacks Game")
clock = pygame.time.Clock()

# ── Music ──────────────────────────────────────────────────────────────
_MUSIC_ROOT    = os.path.join(os.path.dirname(__file__), "..", "music")
_BATTLE_TRACKS = [
    os.path.join(_MUSIC_ROOT, "battleMusic", f)
    for f in os.listdir(os.path.join(_MUSIC_ROOT, "battleMusic"))
    if f.endswith((".mp3", ".ogg", ".wav"))
]
_UI_TRACKS = [
    os.path.join(_MUSIC_ROOT, "uiMusic", f)
    for f in os.listdir(os.path.join(_MUSIC_ROOT, "uiMusic"))
    if f.endswith((".mp3", ".ogg", ".wav"))
]
_FULL_VOLUME   = 0.6
_DUCKED_VOLUME = 0.15
_current_music_type = None   # "battle" | "ui" | None

def _play_music(track_type):
    """Switch to a random track of the given type if not already playing it."""
    global _current_music_type
    if track_type == _current_music_type:
        return
    tracks = _BATTLE_TRACKS if track_type == "battle" else _UI_TRACKS
    if not tracks:
        return
    pygame.mixer.music.stop()
    pygame.mixer.music.load(random.choice(tracks))
    pygame.mixer.music.set_volume(_FULL_VOLUME)
    pygame.mixer.music.play(-1)   # loop forever
    _current_music_type = track_type

def _set_music_volume(vol):
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.set_volume(vol)

# Setup
player = Player(x=200, y=300)
game_state = GameState(player)
scroll = ScrollEngine()
stage_manager = StageManager(game_state)
question_screen = QuestionScreen(screen, game_state, stage_manager)

# FlashcardUploads path (relative to Game files/)
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "FlashcardUploads")
UPLOADS_DIR = os.path.normpath(UPLOADS_DIR)

deck_selector = DeckSelector(screen, game_state, UPLOADS_DIR)

# Message queue for Pokémon-style battle messages
msg_queue = MessageQueue()

# Font cache — keyed by size so we never recreate the same font twice
_font_cache = {}
_UI_FONT_PATH = os.path.join(os.path.dirname(__file__), "..", "PressStart2P-Regular.ttf")
_UI_FONT_SCALE = 0.72
def _font(size):
    size = max(10, size)
    px_size = max(8, int(size * _UI_FONT_SCALE))
    if size not in _font_cache:
        try:
            _font_cache[size] = pygame.font.Font(_UI_FONT_PATH, px_size)
        except Exception:
            _font_cache[size] = pygame.font.SysFont(None, px_size)
    return _font_cache[size]

# Base fonts (800×600 equivalents — use _font(int(48*sf)) etc. for dynamic code)
font = _font(48)
small_font = _font(28)
tiny_font = _font(22)

# HP bar images
_ASSET_DIR = os.path.join(os.path.dirname(__file__), "..", "NONIMPORTEDASSETS")
_hp_bar_empty = pygame.image.load(os.path.join(_ASSET_DIR, "hp-bar-empty.png")).convert_alpha()
_hp_bar_full  = pygame.image.load(os.path.join(_ASSET_DIR, "hp-bar-full.png")).convert_alpha()

# Card art — maps card name → PNG filename
_CARD_ART_FILES = {
    "Sand Throw":    "sandThrow.png",
    "Rock Throw":    "rockThrow.png",
    "Stick Poke":    "stickPoke.png",
    "Tail Whip":     "tailWhip.png",
    "Gator Bite":    "bite.png",
    "Scratch":       "scratch.png",
    "Snot Bubble":   "snotBubble.png",
    "Water Bubble":  "bubble.png",
    "Barrel Roll":   "barrelRoll.png",
    "Water Barrage": "bubblebarrage.png",
    "Death Roll":    "deathRoll.png",
    "Super Whip":    "supaWhip.png",
    "Chud Attack":   "chudAttack.png",
}
_card_art_cache = {}

def _get_card_art(name):
    if name not in _card_art_cache:
        fname = _CARD_ART_FILES.get(name)
        if fname:
            try:
                _card_art_cache[name] = pygame.image.load(
                    os.path.join(_ASSET_DIR, fname)).convert_alpha()
            except Exception:
                _card_art_cache[name] = None
        else:
            _card_art_cache[name] = None
    return _card_art_cache[name]

# Fixed scrolling background: breach.jpg
_backgrounds = []
_pixel_ocean_path = os.path.join(_ASSET_DIR, "breach.jpg")
try:
    _img = pygame.image.load(_pixel_ocean_path).convert()
    _scale = max(WIN_H / _img.get_height(), WIN_W * 1.5 / _img.get_width())
    _w = int(_img.get_width() * _scale)
    _h = int(_img.get_height() * _scale)
    _backgrounds.append(pygame.transform.scale(_img, (_w, _h)))
except Exception as e:
    print(f"[BG] Could not load breach.jpg: {e}")

current_bg = _backgrounds[0] if _backgrounds else None

# State vars
active_screen = "deck_select"
overworld_timer = 0
overworld_duration = 3000
reward_timer = 0
reward_duration = 2000
battle_timer = 0
walk_timer = 0
walk_duration = 2000
enemy = None
battle_logic = None
drawn_cards = []
card_rects = []
reward_cards = []
reward_rects = []
cards_picked = 0
max_picks = 1
reward_close_pending = False
reward_close_timer = 0
enemy_stunned = False
enemy_turn_pending = False

# Revival quiz state
revival_questions = []
revival_index = 0
revival_score = 0
revival_choice_rects = []
revival_show_result = False
revival_result_timer = 0


# ─────────────────────────────────────────────
#  PERFORMANCE-BASED REWARD POOL
# ─────────────────────────────────────────────

def get_performance_reward(count=3):
    """
    Returns `count` unique cards, avoiding globally seen cards.
    60% common, 30% rare, 10% super rare.
    """
    result = []
    # Mix already used globally with this current batch
    used_names = game_state.seen_reward_cards.copy()
    attempts = 0
    while len(result) < count and attempts < 100:
        attempts += 1
        roll = random.random()
        if roll < 0.10 and SUPER_RARE_CARDS:
            template = random.choice(SUPER_RARE_CARDS)
        elif roll < 0.40 and RARE_CARDS:
            template = random.choice(RARE_CARDS)
        else:
            template = random.choice(COMMON_CARDS)
        if template.name not in used_names:
            used_names.add(template.name)
            game_state.seen_reward_cards.add(template.name)
            result.append(_copy_card(template))
            
    # Fallback if we completely run out of unseen cards
    if len(result) < count:
        game_state.seen_reward_cards.clear()
        while len(result) < count:
            template = random.choice(COMMON_CARDS)
            result.append(_copy_card(template))
            
    return result


# ─────────────────────────────────────────────
#  CALLBACK FUNCTIONS
# ─────────────────────────────────────────────

def start_deck_select():
    global active_screen
    active_screen = "deck_select"
    deck_selector._scan_decks()

def start_overworld():
    global active_screen, battle_timer, overworld_timer, current_bg
    active_screen = "overworld"
    scroll.start_scroll()
    battle_timer = pygame.time.get_ticks()
    overworld_timer = pygame.time.get_ticks()
    if _backgrounds:
        current_bg = _backgrounds[0]
        scroll.offset = 0
    player.set_mode("walk")

def start_battle():
    global active_screen, enemy, drawn_cards, card_rects, battle_logic
    active_screen = "battle"
    scroll.stop_scroll()
    player.set_mode("battle")

    template = game_state.get_next_enemy_template()
    if template is None:
        stage_manager.transition_to(Stage.VICTORY)
        return

    enemy = spawn_enemy_from_template(template)
    game_state.reset_battle_effects()
    battle_logic = BattleLogic(player, [enemy], game_state)
    
    global enemy_turn_pending
    enemy_turn_pending = False

    # Snapshot state for potential revival
    game_state.snapshot_for_revival()

    msg_queue.push_info(f"A wild {enemy.name} appeared!")
    msg_queue.push_info(f'"{enemy.description}"')

    deck_copy = game_state.cards_in_deck.copy()
    random.shuffle(deck_copy)
    drawn_cards = deck_copy[:3]
    _recalc_card_rects()

def _recalc_card_rects(panel_rect=None):
    global card_rects
    card_rects = []
    sw, sh = screen.get_size()
    if panel_rect is None:
        panel_rect = pygame.Rect(int(sw * 0.03), int(sh * 0.60), int(sw * 0.94), int(sh * 0.28))
    total = len(drawn_cards)
    if total <= 0:
        return
    card_h = int(panel_rect.height * 0.82)
    card_w = max(130, min(int(panel_rect.width * 0.30), int(card_h * 0.82)))
    total_card_w = total * card_w
    gap = max(10, (panel_rect.width - total_card_w) // (total + 1))
    y = panel_rect.y + (panel_rect.height - card_h) // 2
    for i in range(total):
        x = panel_rect.x + gap + i * (card_w + gap)
        card_rects.append(pygame.Rect(x, y, card_w, card_h))

def start_post_battle_walk():
    global active_screen, walk_timer, current_bg
    active_screen = "post_battle_walk"
    scroll.start_scroll()
    walk_timer = pygame.time.get_ticks()
    if _backgrounds:
        current_bg = _backgrounds[0]
        scroll.offset = 0
    player.set_mode("walk")

def show_card_select():
    global active_screen
    active_screen = "card_select"

def start_questions():
    global active_screen
    active_screen = "question_wave"
    if game_state.selected_deck_path:
        question_screen.generator.load_deck(game_state.selected_deck_path)
    question_screen.start()

def show_card_reward():
    global active_screen, reward_timer, reward_cards, reward_rects, cards_picked, max_picks
    global reward_close_pending, reward_close_timer
    active_screen = "card_reward"
    reward_timer = pygame.time.get_ticks()
    cards_picked = 0
    reward_close_pending = False
    reward_close_timer = 0

    tier = question_screen.logic.get_performance_tier()

    if tier == "perfect":
        # 3/3 → pick 2 cards
        reward_cards = get_performance_reward(3)
        max_picks = 2
    elif tier == "great":
        # 2/3 → pick 1 card
        reward_cards = get_performance_reward(3)
        max_picks = 1
    elif tier == "ok":
        # 1/3 → no cards, but no debuff
        reward_cards = []
        max_picks = 0
    elif tier == "poor":
        # 0/3 → no cards, stack debuff
        reward_cards = []
        max_picks = 0
        game_state.apply_quiz_debuff()

    reward_rects = []
    sw, sh = screen.get_size()
    card_w = int(sw * 0.21)
    card_h = int(sh * 0.27)
    total = max(1, len(reward_cards))
    gap = (sw - total * card_w) // (total + 1)
    y = int(sh * 0.40)
    for i in range(len(reward_cards)):
        x = gap + i * (card_w + gap)
        reward_rects.append(pygame.Rect(x, y, card_w, card_h))

def start_revival_quiz():
    global active_screen, revival_questions, revival_index, revival_score
    global revival_choice_rects, revival_show_result, revival_result_timer
    active_screen = "revival_quiz"

    # Build quiz from all wrong questions
    revival_questions = game_state.all_wrong_questions.copy()
    random.shuffle(revival_questions)
    revival_index = 0
    revival_score = 0
    revival_choice_rects = []
    revival_show_result = False
    revival_result_timer = 0

def show_game_over():
    global active_screen
    active_screen = "game_over"

def show_victory():
    global active_screen
    active_screen = "victory"

def next_stage():
    if game_state.all_enemies_defeated():
        stage_manager.transition_to(Stage.VICTORY)
    else:
        stage_manager.transition_to(Stage.OVERWORLD)


# ─────────────────────────────────────────────
#  REGISTER STAGE CALLBACKS
# ─────────────────────────────────────────────

stage_manager.register(Stage.DECK_SELECT,     start_deck_select)
stage_manager.register(Stage.OVERWORLD,       start_overworld)
stage_manager.register(Stage.BATTLE,          start_battle)
stage_manager.register(Stage.POST_BATTLE_WALK, start_post_battle_walk)
stage_manager.register(Stage.CARD_SELECT,     show_card_select)
stage_manager.register(Stage.QUESTION_WAVE,   start_questions)
stage_manager.register(Stage.CARD_REWARD,     show_card_reward)
stage_manager.register(Stage.REVIVAL_QUIZ,    start_revival_quiz)
stage_manager.register(Stage.GAME_OVER,       show_game_over)
stage_manager.register(Stage.VICTORY,         show_victory)
stage_manager.register(Stage.NEXT_STAGE,      next_stage)

# Initialization
stage_manager.transition_to(Stage.DECK_SELECT)
stage_manager.check_conditions()


# ─────────────────────────────────────────────
#  BATTLE TURN PROCESSING
# ─────────────────────────────────────────────

def process_battle_turn(card_index):
    global enemy_stunned, enemy_turn_pending

    card = drawn_cards[card_index]

    # Check cooldown
    if card.cooldown_remaining > 0:
        msg_queue.push_info(f"{card.name} is on cooldown! ({card.cooldown_remaining} turns)")
        return

    # Put on cooldown
    card.cooldown_remaining = card.cooldown

    # Confusion debuff check — random involuntary skip
    if game_state.confusion_chance > 0 and random.random() < game_state.confusion_chance:
        msg_queue.push_effect("You're confused and can't act!")
        if enemy and enemy.is_alive():
            enemy_turn_pending = True
        return

    # Check skip turn
    if game_state.player_skip_turns > 0:
        game_state.player_skip_turns -= 1
        msg_queue.push_info("You can't move!")
        if enemy and enemy.is_alive():
            enemy_turn_pending = True
        return

    # Special card effects
    if card.effect == "instakill":
        enemy.hp = 0
        msg_queue.push(f"You used {card.name}! INSTAKILL!", MSG_ATTACK)
        return

    if card.effect == "dodge":
        game_state.dodge_active = True
        msg_queue.push(f"You used {card.name}! Dodge ready (50%)", MSG_EFFECT)
        enemy_turn_pending = True
        return

    if card.effect == "multi_hit":
        hits = random.randint(2, 3)
        total_dmg = 0
        for _ in range(hits):
            dmg = card.roll_damage()
            dmg = int(dmg * game_state.player_damage_modifier)
            total_dmg += dmg
            if enemy:
                enemy.take_damage(dmg)
        game_state.player_damage_modifier = 1.0
        msg_queue.push(f"You used {card.name} x{hits}! Total: {total_dmg} damage!", MSG_ATTACK)
        if enemy and not enemy.is_alive():
            msg_queue.push_info(f"{enemy.name} was defeated!")
        else:
            enemy_turn_pending = True
        return

    # Normal damage — check blindness
    raw_damage = card.roll_damage()
    if game_state.blindness_chance > 0 and random.random() < game_state.blindness_chance:
        msg_queue.push_miss("You", card.name, is_player=True)
        msg_queue.push_effect("Your blindness caused you to miss!")
        enemy_turn_pending = True
        return
    damage = int(raw_damage * game_state.player_damage_modifier)
    game_state.player_damage_modifier = 1.0
    enemy.take_damage(damage)
    msg_queue.push(f"You used {card.name}! Dealt {damage} damage!", MSG_ATTACK)

    if card.effect == "poison" and card.roll_effect():
        game_state.poison_active = True
        game_state.poison_turns = 3
        msg_queue.push_effect(f"{enemy.name} was POISONED!")

    if card.effect == "bleed" and card.roll_effect():
        game_state.bleed_active = True
        msg_queue.push_effect(f"{enemy.name} is BLEEDING!")

    if card.effect == "stun" and card.roll_effect():
        enemy_stunned = True
        msg_queue.push_effect(f"{enemy.name} was STUNNED!")

    # Replace used card
    if not card.permanent:
        drawn_cards.pop(card_index)
        deck_copy = [c for c in game_state.cards_in_deck if c not in drawn_cards]
        if deck_copy:
            random.shuffle(deck_copy)
            drawn_cards.insert(card_index, deck_copy[0])
        _recalc_card_rects()

    if enemy and not enemy.is_alive():
        msg_queue.push_info(f"{enemy.name} was defeated!")
        return

    if not enemy_stunned:
        enemy_turn_pending = True
    else:
        msg_queue.push_info(f"{enemy.name} is stunned and can't move!")
        enemy_stunned = False


def _do_enemy_turn():
    if not enemy or not enemy.is_alive():
        return

    if game_state.bleed_active:
        bleed_dmg = max(1, int(enemy.max_hp * 0.10))
        enemy.take_damage(bleed_dmg)
        msg_queue.push_effect(f"{enemy.name} took {bleed_dmg} BLEED damage!")
        msg_queue.push_hp(f"Enemy HP: {enemy.hp}/{enemy.max_hp}")
        if not enemy.is_alive():
            msg_queue.push_info(f"{enemy.name} bled out!")
            return

    attack = enemy.choose_attack()
    atk_data, damage, missed = enemy.execute_attack(attack)

    if missed:
        msg_queue.push_miss(enemy.name, attack["name"], is_player=False)
        return

    if game_state.dodge_active:
        if random.random() < 0.5:
            msg_queue.push_info(f"{enemy.name} used {attack['name']}, but you dodged!")
            game_state.dodge_active = False
            return
        else:
            game_state.dodge_active = False

    multiplier = game_state.damage_multiplier
    final_damage = int(damage * multiplier)

    if final_damage > 0:
        player.hp = max(0, player.hp - final_damage)
        enemy.trigger_attack_anim()
        if multiplier > 1:
            msg_queue.push(f"{enemy.name} used {attack['name']}! {final_damage} damage! (x{multiplier} penalty)", MSG_ATTACK)
        else:
            msg_queue.push(f"{enemy.name} used {attack['name']}! {final_damage} damage!", MSG_ATTACK)
        msg_queue.push_hp(f"Your HP: {player.hp}/{player.max_hp}")
    else:
        msg_queue.push_info(f"{enemy.name} used {attack['name']}!")

    effect = attack.get("effect")
    effect_value = attack.get("effect_value")

    if effect == "skip_turn" and effect_value:
        game_state.player_skip_turns = effect_value
        msg_queue.push_effect(f"You are stunned for {effect_value} turn(s)!")
    elif effect == "attack_debuff" and effect_value:
        game_state.player_damage_modifier = effect_value
        msg_queue.push_effect("Your attack power was reduced!")
    elif effect == "half_damage" and effect_value:
        game_state.player_damage_modifier = 0.5
        msg_queue.push_effect("Your attacks will deal half damage next turn!")
    elif effect == "drain" and effect_value:
        enemy.heal(effect_value)
        msg_queue.push_effect(f"{enemy.name} drained {effect_value} HP and healed!")
    elif effect == "drain_percent" and effect_value:
        drain_amount = int(player.max_hp * effect_value)
        player.hp = max(0, player.hp - drain_amount)
        enemy.heal(drain_amount)
        msg_queue.push(f"{enemy.name} used {attack['name']}! Drained {drain_amount} HP!", MSG_ATTACK)
        msg_queue.push_hp(f"Your HP: {player.hp}/{player.max_hp}")
    elif effect == "blindness" and effect_value:
        game_state.blindness_chance = min(0.6, game_state.blindness_chance + effect_value)
        msg_queue.push_effect(f"Your accuracy dropped! ({int(game_state.blindness_chance*100)}% miss chance)")

    if player.hp <= 0:
        msg_queue.push_info("You were defeated...")

    # Tick down cooldowns at the end of enemy turn
    for c in game_state.cards_in_deck:
        if c.cooldown_remaining > 0:
            c.cooldown_remaining -= 1


# ─────────────────────────────────────────────
#  DRAWING HELPERS
# ─────────────────────────────────────────────

def _outlined(surf, text, font, color=(255,255,255), outline=(0,0,0), pos=(0,0)):
    """Blit text with a 1-px black outline then white fill."""
    ox, oy = pos
    for dx, dy in ((-1,-1),(-1,1),(1,-1),(1,1),(-1,0),(1,0),(0,-1),(0,1)):
        surf.blit(font.render(text, True, outline), (ox+dx, oy+dy))
    surf.blit(font.render(text, True, color), pos)

def _draw_panel(screen, rect, fill=(20, 24, 32), border=(160, 180, 200), alpha=170):
    panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    base_rect = pygame.Rect(0, 0, rect.width, rect.height)
    # Hard rectangular fill to guarantee full coverage to the border.
    panel.fill((*fill, alpha))
    screen.blit(panel, rect.topleft)
    pygame.draw.rect(screen, border, rect, 2)
    pygame.draw.rect(screen, (20, 20, 24), rect.inflate(-3, -3), 1)

def _get_battle_layout(screen):
    sw, sh = screen.get_size()
    margin = max(12, int(sw * 0.02))
    top_h = max(72, int(sh * 0.14))
    card_h = max(130, int(sh * 0.26))
    msg_h = max(74, int(sh * 0.14))

    top_rect = pygame.Rect(margin, margin, sw - margin * 2, top_h)
    msg_rect = pygame.Rect(margin, sh - margin - msg_h, sw - margin * 2, msg_h)
    card_rect = pygame.Rect(margin, msg_rect.y - margin - card_h, sw - margin * 2, card_h)
    arena_y = top_rect.bottom + margin
    arena_h = max(120, card_rect.y - margin - arena_y)
    arena_rect = pygame.Rect(margin, arena_y, sw - margin * 2, arena_h)

    player_panel = pygame.Rect(top_rect.x + 8, top_rect.y + 8, int(top_rect.width * 0.45), top_rect.height - 16)
    enemy_panel = pygame.Rect(top_rect.right - int(top_rect.width * 0.36) - 8, top_rect.y + 8,
                              int(top_rect.width * 0.36), top_rect.height - 16)

    return {
        "top": top_rect,
        "arena": arena_rect,
        "card_panel": card_rect,
        "message_panel": msg_rect,
        "player_panel": player_panel,
        "enemy_panel": enemy_panel,
    }

def _draw_player_hud(screen, panel_rect=None):
    sw, sh = screen.get_size()
    sf = sh / 600
    hp_ratio = max(0, player.hp / player.max_hp)
    if panel_rect:
        bar_x = panel_rect.x + int(panel_rect.width * 0.05)
        bar_w = int(panel_rect.width * 0.72)
        text_y = panel_rect.y + int(panel_rect.height * 0.10)
    else:
        bar_x = int(sw * 0.025)
        bar_w = int(sw * 0.25)
        text_y = int(sh * 0.017)
    bar_h = int(24 * sf)

    hp_font = _font(int(22 * sf))

    _outlined(screen, f"HP: {player.hp}/{player.max_hp}", hp_font,
              pos=(bar_x, text_y))

    bar_y = text_y + int(18 * sf)
    empty_scaled = pygame.transform.scale(_hp_bar_empty, (bar_w, bar_h))
    full_scaled  = pygame.transform.scale(_hp_bar_full,  (bar_w, bar_h))
    screen.blit(empty_scaled, (bar_x, bar_y))
    if hp_ratio > 0:
        fill_w = int(bar_w * hp_ratio)
        screen.blit(full_scaled, (bar_x, bar_y),
                    area=pygame.Rect(0, 0, fill_w, bar_h))

    revival_y = bar_y + bar_h + int(4 * sf)
    revival_font = _font(int(22 * sf))
    if game_state.revival_available and not game_state.has_revived:
        _outlined(screen, "♥ Revival available", revival_font,
                  color=(100, 255, 200), pos=(bar_x, revival_y))
    elif game_state.has_revived:
        _outlined(screen, "♥ Revival used", revival_font,
                  color=(200, 200, 200), pos=(bar_x, revival_y))


def _draw_card(screen, card, rect, reward_mode=False):
    slot_color = (90, 68, 150) if not reward_mode else (70, 110, 70)
    border_col = (220, 210, 255) if not reward_mode else (180, 230, 180)
    pygame.draw.rect(screen, slot_color, rect, border_radius=10)
    pygame.draw.rect(screen, border_col, rect, 2, border_radius=10)
    inner = rect.inflate(-10, -10)

    if card.rarity == "super_rare":
        bg_color = (150, 50, 200)
    elif card.rarity == "rare":
        bg_color = (180, 140, 50)
    elif card.rarity == "starter":
        bg_color = (120, 120, 180)
    else:
        bg_color = (200, 200, 200) if not reward_mode else (50, 150, 50)

    art = _get_card_art(card.name)
    if art:
        art_box = pygame.Rect(inner.x + 4, inner.y + 4, inner.width - 8, int(inner.height * 0.60))
        if art_box.width > 0 and art_box.height > 0:
            scale = min(art_box.width / art.get_width(), art_box.height / art.get_height())
            aw = int(art.get_width() * scale)
            ah = int(art.get_height() * scale)
            art_scaled = pygame.transform.scale(art, (aw, ah))
            ax = art_box.centerx - aw // 2
            ay = art_box.centery - ah // 2
            screen.blit(art_scaled, (ax, ay))
        text_bg = pygame.Surface((inner.width, inner.height - (art_box.bottom - inner.y)), pygame.SRCALPHA)
        text_bg.fill((15, 15, 24, 170))
        screen.blit(text_bg, (inner.x, art_box.bottom))
        content_y = art_box.bottom + 6
    else:
        overlay = pygame.Surface((inner.width, inner.height), pygame.SRCALPHA)
        overlay.fill((*bg_color, 120))
        screen.blit(overlay, inner.topleft)
        content_y = inner.y + max(6, inner.width // 18)
    pygame.draw.rect(screen, (240, 240, 240), inner, 2, border_radius=8)

    fs_name = max(13, inner.height // 10)
    fs_body = max(11, inner.height // 12)
    pad = max(6, inner.width // 18)
    text_color = (18, 18, 18) if not reward_mode else (245, 245, 245)
    if art:
        text_color = (245, 245, 245)

    screen.blit(_font(fs_name).render(card.name, True, text_color), (inner.x + pad, content_y))
    content_y += int(fs_name * 1.05)
    screen.blit(_font(fs_body).render(f"[{card.attack_type}]", True, (210, 210, 210) if reward_mode else (70, 70, 70)),
                (inner.x + pad, content_y))
    content_y += int(fs_body * 1.1)

    if card.damage_min == card.damage_max:
        dmg_str = f"Dmg: {card.damage_min}"
    elif card.damage_max == 0:
        dmg_str = "No damage"
    else:
        dmg_str = f"Dmg: {card.damage_min}-{card.damage_max}"
    screen.blit(_font(fs_body).render(dmg_str, True, (230, 70, 70) if not reward_mode else (200, 255, 200)),
                (inner.x + pad, content_y))
    content_y += int(fs_body * 1.1)

    if card.effect:
        screen.blit(_font(fs_body).render(f"FX: {card.effect}", True, (95, 190, 255) if reward_mode else (0, 100, 200)),
                    (inner.x + pad, content_y))

    if card.permanent:
        perm = _font(fs_body).render("PERM", True, (255, 255, 255))
        screen.blit(perm, (inner.right - perm.get_width() - pad, inner.bottom - perm.get_height() - pad))

    if card.cooldown_remaining > 0 and not reward_mode:
        cd = _font(fs_body).render(f"CD {card.cooldown_remaining}", True, (255, 0, 0))
        screen.blit(cd, (inner.right - cd.get_width() - pad, inner.y + pad))

    if reward_mode:
        rarity_txt = None
        rarity_col = (255, 255, 255)
        if card.rarity == "super_rare":
            rarity_txt, rarity_col = "SUPER RARE", (255, 100, 255)
        elif card.rarity == "rare":
            rarity_txt, rarity_col = "RARE", (255, 215, 0)
        if rarity_txt:
            rarity = _font(fs_body).render(rarity_txt, True, rarity_col)
            screen.blit(rarity, (inner.right - rarity.get_width() - pad, inner.bottom - rarity.get_height() - pad))

def _draw_hover_card_preview(screen, card, source_rect, reward_mode=False):
    art = _get_card_art(card.name)
    if not art:
        return

    sw, sh = screen.get_size()
    preview_w = int(sw * 0.42)
    preview_h = int(sh * 0.52)
    px = max(12, min(sw - preview_w - 12, source_rect.centerx - preview_w // 2))
    py = max(12, source_rect.y - preview_h - 12)
    if py < int(sh * 0.10):
        py = min(sh - preview_h - 12, source_rect.bottom + 12)

    panel = pygame.Rect(px - 10, py - 10, preview_w + 20, preview_h + 20)
    _draw_panel(screen, panel, fill=(24, 16, 36), border=(185, 155, 240), alpha=230)
    pygame.draw.rect(screen, (245, 245, 255), (px - 1, py - 1, preview_w + 2, preview_h + 2), 1, border_radius=6)

    scale = min(preview_w / art.get_width(), preview_h / art.get_height())
    aw = int(art.get_width() * scale)
    ah = int(art.get_height() * scale)
    art_scaled = pygame.transform.scale(art, (aw, ah))
    ax = px + (preview_w - aw) // 2
    ay = py + (preview_h - ah) // 2
    screen.blit(art_scaled, (ax, ay))

def _draw_battle_message_box(screen, box_rect):
    if not msg_queue.is_busy():
        return
    msg = msg_queue._current_msg()
    if not msg:
        return
    _draw_panel(screen, box_rect, fill=(16, 18, 28), border=(205, 205, 220), alpha=215)
    pad = max(10, int(box_rect.width * 0.02))
    txt_font = _font(max(18, box_rect.height // 3))
    visible_text = msg.text[:msg_queue.char_index]
    lines = _wrap_text(visible_text, txt_font, box_rect.width - pad * 2)
    y = box_rect.y + pad
    for ln in lines[:2]:
        screen.blit(txt_font.render(ln, True, msg.color), (box_rect.x + pad, y))
        y += txt_font.get_height() + 2
    if msg_queue.fully_revealed:
        hint = _font(max(14, box_rect.height // 6)).render("click to continue", True, (170, 170, 185))
        screen.blit(hint, (box_rect.right - hint.get_width() - pad, box_rect.bottom - hint.get_height() - pad))


def _wrap_text(text, font, max_width):
    """Word-wrap text for revival quiz display."""
    words = text.split(' ')
    lines = []
    current_line = ""
    for word in words:
        test_line = f"{current_line} {word}".strip()
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines if lines else [text]


def _draw_revival_quiz(screen):
    """Draw the revival quiz screen."""
    global revival_choice_rects
    sw, sh = screen.get_size()
    sf = sh / 600
    margin = int(sw * 0.07)
    content_w = sw - margin * 2
    screen.fill((40, 10, 10))

    def _ctr(text, fnt, color, y):
        s = fnt.render(text, True, color)
        screen.blit(s, (sw // 2 - s.get_width() // 2, y))

    _ctr("REVIVAL QUIZ", _font(int(48 * sf)), (255, 200, 100), int(sh * 0.03))

    if revival_show_result:
        total = len(revival_questions) if revival_questions else 1
        ratio = revival_score / total
        _ctr(f"Score: {revival_score}/{total}", _font(int(48 * sf)), (255, 255, 255), int(sh * 0.33))
        msg = "You passed! You've been REVIVED!" if ratio >= 0.7 else "You failed... Game Over."
        color = (100, 255, 100) if ratio >= 0.7 else (255, 100, 100)
        _ctr(msg, _font(int(28 * sf)), color, int(sh * 0.43))
        return

    if revival_index >= len(revival_questions):
        return

    q = revival_questions[revival_index]

    info_surf = _font(int(22 * sf)).render(
        f"Answer the questions you got wrong! ({revival_index+1}/{len(revival_questions)})  Need 70% to revive!",
        True, (200, 200, 200))
    screen.blit(info_surf, (sw // 2 - info_surf.get_width() // 2, int(sh * 0.12)))

    q_lines = _wrap_text(q["text"], _font(int(28 * sf)), content_w)
    q_y = int(sh * 0.20)
    for line in q_lines:
        surf = _font(int(28 * sf)).render(line, True, (255, 255, 255))
        screen.blit(surf, (margin, q_y))
        q_y += int(30 * sf)

    revival_choice_rects = []
    y_offset = max(int(sh * 0.35), q_y + int(15 * sf))
    mc_font = _font(int(24 * sf))
    for i, choice in enumerate(q.get("choices", [])):
        wrapped = _wrap_text(f"{i+1}. {choice}", mc_font, content_w - int(30 * sf))
        box_h = max(int(40 * sf), len(wrapped) * int(26 * sf) + int(16 * sf))
        rect = pygame.Rect(margin, y_offset, content_w, box_h)

        hover = rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(screen, (80, 40, 40) if hover else (60, 30, 30), rect, border_radius=6)
        pygame.draw.rect(screen, (255, 200, 100) if hover else (150, 100, 60), rect, 2, border_radius=6)

        text_y = y_offset + int(8 * sf)
        for line in wrapped:
            surf = mc_font.render(line, True, (255, 255, 255))
            screen.blit(surf, (margin + int(15 * sf), text_y))
            text_y += int(26 * sf)

        revival_choice_rects.append(rect)
        y_offset += box_h + int(8 * sf)


# ─────────────────────────────────────────────
#  MAIN GAME LOOP
# ─────────────────────────────────────────────

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # ── WINDOW RESIZE ──
        if event.type == pygame.VIDEORESIZE:
            _recalc_card_rects()

        # ── DECK SELECT ──
        if active_screen == "deck_select":
            if deck_selector.handle_event(event):
                stage_manager.transition_to(Stage.OVERWORLD)

        # ── QUESTION WAVE ──
        elif active_screen == "question_wave":
            question_screen.handle_event(event)

        # ── REVIVAL QUIZ ──
        elif active_screen == "revival_quiz":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not revival_show_result:
                    # Answer a revival question
                    for i, rect in enumerate(revival_choice_rects):
                        if rect.collidepoint(event.pos):
                            q = revival_questions[revival_index]
                            if i == q.get("correct_idx", -1):
                                revival_score += 1
                            revival_index += 1
                            if revival_index >= len(revival_questions):
                                revival_show_result = True
                                revival_result_timer = pygame.time.get_ticks()
                            break

        # ── MOUSE CLICKS ──
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if msg_queue.is_busy():
                msg_queue.click_advance()
                continue

            if active_screen == "battle" and enemy and enemy.is_alive():
                if not msg_queue.is_busy() and not enemy_turn_pending:
                    # Handle skip turns — clicking any card triggers the skip
                    if game_state.player_skip_turns > 0:
                        game_state.player_skip_turns -= 1
                        msg_queue.push_info("You can't move!")
                        if enemy and enemy.is_alive():
                            enemy_turn_pending = True
                    else:
                        for i, rect in enumerate(card_rects):
                            if rect.collidepoint(event.pos):
                                process_battle_turn(i)
                                break

            elif active_screen == "card_reward":
                if reward_close_pending:
                    continue
                if max_picks == 0 or not reward_cards:
                    # Click anywhere to proceed when no cards to pick
                    stage_manager.transition_to(Stage.NEXT_STAGE)
                else:
                    for i, rect in enumerate(reward_rects):
                        if rect.collidepoint(event.pos):
                            card = reward_cards[i]
                            game_state.cards_in_deck.append(card)
                            cards_picked += 1
                            reward_cards.pop(i)
                            reward_rects.pop(i)
                            if card.rarity in ("rare", "super_rare"):
                                reward_close_pending = True
                                reward_close_timer = pygame.time.get_ticks()
                            elif cards_picked >= max_picks:
                                stage_manager.transition_to(Stage.NEXT_STAGE)
                            break

    # ─────────────────────────────────────────
    #  UPDATE
    # ─────────────────────────────────────────
    scroll.update()
    stage_manager.check_conditions()
    msg_queue.update()

    if active_screen == "question_wave":
        question_screen.update()

    if active_screen == "revival_quiz":
        if revival_show_result:
            if pygame.time.get_ticks() - revival_result_timer > 2000:
                total = len(revival_questions) if revival_questions else 1
                ratio = revival_score / total
                if ratio >= 0.7:
                    # Revive! Restore player to full HP and re-enter battle
                    player.hp = player.max_hp
                    game_state.has_revived = True
                    game_state.revival_available = False
                    game_state.all_wrong_questions = []
                    
                    # Reset only player debuffs/status, preserving enemy conditions
                    game_state.dodge_active = False
                    game_state.charging_card = None
                    game_state.player_skip_turns = 0
                    game_state.player_damage_modifier = 1.0
                    
                    msg_queue.push_info("You've been revived with full HP! Fight on!")
                    stage_manager.transition_to(Stage.BATTLE)
                else:
                    stage_manager.transition_to(Stage.GAME_OVER)

    if active_screen == "overworld":
        if pygame.time.get_ticks() - overworld_timer > overworld_duration:
            stage_manager.transition_to(Stage.BATTLE)

    if active_screen == "battle":
        if not msg_queue.is_busy():
            if enemy_turn_pending:
                enemy_turn_pending = False
                _do_enemy_turn()
            elif enemy and not enemy.is_alive():
                if enemy.is_death_animation_done():
                    game_state.advance_enemy()
                    if game_state.all_enemies_defeated():
                        stage_manager.transition_to(Stage.VICTORY)
                    else:
                        stage_manager.transition_to(Stage.POST_BATTLE_WALK)
                    enemy = None
            elif player.hp <= 0:
                # Check if revival is available
                if game_state.revival_available and not game_state.has_revived and game_state.all_wrong_questions:
                    stage_manager.transition_to(Stage.REVIVAL_QUIZ)
                else:
                    stage_manager.transition_to(Stage.GAME_OVER)

    if active_screen == "post_battle_walk":
        if pygame.time.get_ticks() - walk_timer > walk_duration:
            stage_manager.transition_to(Stage.QUESTION_WAVE)

    if active_screen == "card_reward":
        if reward_close_pending:
            if pygame.time.get_ticks() - reward_close_timer > 1000:
                stage_manager.transition_to(Stage.NEXT_STAGE)
        else:
            tier = question_screen.logic.get_performance_tier()
            if tier == "poor" or not reward_cards:
                # No cards to pick — auto-advance after brief delay
                delay = 3500 if tier == "poor" else 2000
                if pygame.time.get_ticks() - reward_timer > delay:
                    stage_manager.transition_to(Stage.NEXT_STAGE)

    # ─────────────────────────────────────────
    #  DRAW
    # ─────────────────────────────────────────
    sw, sh = screen.get_size()
    sf = sh / 600  # scale factor relative to base 600px height
    screen.fill((0, 0, 0))

    if active_screen == "deck_select":
        deck_selector.draw()

    elif active_screen in ["overworld", "battle", "post_battle_walk"]:
        scroll.draw_background(screen, current_bg)
        battle_layout = _get_battle_layout(screen) if active_screen == "battle" else None
        if battle_layout:
            _draw_panel(screen, battle_layout["top"], fill=(8, 12, 20), border=(145, 170, 195), alpha=220)
            _draw_panel(screen, battle_layout["card_panel"], fill=(10, 10, 16), border=(170, 170, 185), alpha=225)
            _draw_panel(screen, battle_layout["message_panel"], fill=(12, 10, 20), border=(210, 210, 220), alpha=230)

        # Position player and enemy relative to screen
        if battle_layout:
            arena = battle_layout["arena"]
            player.rect.x = arena.left + int(arena.width * 0.18)
            player.rect.y = arena.top + int(arena.height * 0.62) - 10
        else:
            player.rect.x = int(sw * 0.18)
            player.rect.y = int(sh * 0.42) - 10
        player.draw(screen)

        if active_screen == "battle" and enemy:
            enemy_h = max(1, int(Player.DISPLAY_H * 0.7))
            enemy_w = enemy_h
            enemy.rect.width = enemy_w
            enemy.rect.height = enemy_h
            if battle_layout:
                arena = battle_layout["arena"]
                enemy.rect.x = arena.left + int(arena.width * 0.70)
                # Keep both sprites aligned on the same vertical line.
                enemy.rect.y = player.rect.y - 15
            else:
                enemy.rect.x = int(sw * 0.68)
                enemy.rect.y = player.rect.y - 15
            enemy.draw(screen)

        if active_screen == "battle":
            _draw_player_hud(screen, battle_layout["player_panel"] if battle_layout else None)

        if active_screen == "overworld":
            ow_surf = _font(int(48 * sf)).render("Overworld (Walking)", True, (255, 255, 255))
            screen.blit(ow_surf, (sw // 2 - ow_surf.get_width() // 2, int(sh * 0.05)))
            template = game_state.get_next_enemy_template()
            if template:
                nx_surf = _font(int(28 * sf)).render(f"Next: {template['name']} ({template['tier'].upper()})", True, (200, 200, 100))
                screen.blit(nx_surf, (sw // 2 - nx_surf.get_width() // 2, int(sh * 0.13)))

        elif active_screen == "battle":
            if enemy:
                enemy_panel = battle_layout["enemy_panel"]
                _draw_panel(screen, enemy_panel, fill=(20, 14, 14), border=(195, 140, 140), alpha=170)
                name_font = _font(max(20, enemy_panel.height // 3))
                enemy_name = name_font.render(enemy.name, True, (245, 245, 245))

                tier_colors = {"easy": (100, 255, 100), "medium": (255, 200, 50), "hard": (255, 80, 80), "boss": (200, 100, 255)}
                tier_col = tier_colors.get(enemy.tier, (255, 255, 255))
                tier_font = _font(max(18, enemy_panel.height // 4))
                tier_surf = tier_font.render(f"[{enemy.tier.upper()}]", True, tier_col)
                spacing = max(6, enemy_panel.height // 10)
                block_h = enemy_name.get_height() + spacing + tier_surf.get_height()
                block_y = enemy_panel.y + (enemy_panel.height - block_h) // 2
                screen.blit(enemy_name, (enemy_panel.centerx - enemy_name.get_width() // 2, block_y))
                screen.blit(tier_surf, (enemy_panel.centerx - tier_surf.get_width() // 2,
                                        block_y + enemy_name.get_height() + spacing))

            _recalc_card_rects(battle_layout["card_panel"])
            hovered_card = None
            hovered_rect = None
            if not msg_queue.is_busy():
                if game_state.player_skip_turns > 0:
                    stun_surf = _font(max(18, int(24 * sf))).render(
                        f"STUNNED! ({game_state.player_skip_turns} turn(s) left) - Click to skip turn",
                        True, (255, 100, 100))
                    stun_y = battle_layout["card_panel"].y + 8
                    screen.blit(stun_surf, (sw // 2 - stun_surf.get_width() // 2, stun_y))
                else:
                    for i, card in enumerate(drawn_cards):
                        if i < len(card_rects):
                            rect = card_rects[i]
                            _draw_card(screen, card, rect)
                            if rect.collidepoint(pygame.mouse.get_pos()):
                                hovered_card = card
                                hovered_rect = rect

            _draw_battle_message_box(screen, battle_layout["message_panel"])
            if hovered_card and hovered_rect:
                _draw_hover_card_preview(screen, hovered_card, hovered_rect, reward_mode=False)

        elif active_screen == "post_battle_walk":
            pb_font = _font(min(int(36 * sf), 30))
            pb_text = "Enemy Defeated! Walking..."
            pb_surf = pb_font.render(pb_text, True, (255, 255, 255))
            _outlined(screen, pb_text, pb_font, color=(255, 255, 255), outline=(0, 0, 0),
                      pos=(sw // 2 - pb_surf.get_width() // 2, int(sh * 0.05)))

    elif active_screen == "question_wave":
        question_screen.draw()

    elif active_screen == "card_reward":
        def _ctr(text, fnt, color, y):
            s = fnt.render(text, True, color); screen.blit(s, (sw//2 - s.get_width()//2, y))
        tier = question_screen.logic.get_performance_tier()
        if tier == "poor":
            screen.fill((40, 10, 10))
            _ctr("DEBUFF APPLIED!", _font(int(48 * sf)), (255, 80, 80), int(sh * 0.23))
            debuff_y = int(sh * 0.35)
            line = int(38 * sf)
            _ctr(f"Enemy damage: x{game_state.damage_multiplier:.0f}", _font(int(28 * sf)), (255, 150, 150), debuff_y); debuff_y += line
            if game_state.blindness_chance > 0:
                _ctr(f"Blindness: {int(game_state.blindness_chance*100)}% miss chance", _font(int(28 * sf)), (255, 200, 100), debuff_y); debuff_y += line
            if game_state.confusion_chance > 0:
                _ctr(f"Confusion: {int(game_state.confusion_chance*100)}% skip chance", _font(int(28 * sf)), (200, 150, 255), debuff_y); debuff_y += line
            _ctr("Study harder next time!", _font(int(28 * sf)), (200, 200, 200), debuff_y + int(10 * sf))
        elif tier == "ok":
            screen.fill((20, 20, 40))
            _ctr("No benefits or debuffs.", _font(min(int(34 * sf), 28)), (200, 200, 200), int(sh * 0.40))
            _ctr("You didn't answer enough", _font(min(int(24 * sf), 20)), (150, 200, 150), int(sh * 0.50))
            _ctr("correctly to get a card.", _font(min(int(24 * sf), 20)), (150, 200, 150), int(sh * 0.56))
        else:
            picks_left = max_picks - cards_picked
            msg = f"Pick {picks_left} card{'s' if picks_left > 1 else ''}!"
            pick_surf = _font(int(48 * sf)).render(msg, True, (255, 255, 255))
            screen.blit(pick_surf, (sw // 2 - pick_surf.get_width() // 2, int(sh * 0.25)))
            hovered_reward_card = None
            hovered_reward_rect = None
            for i, card in enumerate(reward_cards):
                if i < len(reward_rects):
                    rect = reward_rects[i]
                    _draw_card(screen, card, rect, reward_mode=True)
                    if rect.collidepoint(pygame.mouse.get_pos()):
                        hovered_reward_card = card
                        hovered_reward_rect = rect
            if hovered_reward_card and hovered_reward_rect:
                _draw_hover_card_preview(screen, hovered_reward_card, hovered_reward_rect, reward_mode=True)

    elif active_screen == "revival_quiz":
        _draw_revival_quiz(screen)

    elif active_screen == "game_over":
        screen.fill((30, 0, 0))
        def _center(text, fnt, color, y):
            s = fnt.render(text, True, color); screen.blit(s, (sw//2 - s.get_width()//2, y))
        _center("GAME OVER", _font(int(48 * sf)), (255, 50, 50), int(sh * 0.33))
        _center("You were defeated...", _font(int(28 * sf)), (200, 200, 200), int(sh * 0.43))
        _center(f"Enemies defeated: {game_state.monsters_defeated}", _font(int(28 * sf)), (200, 200, 200), int(sh * 0.50))

    elif active_screen == "victory":
        screen.fill((0, 30, 0))
        def _center(text, fnt, color, y):
            s = fnt.render(text, True, color); screen.blit(s, (sw//2 - s.get_width()//2, y))
        _center("VICTORY!", _font(int(48 * sf)), (100, 255, 100), int(sh * 0.30))
        _center("You defeated all enemies!", _font(int(28 * sf)), (200, 255, 200), int(sh * 0.40))
        _center(f"All {game_state.monsters_defeated} enemies vanquished!", _font(int(28 * sf)), (200, 255, 200), int(sh * 0.47))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
