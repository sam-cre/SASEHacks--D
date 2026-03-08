import pygame
import os
import sys

# Initialize pygame before font operations inside components
pygame.init()

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

screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("SASEHacks Game")
clock = pygame.time.Clock()

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

# Fonts for temporary UI
font = pygame.font.SysFont(None, 48)
small_font = pygame.font.SysFont(None, 28)
tiny_font = pygame.font.SysFont(None, 22)

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
    global active_screen, battle_timer, overworld_timer
    active_screen = "overworld"
    scroll.start_scroll()
    battle_timer = pygame.time.get_ticks()
    overworld_timer = pygame.time.get_ticks()

def start_battle():
    global active_screen, enemy, drawn_cards, card_rects, battle_logic
    active_screen = "battle"
    scroll.stop_scroll()

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

def _recalc_card_rects():
    global card_rects
    card_rects = []
    total = len(drawn_cards)
    card_w, card_h = 140, 120
    gap = 10
    total_w = total * card_w + (total - 1) * gap
    start_x = (800 - total_w) // 2
    for i in range(total):
        rect = pygame.Rect(start_x + i * (card_w + gap), 370, card_w, card_h)
        card_rects.append(rect)

def start_post_battle_walk():
    global active_screen, walk_timer
    active_screen = "post_battle_walk"
    scroll.start_scroll()
    walk_timer = pygame.time.get_ticks()

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
    active_screen = "card_reward"
    reward_timer = pygame.time.get_ticks()
    cards_picked = 0

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
    card_w, card_h = 140, 120
    gap = 10
    total_w = max(1, len(reward_cards)) * card_w + max(0, len(reward_cards) - 1) * gap
    start_x = (800 - total_w) // 2
    for i in range(len(reward_cards)):
        rect = pygame.Rect(start_x + i * (card_w + gap), 250, card_w, card_h)
        reward_rects.append(rect)

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


# ─────────────────────────────────────────────
#  DRAWING HELPERS
# ─────────────────────────────────────────────

def _draw_player_hud(screen):
    hp_ratio = max(0, player.hp / player.max_hp)
    bar_x, bar_y = 20, 20
    bar_w, bar_h = 200, 18
    pygame.draw.rect(screen, (80, 0, 0), (bar_x, bar_y, bar_w, bar_h))
    if hp_ratio > 0.5:
        bar_color = (0, 200, 0)
    elif hp_ratio > 0.25:
        bar_color = (255, 200, 0)
    else:
        bar_color = (255, 50, 50)
    pygame.draw.rect(screen, bar_color, (bar_x, bar_y, bar_w * hp_ratio, bar_h))
    pygame.draw.rect(screen, (255, 255, 255), (bar_x, bar_y, bar_w, bar_h), 2)
    hp_font = pygame.font.SysFont(None, 22)
    hp_text = hp_font.render(f"HP: {player.hp}/{player.max_hp}", True, (255, 255, 255))
    screen.blit(hp_text, (bar_x + 5, bar_y + 1))

    # Revival indicator
    if game_state.revival_available and not game_state.has_revived:
        rev_text = tiny_font.render("♥ Revival available", True, (100, 255, 200))
        screen.blit(rev_text, (bar_x, bar_y + 22))
    elif game_state.has_revived:
        rev_text = tiny_font.render("♥ Revival used", True, (150, 150, 150))
        screen.blit(rev_text, (bar_x, bar_y + 22))


