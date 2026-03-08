import pygame

# Initialize pygame before font operations inside components
pygame.init()

from Frame.stage_manager import StageManager, Stage
from Frame.scroll_engine import ScrollEngine
from Frame.game_state import GameState
from Entities.player import Player
from Entities.enemies import Enemy
from Cards.Cards import Card
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

# Fonts for temporary UI
font = pygame.font.SysFont(None, 48)

# Dummy state vars for placeholder screens
active_screen = "overworld"
overworld_timer = 0
overworld_duration = 3000
reward_timer = 0
reward_duration = 2000
battle_timer = 0
walk_timer = 0
walk_duration = 2000 # 2 seconds of walking
enemy = None
drawn_cards = []
card_rects = []
reward_cards = []
reward_rects = []
cards_picked = 0

# Callback functions
def start_overworld():
    global active_screen, battle_timer, enemy, overworld_timer
    active_screen = "overworld"
    scroll.start_scroll()
    battle_timer = pygame.time.get_ticks()
    overworld_timer = pygame.time.get_ticks()

def start_battle():
    global active_screen, enemy, drawn_cards, card_rects
    active_screen = "battle"
    scroll.stop_scroll()
    enemy = Enemy("Slime", 100, 100, 10, x=600, y=300)
    
    # Draw up to 3 cards from deck
    deck_copy = game_state.cards_in_deck.copy()
    random.shuffle(deck_copy)
    drawn_cards = deck_copy[:3]
    
    # Calculate rects for drawing and clicking
    card_rects = []
    start_x = 150
    for i in range(len(drawn_cards)):
        rect = pygame.Rect(start_x + (i * 160), 450, 140, 120)
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
    question_screen.start()

def show_card_reward():
    global active_screen, reward_timer, reward_cards, reward_rects, cards_picked
    active_screen = "card_reward"
    reward_timer = pygame.time.get_ticks()
    cards_picked = 0
    
    # Generate 3 random cards
    reward_cards = [
        Card("Slash", 15, 20, "Strong attack"),
        Card("Fireball", 20, 25, "Magic attack"),
        Card("Quick Hit", 5, 25, "Unpredictable")
    ]
    random.shuffle(reward_cards)
    
    reward_rects = []
    start_x = 150
    for i in range(len(reward_cards)):
        rect = pygame.Rect(start_x + (i * 160), 250, 140, 120)
        reward_rects.append(rect)

def show_game_over():
    global active_screen
    active_screen = "game_over"

def next_stage():
    # just loop back to overworld for now
    stage_manager.transition_to(Stage.OVERWORLD)

stage_manager.register(Stage.OVERWORLD,     start_overworld)
stage_manager.register(Stage.BATTLE,        start_battle)
stage_manager.register(Stage.POST_BATTLE_WALK, start_post_battle_walk)
stage_manager.register(Stage.CARD_SELECT,   show_card_select)
stage_manager.register(Stage.QUESTION_WAVE, start_questions)
stage_manager.register(Stage.CARD_REWARD,   show_card_reward)
stage_manager.register(Stage.GAME_OVER,     show_game_over)
stage_manager.register(Stage.NEXT_STAGE,    next_stage)

