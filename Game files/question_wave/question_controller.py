from question_wave.question_logic import QuestionLogic
from question_wave.question_renderer import QuestionRenderer
from question_wave.question_events import QuestionEvents
from question_wave.question_generator import QuestionGenerator

from Frame.stage_manager import Stage
import pygame

class QuestionScreen:
    def __init__(self, screen, game_state, stage_manager):
        self.screen = screen
        self.game_state = game_state
        self.stage_manager = stage_manager

        self.generator = QuestionGenerator()
        self.logic = QuestionLogic(game_state)
        self.renderer = QuestionRenderer(screen)
        self.events = QuestionEvents()

        self.show_summary = False
        self.summary_timer = 0
        self.summary_duration = 3000
        self.choice_rects = []

    def start(self):
        """Called automatically when QUESTION_WAVE stage is entered"""
        self.show_summary = False
        self.choice_rects = []
        questions = self.generator.generate_wave(count=3)
        self.logic.load_wave(questions)

    def handle_event(self, event):
        question = self.logic.current_question()
        if not question or self.show_summary:
            return

        # MC only — check for clicks
        if question["type"] == "multiple_choice":
            chosen = self.events.check_choice_click(event, self.choice_rects)
            if chosen is not None:
                correct = self.logic.submit_answer(chosen)
                self.check_wave_complete()

    def check_wave_complete(self):
        if self.logic.wave_complete:
            self.show_summary = True
            self.summary_timer = pygame.time.get_ticks()

    def update(self):
        """Called every frame — auto transitions after summary"""
        if self.show_summary and self.logic.result:
            tier = self.logic.get_performance_tier()
            # For poor tier only, skip the summary screen and go straight to reward
            if tier == "poor":
                self.stage_manager.transition_to(Stage.CARD_REWARD)
                return
            if pygame.time.get_ticks() - self.summary_timer > self.summary_duration:
                self.stage_manager.transition_to(Stage.CARD_REWARD)

    def draw(self):
        self.renderer.draw_background()
        question = self.logic.current_question()

        if self.show_summary:
            self.renderer.draw_score_summary(self.logic.get_score())
            # Show performance tier message (already handled in renderer)
            return

        if question:
            self.renderer.draw_question(question, self.logic.current_index, len(self.logic.questions))

            if question["type"] == "multiple_choice":
                self.choice_rects = self.renderer.draw_multiple_choice(question["choices"])