def _draw_card(screen, card, rect, reward_mode=False):
    if card.rarity == "super_rare":
        bg_color = (150, 50, 200)
    elif card.rarity == "rare":
        bg_color = (180, 140, 50)
    elif card.rarity == "starter":
        bg_color = (120, 120, 180)
    else:
        bg_color = (200, 200, 200) if not reward_mode else (50, 150, 50)

    pygame.draw.rect(screen, bg_color, rect)
    pygame.draw.rect(screen, (255, 255, 255), rect, 3)

    name_text = pygame.font.SysFont(None, 22).render(card.name, True, (0, 0, 0) if not reward_mode else (255, 255, 255))
    screen.blit(name_text, (rect.x + 5, rect.y + 5))

    type_color = (80, 80, 80) if not reward_mode else (200, 200, 200)
    type_text = pygame.font.SysFont(None, 18).render(f"[{card.attack_type}]", True, type_color)
    screen.blit(type_text, (rect.x + 5, rect.y + 25))

    if card.damage_min == card.damage_max:
        dmg_str = f"Dmg: {card.damage_min}"
    elif card.damage_max == 0:
        dmg_str = "No damage"
    else:
        dmg_str = f"Dmg: {card.damage_min}-{card.damage_max}"
    dmg_color = (200, 0, 0) if not reward_mode else (200, 255, 200)
    dmg_text = pygame.font.SysFont(None, 18).render(dmg_str, True, dmg_color)
    screen.blit(dmg_text, (rect.x + 5, rect.y + 45))

    if card.effect:
        eff_color = (0, 100, 200) if not reward_mode else (100, 200, 255)
        eff_text = pygame.font.SysFont(None, 18).render(f"FX: {card.effect}", True, eff_color)
        screen.blit(eff_text, (rect.x + 5, rect.y + 65))

    if card.permanent:
        perm_text = pygame.font.SysFont(None, 16).render("PERM", True, (255, 255, 255))
        screen.blit(perm_text, (rect.x + 100, rect.y + 100))

    if reward_mode:
        if card.rarity == "super_rare":
            badge = pygame.font.SysFont(None, 16).render("SUPER RARE", True, (255, 100, 255))
            screen.blit(badge, (rect.x + 5, rect.y + 100))
        elif card.rarity == "rare":
            rare_text = pygame.font.SysFont(None, 16).render("RARE", True, (255, 215, 0))
            screen.blit(rare_text, (rect.x + 100, rect.y + 100))


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
    screen.fill((40, 10, 10))

    # Title
    title = font.render("REVIVAL QUIZ", True, (255, 200, 100))
    screen.blit(title, (270, 20))

    if revival_show_result:
        # Show result
        total = len(revival_questions) if revival_questions else 1
        ratio = revival_score / total
        score_text = font.render(f"Score: {revival_score}/{total}", True, (255, 255, 255))
        screen.blit(score_text, (300, 200))

        if ratio >= 0.7:
            msg = "You passed! You've been REVIVED!"
            color = (100, 255, 100)
        else:
            msg = "You failed... Game Over."
            color = (255, 100, 100)
        result_surf = small_font.render(msg, True, color)
        screen.blit(result_surf, (230, 260))
        return

    if revival_index >= len(revival_questions):
        return

    q = revival_questions[revival_index]

    # Info bar
    info = small_font.render(
        f"Answer the questions you got wrong! ({revival_index+1}/{len(revival_questions)})  Need 70% to revive!",
        True, (200, 200, 200)
    )
    screen.blit(info, (50, 60))

    # Question text (wrapped)
    q_lines = _wrap_text(q["text"], small_font, 700)
    q_y = 100
    for line in q_lines:
        surf = small_font.render(line, True, (255, 255, 255))
        screen.blit(surf, (50, q_y))
        q_y += 28

    # Choices
    revival_choice_rects = []
    y_offset = max(180, q_y + 20)
    mc_font = pygame.font.SysFont(None, 24)
    for i, choice in enumerate(q.get("choices", [])):
        wrapped = _wrap_text(f"{i+1}. {choice}", mc_font, 680)
        box_h = max(40, len(wrapped) * 24 + 16)
        rect = pygame.Rect(50, y_offset, 700, box_h)

        mouse_pos = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse_pos)
        bg = (80, 40, 40) if hover else (60, 30, 30)
        border = (255, 200, 100) if hover else (150, 100, 60)

        pygame.draw.rect(screen, bg, rect, border_radius=6)
        pygame.draw.rect(screen, border, rect, 2, border_radius=6)

        text_y = y_offset + 8
        for line in wrapped:
            surf = mc_font.render(line, True, (255, 255, 255))
            screen.blit(surf, (70, text_y))
            text_y += 24

        revival_choice_rects.append(rect)
        y_offset += box_h + 8


