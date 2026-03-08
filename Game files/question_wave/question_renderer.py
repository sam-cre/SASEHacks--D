import pygame

class QuestionRenderer:
    def __init__(self, screen):
        self.screen = screen
        self.font_large = pygame.font.SysFont(None, 40)
        self.font = pygame.font.SysFont(None, 28)
        self.font_small = pygame.font.SysFont(None, 22)

    def draw_background(self):
        self.screen.fill((30, 30, 60))

    def draw_question(self, question, index, total):
        # Draw Progress
        progress_text = self.font.render(f"Question {index + 1} / {total}", True, (200, 200, 200))
        self.screen.blit(progress_text, (20, 20))

        # Draw Question Text with word wrap
        self._draw_wrapped_text(question["text"], self.font_large, (255, 255, 255), 50, 70, 700)

    def draw_multiple_choice(self, choices):
        choice_rects = []
        y_offset = 180
        for i, choice in enumerate(choices):
            # Calculate needed height based on text length
            wrapped_lines = self._wrap_text(f"{i + 1}. {choice}", self.font, 680)
            box_height = max(45, len(wrapped_lines) * 25 + 20)

            rect = pygame.Rect(50, y_offset, 700, box_height)

            # Hover effect
            mouse_pos = pygame.mouse.get_pos()
            hover = rect.collidepoint(mouse_pos)
            bg_color = (80, 80, 140) if hover else (60, 60, 110)
            border_color = (200, 200, 255) if hover else (140, 140, 200)

            pygame.draw.rect(self.screen, bg_color, rect, border_radius=6)
            pygame.draw.rect(self.screen, border_color, rect, 2, border_radius=6)

            # Draw wrapped choice text
            text_y = y_offset + 10
            for line in wrapped_lines:
                line_surf = self.font.render(line, True, (255, 255, 255))
                self.screen.blit(line_surf, (70, text_y))
                text_y += 25

            choice_rects.append(rect)
            y_offset += box_height + 10
        return choice_rects

    def draw_score_summary(self, score_dict):
        correct = score_dict['correct']
        total = score_dict['total']

        # Big score
        text = self.font_large.render(f"Quiz Complete!  {correct}/{total}", True, (255, 255, 255))
        self.screen.blit(text, (200, 160))

        # Performance tier message
        ratio = correct / total if total > 0 else 0
        if ratio >= 1.0:
            msg = "PERFECT! You earned access to Rare cards!"
            color = (255, 215, 0)
        elif ratio >= 0.66:
            msg = "Great job! You earned a card reward!"
            color = (100, 255, 100)
        elif ratio >= 0.33:
            msg = "Okay. Common cards only this time."
            color = (255, 200, 100)
        else:
            msg = "Poor performance. No card reward."
            color = (255, 100, 100)

        tier_text = self.font.render(msg, True, color)
        self.screen.blit(tier_text, (150, 220))

    def draw_damage_warning(self, multiplier):
        text = self.font.render(f"Enemies deal {multiplier}x damage next battle.", True, (255, 100, 100))
        self.screen.blit(text, (150, 280))

    def draw_reward_notification(self):
        text = self.font.render("Pick a card to add to your deck!", True, (100, 255, 100))
        self.screen.blit(text, (200, 280))

    # ── Text wrapping helpers ──

    def _wrap_text(self, text, font, max_width):
        """Word-wrap text to fit within max_width pixels."""
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

    def _draw_wrapped_text(self, text, font, color, x, y, max_width):
        """Draw word-wrapped text on screen."""
        lines = self._wrap_text(text, font, max_width)
        for line in lines:
            surf = font.render(line, True, color)
            self.screen.blit(surf, (x, y))
            y += font.get_height() + 4
