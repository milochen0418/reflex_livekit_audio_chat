import reflex as rx
import os
import logging
from livekit import api


class ConferenceState(rx.State):
    room_name: str = ""
    username: str = ""
    token: str = ""
    connection_status: str = "Disconnected"
    participants: list[dict[str, str | bool]] = []
    is_connected: bool = False
    is_muted: bool = False
    error_message: str = ""
    loading: bool = False

    @rx.event
    async def join_room(self, form_data: dict):
        self.loading = True
        self.error_message = ""
        yield
        try:
            username = form_data.get("username", "").strip()
            room_name = form_data.get("room_name", "").strip()
            if not username or not room_name:
                self.error_message = "Username and Room Name are required."
                self.loading = False
                return
            api_key = os.environ.get("LIVEKIT_API_KEY")
            api_secret = os.environ.get("LIVEKIT_API_SECRET")
            livekit_url = os.environ.get("LIVEKIT_URL")
            if not api_key or not api_secret or (not livekit_url):
                self.error_message = (
                    "LiveKit credentials not configured. Please check settings."
                )
                self.loading = False
                return
            grant = api.VideoGrants(room_join=True, room=room_name)
            access_token = (
                api.AccessToken(api_key, api_secret)
                .with_identity(username)
                .with_name(username)
                .with_grants(grant)
                .to_jwt()
            )
            self.token = access_token
            self.room_name = room_name
            self.username = username
            self.is_connected = True
            self.connection_status = "Connecting..."
            self.is_muted = False
            safe_username = self.username.replace("'", "\\'").replace("\\", "\\\\")
            self.loading = False
            yield rx.call_script(
                f"window.livekitClient.connect('{livekit_url}', '{self.token}', '{safe_username}')"
            )
        except Exception as e:
            logging.exception(f"Error generating token: {e}")
            self.error_message = f"Failed to join room: {str(e)}"
            self.is_connected = False
            self.loading = False

    @rx.event
    def leave_room(self):
        yield rx.call_script("window.livekitClient.disconnect()")
        self.is_connected = False
        self.room_name = ""
        self.token = ""
        self.participants = []
        self.connection_status = "Disconnected"
        self.is_muted = False
        self.error_message = ""

    @rx.event
    def toggle_mute(self):
        new_muted_state = not self.is_muted
        self.is_muted = new_muted_state
        yield rx.call_script(
            f"window.livekitClient.setMicrophone({str(not new_muted_state).lower()})"
        )

    @rx.event
    def handle_js_message(self, json_data: str):
        import json
        logging.info(f"Received JS message: {json_data[:100]}...") # Log first 100 chars

        if not json_data or json_data.strip() == "":
            return
        try:
            data = json.loads(json_data)
            if "type" in data and data["type"] == "error":
                self.error_message = data.get("message", "Unknown error")
                self.is_connected = False
                self.loading = False
                yield rx.toast.error(f"Error: {self.error_message}")
                return
            if "status" in data:
                self.connection_status = data["status"]
                if data["status"] == "Disconnected":
                    self.is_connected = False
            if "participants" in data:
                # Ensure each participant has valid keys to avoid rendering errors
                self.participants = data["participants"]
            if "is_muted" in data:
                self.is_muted = data["is_muted"]
        except json.JSONDecodeError as e:
            logging.exception(f"Invalid JSON from JS: {e}")
        except Exception as e:
            logging.exception(f"Failed to parse JS message: {e}")