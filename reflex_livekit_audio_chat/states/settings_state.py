import reflex as rx
import os
from pathlib import Path
import logging


class SettingsState(rx.State):
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    livekit_url: str = ""
    is_saving: bool = False

    @rx.event
    def load_config(self):
        """Load existing config from environment or .env file."""
        self.livekit_api_key = os.environ.get("LIVEKIT_API_KEY", "")
        self.livekit_api_secret = os.environ.get("LIVEKIT_API_SECRET", "")
        self.livekit_url = os.environ.get("LIVEKIT_URL", "")

    @rx.event
    async def save_config(self, form_data: dict[str, str]):
        """Save form data to .env file and update state."""
        self.is_saving = True
        yield
        try:
            api_key = form_data.get("livekit_api_key", "").strip()
            api_secret = form_data.get("livekit_api_secret", "").strip()
            url = form_data.get("livekit_url", "").strip()
            if not api_key or not api_secret or (not url):
                yield rx.toast("All fields are required", duration=3000)
                self.is_saving = False
                return
            os.environ["LIVEKIT_API_KEY"] = api_key
            os.environ["LIVEKIT_API_SECRET"] = api_secret
            os.environ["LIVEKIT_URL"] = url
            env_path = Path(".env")
            content = f"LIVEKIT_API_KEY={api_key}\nLIVEKIT_API_SECRET={api_secret}\nLIVEKIT_URL={url}\n"
            with env_path.open("w") as f:
                f.write(content)
            self.livekit_api_key = api_key
            self.livekit_api_secret = api_secret
            self.livekit_url = url
            yield rx.toast("Settings saved successfully!", duration=3000)
        except Exception as e:
            logging.exception(f"Error saving settings: {e}")
            yield rx.toast(f"Failed to save settings: {str(e)}", duration=5000)
        finally:
            self.is_saving = False