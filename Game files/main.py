import pygame

# Initialize pygame before font operations inside components
pygame.init()

from Frame.stage_manager import StageManager, Stage
from Frame.scroll_engine import ScrollEngine
from Frame.game_state import GameState
from Entities.player import Player
from Entities.enemies import Enemy
from question_wave.question_controller import QuestionScreen

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
battle_timer = 0
enemy = None

# Callback functions
def start_overworld():
    global active_screen, battle_timer, enemy
    active_screen = "overworld"
    scroll.start_scroll()
    battle_timer = pygame.time.get_ticks()

def start_battle():
    global active_screen, enemy
    active_screen = "battle"
    scroll.stop_scroll()
    enemy = Enemy("Slime", 50, 50, 10, x=600, y=300)

def show_card_select():
    global active_screen
    active_screen = "card_select"

def start_questions():
    global active_screen
    active_screen = "question_wave"
    question_screen.start()

def show_card_reward():
    global active_screen
    active_screen = "card_reward"

def show_game_over():
    global active_screen
    active_screen = "game_over"

def next_stage():
    # just loop back to overworld for now
    stage_manager.transition_to(Stage.OVERWORLD)

stage_manager.register(Stage.OVERWORLD,     start_overworld)
stage_manager.register(Stage.BATTLE,        start_battle)
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
            # Temp dev interactions: Press Space to skip states
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                if active_screen == "overworld":
                    stage_manager.transition_to(Stage.BATTLE)
                elif active_screen == "battle":
                    stage_manager.transition_to(Stage.CARD_SELECT)
                elif active_screen == "card_select":
                    stage_manager.transition_to(Stage.QUESTION_WAVE)
                elif active_screen == "card_reward":
                    stage_manager.transition_to(Stage.OVERWORLD)

    # Update
    scroll.update()
    stage_manager.check_conditions()

    if active_screen == "question_wave":
        question_screen.update()

    # Draw
    screen.fill((0, 0, 0))

    if active_screen in ["overworld", "battle"]:
        scroll.draw_background(screen)
        player.draw(screen)
        if active_screen == "battle" and enemy:
            enemy.draw(screen)
        
        # Draw instructions
        inst = pygame.font.SysFont(None, 24).render("Press SPACE to advance stage for testing", True, (255, 255, 255))
        screen.blit(inst, (10, 10))

        if active_screen == "overworld":
            text = font.render(f"Overworld (Walking)", True, (255, 255, 255))
            screen.blit(text, (250, 50))
        elif active_screen == "battle":
            text = font.render(f"Battle!", True, (255, 0, 0))
            screen.blit(text, (350, 50))

    elif active_screen == "card_select":
        text = font.render(f"Card Select (Press SPACE)", True, (255, 255, 255))
        screen.blit(text, (200, 200))

    elif active_screen == "question_wave":
        question_screen.draw()

    elif active_screen == "card_reward":
        text = font.render(f"Card Reward! (Press SPACE)", True, (100, 255, 100))
        screen.blit(text, (200, 200))

    elif active_screen == "game_over":
        text = font.render(f"GAME OVER", True, (255, 0, 0))
        screen.blit(text, (300, 250))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()