# ─────────────────────────────────────────────
#  MAIN GAME LOOP
# ─────────────────────────────────────────────

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

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
                if revival_show_result:
                    # Click to proceed after result
                    total = len(revival_questions) if revival_questions else 1
                    ratio = revival_score / total
                    if ratio >= 0.7:
                        # Revive! Restore player to full HP and re-enter battle
                        player.hp = player.max_hp
                        game_state.has_revived = True
                        game_state.revival_available = False
                        game_state.all_wrong_questions = []
                        game_state.reset_battle_effects()
                        msg_queue.push_info("You've been revived with full HP! Fight on!")
                        stage_manager.transition_to(Stage.BATTLE)
                    else:
                        stage_manager.transition_to(Stage.GAME_OVER)
                else:
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
                            if cards_picked >= max_picks:
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

    if active_screen == "overworld":
        if pygame.time.get_ticks() - overworld_timer > overworld_duration:
            stage_manager.transition_to(Stage.BATTLE)

    if active_screen == "battle":
        if not msg_queue.is_busy():
            if enemy_turn_pending:
                enemy_turn_pending = False
                _do_enemy_turn()
            elif enemy and not enemy.is_alive():
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
        tier = question_screen.logic.get_performance_tier()
        if tier == "poor" or not reward_cards:
            # No cards to pick — auto-advance after brief delay
            delay = 3500 if tier == "poor" else 2000
            if pygame.time.get_ticks() - reward_timer > delay:
                stage_manager.transition_to(Stage.NEXT_STAGE)

    # ─────────────────────────────────────────
    #  DRAW
    # ─────────────────────────────────────────
    screen.fill((0, 0, 0))

    if active_screen == "deck_select":
        deck_selector.draw()

    elif active_screen in ["overworld", "battle", "post_battle_walk"]:
        scroll.draw_background(screen)
        player.draw(screen)
        if active_screen == "battle" and enemy:
            enemy.draw(screen)

        _draw_player_hud(screen)

        if active_screen == "overworld":
            text = font.render("Overworld (Walking)", True, (255, 255, 255))
            screen.blit(text, (250, 50))
            template = game_state.get_next_enemy_template()
            if template:
                preview = small_font.render(f"Next: {template['name']} ({template['tier'].upper()})", True, (200, 200, 100))
                screen.blit(preview, (280, 90))

        elif active_screen == "battle":
            if enemy:
                tier_colors = {"easy": (100, 255, 100), "medium": (255, 200, 50), "hard": (255, 80, 80), "boss": (200, 100, 255)}
                tier_col = tier_colors.get(enemy.tier, (255, 255, 255))
                text = font.render(f"VS {enemy.name}", True, tier_col)
                screen.blit(text, (300, 20))
                tier_label = small_font.render(f"[{enemy.tier.upper()}]", True, tier_col)
                screen.blit(tier_label, (350, 55))

            if not msg_queue.is_busy():
                if game_state.player_skip_turns > 0:
                    skip_text = small_font.render(f"STUNNED! ({game_state.player_skip_turns} turn(s) left) - Click to skip turn", True, (255, 100, 100))
                    screen.blit(skip_text, (200, 350))
                else:
                    for i, card in enumerate(drawn_cards):
                        if i < len(card_rects):
                            _draw_card(screen, card, card_rects[i])

            msg_queue.draw(screen)

        elif active_screen == "post_battle_walk":
            text = font.render("Enemy Defeated! Walking...", True, (100, 255, 100))
            screen.blit(text, (200, 50))

    elif active_screen == "question_wave":
        question_screen.draw()

    elif active_screen == "card_reward":
        tier = question_screen.logic.get_performance_tier()
        if tier == "poor":
            screen.fill((40, 10, 10))
            text = font.render("DEBUFF APPLIED!", True, (255, 80, 80))
            screen.blit(text, (260, 140))
            # Show active debuffs
            debuff_y = 200
            dmg_text = small_font.render(f"Enemy damage: x{game_state.damage_multiplier:.0f}", True, (255, 150, 150))
            screen.blit(dmg_text, (270, debuff_y))
            debuff_y += 35
            if game_state.blindness_chance > 0:
                blind_text = small_font.render(f"Blindness: {int(game_state.blindness_chance*100)}% miss chance", True, (255, 200, 100))
                screen.blit(blind_text, (250, debuff_y))
                debuff_y += 35
            if game_state.confusion_chance > 0:
                conf_text = small_font.render(f"Confusion: {int(game_state.confusion_chance*100)}% skip chance", True, (200, 150, 255))
                screen.blit(conf_text, (250, debuff_y))
                debuff_y += 35
            sub = small_font.render("Study harder next time!", True, (200, 200, 200))
            screen.blit(sub, (280, debuff_y + 10))
        elif tier == "ok":
            screen.fill((20, 20, 40))
            text = font.render("No benefits or debuffs.", True, (200, 200, 200))
            screen.blit(text, (220, 240))
            sub = small_font.render("You didn't answer enough correctly to get a card.", True, (150, 200, 150))
            screen.blit(sub, (160, 290))
        else:
            picks_left = max_picks - cards_picked
            msg = f"Pick {picks_left} card{'s' if picks_left > 1 else ''}!"
            text = font.render(msg, True, (255, 255, 255))
            screen.blit(text, (150, 150))

            for i, card in enumerate(reward_cards):
                if i < len(reward_rects):
                    _draw_card(screen, card, reward_rects[i], reward_mode=True)

    elif active_screen == "revival_quiz":
        _draw_revival_quiz(screen)

    elif active_screen == "game_over":
        screen.fill((30, 0, 0))
        text = font.render("GAME OVER", True, (255, 50, 50))
        screen.blit(text, (300, 200))
        sub_text = small_font.render("You were defeated...", True, (200, 200, 200))
        screen.blit(sub_text, (310, 260))
        enemies_text = small_font.render(f"Enemies defeated: {game_state.monsters_defeated}", True, (200, 200, 200))
        screen.blit(enemies_text, (290, 300))

    elif active_screen == "victory":
        screen.fill((0, 30, 0))
        text = font.render("VICTORY!", True, (100, 255, 100))
        screen.blit(text, (310, 180))
        sub_text = small_font.render("You defeated all enemies!", True, (200, 255, 200))
        screen.blit(sub_text, (280, 240))
        enemies_text = small_font.render(f"All {game_state.monsters_defeated} enemies vanquished!", True, (200, 255, 200))
        screen.blit(enemies_text, (260, 280))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()