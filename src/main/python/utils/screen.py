from models.screen import Activities

def get_activity(store, name: str) -> int:
        activities: Activities = store["activities"]
        for idx, activity in enumerate(activities["screens"]):
            if activity["name"] == name:
                return idx
        return -1