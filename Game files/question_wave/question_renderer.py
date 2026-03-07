import pygame

class QuestionRenderer:
    def __init__(self, screen):
        self.screen = screen
        self.font_large = pygame.font.SysFont(None, 48)
        self.font = pygame.font.SysFont(None, 36)
        self.font_small = pygame.font.SysFont(None, 24)

    def draw_background(self):
        self.screen.fill((30, 30, 60))

    def draw_question(self, question, index, total):
        # Draw Progress
        progress_text = self.font.render(f"Question {index + 1} / {total}", True, (200, 200, 200))
        self.screen.blit(progress_text, (20, 20))

        # Draw Question Text
        q_text = self.font_large.render(question["text"], True, (255, 255, 255))
        self.screen.blit(q_text, (50, 100))

    def draw_multiple_choice(self, choices):
        choice_rects = []
        y_offset = 200
        for i, choice in enumerate(choices):
            rect = pygame.Rect(50, y_offset, 600, 50)
            pygame.draw.rect(self.screen, (100, 100, 150), rect)
            pygame.draw.rect(self.screen, (200, 200, 255), rect, 2)
            
            c_text = self.font.render(f"{i + 1}. {choice}", True, (255, 255, 255))
            self.screen.blit(c_text, (70, y_offset + 10))
            
            choice_rects.append(rect)
            y_offset += 70
        return choice_rects

    def draw_free_response(self, current_input):
        pygame.draw.rect(self.screen, (255, 255, 255), (50, 200, 600, 50))
        input_text = self.font.render(current_input + ("_" if pygame.time.get_ticks() % 1000 < 500 else ""), True, (0, 0, 0))
        self.screen.blit(input_text, (60, 210))
        
        hint = self.font_small.render("Type your answer and press ENTER", True, (150, 150, 150))
        self.screen.blit(hint, (50, 260))

    def draw_score_summary(self, score_dict):
        text = self.font_large.render(f"Wave Complete! Score: {score_dict['correct']}/{score_dict['total']}", True, (255, 255, 255))
        self.screen.blit(text, (100, 200))

    def draw_damage_warning(self, multiplier):
        text = self.font.render(f"Failed! Enemies deal {multiplier}x damage next battle.", True, (255, 100, 100))
        self.screen.blit(text, (100, 300))
        
    def draw_reward_notification(self):
        text = self.font.render("Passed! You earned a new card.", True, (100, 255, 100))
        self.screen.blit(text, (100, 300))
