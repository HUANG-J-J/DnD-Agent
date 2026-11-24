from engine.dice import Dice


class GameState:
    def __init__ (self, seed=None):
        self.hero = None
        self.dice = Dice(seed)
        