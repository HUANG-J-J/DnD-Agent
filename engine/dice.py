import random


class Dice:
    @staticmethod
    def roll(sides: int) -> int:
        return random.randint(1, sides)


    