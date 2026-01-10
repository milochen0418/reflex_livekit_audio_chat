import reflex as rx
import os
from pathlib import Path
import logging
from dotenv import dotenv_values


class SettingsState(rx.State):
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    livekit_url: str = ""
    is_saving: bool = False

    is_admin_authenticated: bool = False
    is_authenticating: bool = False
    auth_error: str = ""

    @rx.event
    def on_settings_load(self):
        """Reset admin gate when navigating to /settings."""
        self.is_admin_authenticated = False
        self.is_authenticating = False
        self.auth_error = ""
        # Don't load config until admin is authenticated.
        self.livekit_api_key = ""
        self.livekit_api_secret = ""
        self.livekit_url = ""

    @rx.event
    async def verify_admin(self, form_data: dict[str, str]):
        self.is_authenticating = True
        self.auth_error = ""
        yield
        try:
            provided = (form_data.get("admin_passcode") or "").strip()
            expected = (os.environ.get("ADMIN_PASSCODE") or "").strip()

            if not expected:
                self.auth_error = "ADMIN_PASSCODE is not set in the environment."
                yield rx.toast.error(self.auth_error)
                return

            if provided != expected:
                self.auth_error = "Invalid admin passcode."
                yield rx.toast.error(self.auth_error)
                return

            self.is_admin_authenticated = True
            self.load_config()
            yield rx.toast.success("Admin access granted.")
        finally:
            self.is_authenticating = False

    @rx.event
    def load_config(self):
        """Load existing config from environment or .env file."""
        self.livekit_api_key = os.environ.get("LIVEKIT_API_KEY", "")
        self.livekit_api_secret = os.environ.get("LIVEKIT_API_SECRET", "")
        self.livekit_url = os.environ.get("LIVEKIT_URL", "")

    @rx.event
    async def save_config(self, form_data: dict[str, str]):
        """Save form data to .env file and update state."""
        if not self.is_admin_authenticated:
            yield rx.toast.error("Admin access required.")
            return

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

            existing = dotenv_values(env_path) if env_path.exists() else {}
            # Preserve ADMIN_PASSCODE (and any other existing keys) while updating LiveKit keys.
            merged = dict(existing)
            merged["LIVEKIT_API_KEY"] = api_key
            merged["LIVEKIT_API_SECRET"] = api_secret
            merged["LIVEKIT_URL"] = url

            lines: list[str] = []
            for key, value in merged.items():
                if value is None:
                    continue
                lines.append(f"{key}={value}")
            with env_path.open("w") as f:
                f.write("\n".join(lines) + "\n")

            self.livekit_api_key = api_key
            self.livekit_api_secret = api_secret
            self.livekit_url = url
            yield rx.toast("Settings saved successfully!", duration=3000)
        except Exception as e:
            logging.exception(f"Error saving settings: {e}")
            yield rx.toast(f"Failed to save settings: {str(e)}", duration=5000)
        finally:
            self.is_saving = False