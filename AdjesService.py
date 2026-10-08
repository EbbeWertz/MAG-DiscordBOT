import json
import os

ADJES_JSON = "adjes.json"


class AdjesService:

    def __init__(self):
        self.adjes: dict[str, int] = {}  # user_id -> total adjes amount
        self.last_adjes: dict[str, int] = {} # user_id -> last added adjes amount
        self._load_counter()

    def _load_counter(self):
        if os.path.exists(ADJES_JSON):
            try:
                with open(ADJES_JSON, "r") as f:
                    self.adjes = json.load(f)
            except Exception as e:
                print(f"Error loading counter file: {e}")
        else:
            self._save_counter()

    def _save_counter(self):
        try:
            with open(ADJES_JSON, "w") as f:
                json.dump(self.adjes, f, indent=4)
        except Exception as e:
            print(f"Error saving counter file: {e}")

    def register_adje(self, user_id: str, amount: int):
        self.adjes[user_id] = self.adjes.get(user_id, 0) + amount
        self.last_adjes[user_id] = amount
        self._save_counter()

    def undo_adje(self, user_id: str):
        adjes = self.last_adjes.get(user_id, 0)
        self.adjes[user_id] = max(0, self.adjes.get(user_id, 0) - adjes)
        self.last_adjes[user_id] = 0
        self._save_counter()

    def remove_user(self, user_id: str) -> bool:
        removed = False
        if user_id in self.adjes:
            del self.adjes[user_id]
            removed = True
        if user_id in self.last_adjes:
            del self.last_adjes[user_id]
        if removed:
            self._save_counter()
        return removed

    def clear_all(self):
        self.adjes.clear()
        self.last_adjes.clear()
        self._save_counter()