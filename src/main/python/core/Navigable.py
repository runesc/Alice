from utils.screen import get_activity


class Navigable:

    def navigate(self, screen_name: str):
        idx = get_activity(self.store, screen_name)

        if idx == -1:
            raise ValueError(
                f"Screen '{screen_name}' is not registered in Activities"
            )

        current_idx = self.store["activities"]["idx"]

        # evitar navegación redundante
        if idx == current_idx:
            return

        self.update_nested_model(
            "activities",
            {"idx": idx}
        )