class QuestionGenerator:
    def generate_wave(self):
        return [
            {
                "type": "multiple_choice",
                "text": "What is 2 + 2?",
                "choices": ["3", "4", "5", "22"],
                "correct_idx": 1
            },
            {
                "type": "free_response",
                "text": "Type 'hello'",
                "correct_answer": "hello"
            },
            {
                "type": "multiple_choice",
                "text": "What color is the sky?",
                "choices": ["Red", "Green", "Blue", "Yellow"],
                "correct_idx": 2
            }
        ]
