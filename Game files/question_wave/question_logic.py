class QuestionLogic:
    def __init__(self, game_state):
        self.game_state = game_state
        self.questions = []
        self.current_index = 0
        self.score = 0
        self.wave_complete = False
        self.result = None          # "great", "ok", "poor"
        self.wrong_questions = []   # track wrong answers for revival

    def load_wave(self, questions):
        self.questions = questions
        self.current_index = 0
        self.score = 0
        self.wave_complete = False
        self.result = None
        self.wrong_questions = []

    def current_question(self):
        if self.current_index < len(self.questions):
            return self.questions[self.current_index]
        return None

    def submit_answer(self, answer):
        question = self.current_question()
        if not question:
            return False

        correct = False
        if question["type"] == "multiple_choice":
            if answer == question["correct_idx"]:
                correct = True

        if correct:
            self.score += 1
        else:
            # Track wrong question for revival system
            self.wrong_questions.append(question)
            # Also add to global wrong list on game_state
            if hasattr(self.game_state, 'all_wrong_questions'):
                self.game_state.all_wrong_questions.append(question)

        self.current_index += 1

        if self.current_index >= len(self.questions):
            self.complete_wave()

        return correct

    def complete_wave(self):
        self.wave_complete = True
        total = len(self.questions) if self.questions else 1
        ratio = self.score / total

        # Performance tiers for card rewards
        if ratio >= 1.0:
            self.result = "perfect"   # 3/3 → best cards
        elif ratio >= 0.66:
            self.result = "great"     # 2/3 → good cards
        elif ratio >= 0.33:
            self.result = "ok"        # 1/3 → common cards only
        else:
            self.result = "poor"      # 0/3 → no reward, just continue

        # Reset damage multiplier based on performance
        if ratio >= 0.66:
            self.game_state.damage_multiplier = 1.0
        else:
            self.game_state.damage_multiplier = 1.5

    def get_score(self):
        return {"correct": self.score, "total": len(self.questions)}

    def get_performance_tier(self):
        """Returns the performance tier string for the reward system."""
        return self.result or "poor"