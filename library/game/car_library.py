from __future__ import annotations

from library.game.car import Car


class CarLibrary:
    """The bro's collection of cars. One MK7 GTI for now; structured for more
    later (and to serialize as a list in the save file)."""

    def __init__(self):
        self.cars = [Car("mk7_gti")]
        self.active_index = 0

    def active(self) -> Car:
        return self.cars[self.active_index]

    def to_dict(self) -> dict:
        return {"active_index": self.active_index, "cars": [car.to_dict() for car in self.cars]}

    def from_dict(self, data: dict):
        self.active_index = data.get("active_index", 0)
        self.cars = []
        for car_data in data.get("cars", []):
            # Construct from the saved car_id so the physics spec loads; then restore the
            # build state. Old saves (no car_id) default to the MK7 GTI.
            car = Car(car_data.get("car_id", "mk7_gti"))
            car.from_dict(car_data)
            self.cars.append(car)
        if not self.cars:
            self.cars = [Car("mk7_gti")]
