import random


class Dice:
    def __init__(self, seed=None): 
        self.rng = random.Random(seed)

    def roll(self, sides:int ) -> int:
        return self.rng.randint(1, sides)
    