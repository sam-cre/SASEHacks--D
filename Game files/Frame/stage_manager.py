from enum import Enum, auto

class Stage(Enum):
    OVERWORLD = auto()
    BATTLE = auto()
    CARD_SELECT = auto()
    QUESTION_WAVE = auto()
    CARD_REWARD = auto()
    GAME_OVER = auto()
    NEXT_STAGE = auto()

class StageManager:
    def __init__(self, game_state):
        self.game_state = game_state
        self.callbacks = {}
        self.current_stage = Stage.OVERWORLD
        self.next_stage = None

    def register(self, stage, callback):
        self.callbacks[stage] = callback

    def transition_to(self, stage):
        self.next_stage = stage

    def check_conditions(self):
        if self.next_stage is not None:
            self.current_stage = self.next_stage
            self.next_stage = None
            if self.current_stage in self.callbacks:
                self.callbacks[self.current_stage]()
