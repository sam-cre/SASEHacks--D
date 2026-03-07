from question_wave.question_logic import QuestionLogic
from question_wave.question_renderer import QuestionRenderer
from question_wave.question_events import QuestionEvents
from question_wave.question_generator import QuestionGenerator

from Frame.stage_manager import Stage

class QuestionScreen:
    def __init__(self, screen, game_state, stage_manager):
        self.screen = screen
        self.game_state = game_state
        self.stage_manager = stage_manager

        self.generator = QuestionGenerator()
        self.logic = QuestionLogic(game_state)
        self.renderer = QuestionRenderer(screen)    # ← your UI slot
        self.events = QuestionEvents()

        self.current_input = ""     # tracks free response typing
        self.answer_submitted = False
        self.show_summary = False

    def start(self):
        """Called automatically when QUESTION_WAVE stage is entered"""
        questions = self.generator.generate_wave()
        self.logic.load_wave(questions)

    def handle_event(self, event):
        question = self.logic.current_question()
        if not question or self.show_summary:
            return

        if question["type"] == "multiple_choice":
            chosen = self.events.check_choice_click(event, self.choice_rects)
            if chosen is not None:
                correct = self.logic.submit_answer(chosen)
                self.check_wave_complete()

        elif question["type"] == "free_response":
            typed, submitted = self.events.handle_typing(event, self.current_input)
            self.current_input = typed
            if submitted:
                correct = self.logic.submit_answer(self.current_input)
                self.current_input = ""
                self.check_wave_complete()

    def check_wave_complete(self):
        if self.logic.wave_complete:
            self.show_summary = True

    def update(self):
        """Called every frame — auto transitions after summary"""
        if self.show_summary and self.logic.result:
            if self.logic.result == "pass":
                self.stage_manager.transition_to(Stage.CARD_REWARD)
            else:
                self.stage_manager.transition_to(Stage.NEXT_STAGE)

    def draw(self):
        self.renderer.draw_background()
        question = self.logic.current_question()

        if self.show_summary:
            self.renderer.draw_score_summary(self.logic.get_score())
            if self.logic.result == "fail":
                self.renderer.draw_damage_warning(self.game_state.damage_multiplier)
            else:
                self.renderer.draw_reward_notification()
            return

        if question:
            self.renderer.draw_question(question, self.logic.current_index, len(self.logic.questions))

            if question["type"] == "multiple_choice":
                self.choice_rects = self.renderer.draw_multiple_choice(question["choices"])

            elif question["type"] == "free_response":
                self.renderer.draw_free_response(self.current_input)