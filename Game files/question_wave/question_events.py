import pygame

class QuestionEvents:
    def check_choice_click(self, event, choice_rects):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(choice_rects):
                if rect.collidepoint(event.pos):
                    return i
        return None

    def handle_typing(self, event, current_input):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                return current_input, True
            elif event.key == pygame.K_BACKSPACE:
                return current_input[:-1], False
            else:
                return current_input + event.unicode, False
        return current_input, False
