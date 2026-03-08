"""
Question generator that loads real flashcard data from JSON decks.
MC-only — 3 random questions per wave. No free response.
"""
import json
import os
import random

class QuestionGenerator:
    def __init__(self, deck_path=None):
        self.deck_path = deck_path
        self.flashcards = []
        if deck_path:
            self.load_deck(deck_path)

    def load_deck(self, deck_path):
        """Load flashcards from a JSON file."""
        self.deck_path = deck_path
        self.flashcards = []
        try:
            with open(deck_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self.flashcards = data
        except Exception as e:
            print(f"[QuestionGenerator] Failed to load deck: {e}")
            self.flashcards = []

    def generate_wave(self, count=3):
        """
        Generate a wave of 3 random MC questions from the loaded deck.
        Falls back to dummy questions if no deck is loaded.
        """
        if not self.flashcards or len(self.flashcards) < 4:
            return self._dummy_wave()

        pool = self.flashcards.copy()
        random.shuffle(pool)
        selected = pool[:count]

        questions = []
        for card in selected:
            term = card.get("term", "")
            answer = card.get("answer", "")
            if not term or not answer:
                continue
            q = self._make_mc(term, answer)
            questions.append(q)

        return questions if questions else self._dummy_wave()

    def _make_mc(self, term, correct_answer):
        """Create a multiple choice question using other terms as distractors."""
        wrong_pool = [fc.get("answer", "") for fc in self.flashcards
                      if fc.get("answer", "") != correct_answer and fc.get("answer", "")]
        random.shuffle(wrong_pool)
        distractors = wrong_pool[:3]

        while len(distractors) < 3:
            distractors.append(f"Not {correct_answer[:30]}")

        choices = [correct_answer] + distractors
        random.shuffle(choices)
        correct_idx = choices.index(correct_answer)

        return {
            "type": "multiple_choice",
            "text": f"What is: {term}?",
            "choices": choices,
            "correct_idx": correct_idx,
            "term": term,
            "correct_answer": correct_answer,
        }

    def _dummy_wave(self):
        """Fallback dummy questions if no deck loaded."""
        return [
            {
                "type": "multiple_choice",
                "text": "What is 2 + 2?",
                "choices": ["3", "4", "5", "22"],
                "correct_idx": 1,
                "term": "2 + 2",
                "correct_answer": "4",
            },
            {
                "type": "multiple_choice",
                "text": "What color is the sky?",
                "choices": ["Red", "Green", "Blue", "Yellow"],
                "correct_idx": 2,
                "term": "sky color",
                "correct_answer": "Blue",
            },
            {
                "type": "multiple_choice",
                "text": "Which planet is closest to the sun?",
                "choices": ["Venus", "Earth", "Mercury", "Mars"],
                "correct_idx": 2,
                "term": "closest planet to sun",
                "correct_answer": "Mercury",
            },
        ]
