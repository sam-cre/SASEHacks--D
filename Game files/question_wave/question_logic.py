class QuestionLogic:
    def __init__(self, game_state):
        self.game_state = game_state
        self.questions = []
        self.current_index = 0
        self.score = 0
        self.wave_complete = False
        self.result = None

    def load_wave(self, questions):
        self.questions = questions
        self.current_index = 0
        self.score = 0
        self.wave_complete = False
        self.result = None

    def current_question(self):
        if self.current_index < len(self.questions):
            return self.questions[self.current_index]
        return None

    def submit_answer(self, answer):
        question = self.current_question()
        if not question:
            return False

        # In multiple choice, answer is the index of the choice
        # In free response, answer is the string
        correct = False
        if question["type"] == "multiple_choice":
            if answer == question["correct_idx"]:
                correct = True
        elif question["type"] == "free_response":
            if str(answer).strip().lower() == str(question["correct_answer"]).strip().lower():
                correct = True

        if correct:
            self.score += 1
            
        self.current_index += 1
        
        if self.current_index >= len(self.questions):
            self.complete_wave()
            
        return correct

    def complete_wave(self):
        self.wave_complete = True
        # Check pass/fail (e.g., 50% required)
        pass_ratio = self.score / len(self.questions) if self.questions else 0
        if pass_ratio >= 0.5:
            self.result = "pass"
            self.game_state.damage_multiplier = 1.0
        else:
            self.result = "fail"
            # Increase damage multiplier for failed question wave
            self.game_state.damage_multiplier = 2.0

    def get_score(self):
        return {"correct": self.score, "total": len(self.questions)}