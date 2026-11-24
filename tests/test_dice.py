from engine.dice import Dice


def test_same_seed_same_sequence():
    a, b = Dice(42), Dice(42)
    assert [a.roll(20) for _ in range(10)] == [b.roll(20) for _ in range(10)]


def test_roll_in_range():
    d = Dice(0)
    assert all(1 <= d.roll(6) <= 6 for _ in range(200))