# Initialization
stage_manager.transition_to(Stage.OVERWORLD)
stage_manager.check_conditions()

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if active_screen == "question_wave":
            question_screen.handle_event(event)
        else:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Battle card clicks
                if active_screen == "battle" and enemy and enemy.is_alive():
                    for i, rect in enumerate(card_rects):
                        if rect.collidepoint(event.pos):
                            card = drawn_cards[i]
                            damage = card.roll_damage()
                            enemy.take_damage(damage)
                            
                            drawn_cards.pop(i)
                            deck_copy = game_state.cards_in_deck.copy()
                            random.shuffle(deck_copy)
                            for c in deck_copy:
                                if c not in drawn_cards:
                                    drawn_cards.insert(i, c)
                                    break
                            break

                # Reward card clicks
                elif active_screen == "card_reward":
                    # Only allow clicks if they actually passed the wave
                    if question_screen.logic.result == "pass":
                        for i, rect in enumerate(reward_rects):
                            if rect.collidepoint(event.pos):
                                card = reward_cards[i]
                                # Add chosen card to deck
                                game_state.cards_in_deck.append(card)
                                cards_picked += 1
                                
                                # Remove clicked card from screen
                                reward_cards.pop(i)
                                reward_rects.pop(i)
                                
                                # Check if they picked 2 yet
                                if cards_picked >= 2:
                                    stage_manager.transition_to(Stage.GAME_OVER)
                                break

    # Update
    scroll.update()
    stage_manager.check_conditions()

    if active_screen == "question_wave":
        question_screen.update()
        
    if active_screen == "overworld":
        if pygame.time.get_ticks() - overworld_timer > overworld_duration:
            stage_manager.transition_to(Stage.BATTLE)
            
    if active_screen == "battle":
        if enemy and not enemy.is_alive():
            stage_manager.transition_to(Stage.POST_BATTLE_WALK)
            enemy = None # clear enemy to prevent double triggering
            
    if active_screen == "post_battle_walk":
        if pygame.time.get_ticks() - walk_timer > walk_duration:
            stage_manager.transition_to(Stage.QUESTION_WAVE)
            
    if active_screen == "card_reward":
        # If they failed, just use standard timer to skip reward screen
        if question_screen.logic.result == "fail":
            if pygame.time.get_ticks() - reward_timer > reward_duration:
                stage_manager.transition_to(Stage.GAME_OVER)

    # Draw
    screen.fill((0, 0, 0))

    if active_screen in ["overworld", "battle", "post_battle_walk"]:
        scroll.draw_background(screen)
        player.draw(screen)
        if active_screen == "battle" and enemy:
            enemy.draw(screen)
        

        if active_screen == "overworld":
            text = font.render(f"Overworld (Walking)", True, (255, 255, 255))
            screen.blit(text, (250, 50))
        elif active_screen == "battle":
            text = font.render(f"Battle! (Select a Card)", True, (255, 0, 0))
            screen.blit(text, (200, 50))
            
            # Draw Cards
            for i, card in enumerate(drawn_cards):
                rect = card_rects[i]
                pygame.draw.rect(screen, (200, 200, 200), rect)
                pygame.draw.rect(screen, (255, 255, 255), rect, 3)
                
                # Card Name
                name_text = pygame.font.SysFont(None, 24).render(card.name, True, (0, 0, 0))
                screen.blit(name_text, (rect.x + 10, rect.y + 10))
                
                # Card Dmg
                dmg_text = pygame.font.SysFont(None, 20).render(f"Dmg: {card.damage_min}-{card.damage_max}", True, (200, 0, 0))
                screen.blit(dmg_text, (rect.x + 10, rect.y + 50))
                
        elif active_screen == "post_battle_walk":
            text = font.render(f"Enemy Defeated! Walking...", True, (100, 255, 100))
            screen.blit(text, (200, 50))

    elif active_screen == "card_select":
        text = font.render(f"Card Select (Press SPACE)", True, (255, 255, 255))
        screen.blit(text, (200, 200))

    elif active_screen == "question_wave":
        question_screen.draw()

    elif active_screen == "card_reward":
        if question_screen.logic.result == "pass":
            text = font.render(f"Pick 2 Cards to Add to Your Deck!", True, (100, 255, 100))
            screen.blit(text, (150, 150))
            
            # Draw Reward Cards
            for i, card in enumerate(reward_cards):
                rect = reward_rects[i]
                pygame.draw.rect(screen, (50, 150, 50), rect)
                pygame.draw.rect(screen, (255, 255, 255), rect, 3)
                
                # Card Name
                name_text = pygame.font.SysFont(None, 24).render(card.name, True, (255, 255, 255))
                screen.blit(name_text, (rect.x + 10, rect.y + 10))
                
                # Card Dmg
                dmg_text = pygame.font.SysFont(None, 20).render(f"Dmg: {card.damage_min}-{card.damage_max}", True, (200, 255, 200))
                screen.blit(dmg_text, (rect.x + 10, rect.y + 50))
        else:
            # Failed wave, no reward
            text = font.render(f"No rewards this time...", True, (255, 100, 100))
            screen.blit(text, (200, 200))

    elif active_screen == "game_over":
        text = font.render(f"DONE", True, (0, 255, 0))
        screen.blit(text, (350, 200))
        sub_text = pygame.font.SysFont(None, 32).render(f"(Baseplate for future end screen)", True, (200, 200, 200))
        screen.blit(sub_text, (200, 260))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()