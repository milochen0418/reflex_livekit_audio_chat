from __future__ import annotations

import json
import logging
import os
from typing import Type

import reflex as rx
from livekit import api


class LiveKitBridgeState(rx.State):
    """State that bridges Reflex <-> LiveKit JS client running in the browser."""

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

            # Escape username for JS.
            safe_username = self.username.replace("\\", "\\\\").replace("'", "\\'")

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
        if not json_data or json_data.strip() == "":
            return

        try:
            data = json.loads(json_data)

            if data.get("type") == "error":
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
                self.participants = data["participants"]

            if "is_muted" in data:
                self.is_muted = data["is_muted"]
        except json.JSONDecodeError as e:
            logging.exception(f"Invalid JSON from JS: {e}")
        except Exception as e:
            logging.exception(f"Failed to parse JS message: {e}")


class _LiveKitUI:
    """UI + JS binding helpers for LiveKit."""

    def __init__(self, state_cls: Type[rx.State], *, bridge_input_id: str = "js_msg_input"):
        self._state_cls = state_cls
        self._bridge_input_id = bridge_input_id

    def bridge_input(self) -> rx.Component:
        return rx.el.input(
            id=self._bridge_input_id,
            class_name="hidden",
            on_change=self._state_cls.handle_js_message,
        )

    def volume_bar(self, identity: str, *, width: str = "0%") -> rx.Component:
        return rx.el.div(
            id=f"vol-{identity}",
            class_name="h-full bg-violet-500 transition-all duration-75 rounded-full",
            style={"width": width},
        )

    def head_components(self) -> list[rx.Component]:
        return [
            rx.el.script(
                src="https://cdn.jsdelivr.net/npm/livekit-client/dist/livekit-client.umd.min.js"
            ),
            rx.el.script(
                f"""
                    window.livekitClient = {{
                        room: null,
                        audioInterval: null,

                        async connect(url, token, username) {{
                            try {{
                                if (this.room) {{
                                    await this.room.disconnect();
                                }}

                                this.room = new LivekitClient.Room({{
                                    adaptiveStream: true,
                                    dynacast: true,
                                    publishDefaults: {{
                                        audioPreset: LivekitClient.AudioPresets.music,
                                    }},
                                }});

                                this.room
                                    .on(LivekitClient.RoomEvent.Connected, () => this.sendStatus({{ status: 'Connected' }}))
                                    .on(LivekitClient.RoomEvent.Reconnecting, () => this.sendStatus({{ status: 'Reconnecting...' }}))
                                    .on(LivekitClient.RoomEvent.Reconnected, () => this.sendStatus({{ status: 'Connected' }}))
                                    .on(LivekitClient.RoomEvent.ParticipantConnected, () => this.updateParticipants())
                                    .on(LivekitClient.RoomEvent.ParticipantDisconnected, () => this.updateParticipants())
                                    .on(LivekitClient.RoomEvent.ActiveSpeakersChanged, () => this.updateParticipants())
                                    .on(LivekitClient.RoomEvent.TrackSubscribed, (track) => {{
                                        if (track.kind === 'audio') {{
                                            track.attach();
                                        }}
                                    }})
                                    .on(LivekitClient.RoomEvent.Disconnected, () => {{
                                        this.sendStatus({{ status: 'Disconnected', participants: [] }});
                                        this.stopAudioVisualizer();
                                    }});

                                await this.room.connect(url, token);

                                // Publish local mic
                                await this.room.localParticipant.setMicrophoneEnabled(true);

                                this.updateParticipants();
                                this.startAudioVisualizer();

                                // Force connected status just in case
                                if (this.room.state === 'connected') {{
                                    this.sendStatus({{ status: 'Connected' }});
                                }}
                            }} catch (error) {{
                                console.error('Connection error:', error);
                                this.sendStatus({{ type: 'error', message: error.message }});
                            }}
                        }},

                        async disconnect() {{
                            if (this.room) {{
                                await this.room.disconnect();
                                this.room = null;
                                this.stopAudioVisualizer();
                            }}
                        }},

                        startAudioVisualizer() {{
                            this.stopAudioVisualizer();
                            this.audioInterval = setInterval(() => {{
                                if (!this.room) return;

                                const updateBar = (p) => {{
                                    if (!p) return;
                                    const identity = p.identity;
                                    const el = document.getElementById('vol-' + identity);
                                    if (el) {{
                                        let level = p.audioLevel || 0;
                                        let width = Math.min(100, level * 100 * 5);
                                        if (width < 5 && width > 0) width = 5;
                                        if (level === 0) width = 0;
                                        el.style.width = width + '%';
                                    }}
                                }};

                                if (this.room.localParticipant) updateBar(this.room.localParticipant);
                                this.room.remoteParticipants.forEach(p => updateBar(p));
                            }}, 50);
                        }},

                        stopAudioVisualizer() {{
                            if (this.audioInterval) {{
                                clearInterval(this.audioInterval);
                                this.audioInterval = null;
                            }}
                        }},

                        async setMicrophone(enabled) {{
                            if (this.room && this.room.localParticipant) {{
                                await this.room.localParticipant.setMicrophoneEnabled(enabled);
                                this.updateParticipants();
                            }}
                        }},

                        updateParticipants() {{
                            if (!this.room) return;

                            const participants = [];

                            // Add local participant
                            participants.push({{
                                identity: this.room.localParticipant.identity,
                                is_speaking: this.room.localParticipant.isSpeaking,
                                is_local: true,
                            }});

                            // Add remote participants
                            this.room.remoteParticipants.forEach((p) => {{
                                participants.push({{
                                    identity: p.identity,
                                    is_speaking: p.isSpeaking,
                                    is_local: false,
                                }});
                            }});

                            this.sendStatus({{
                                participants: participants,
                                is_muted: !this.room.localParticipant.isMicrophoneEnabled,
                            }});
                        }},

                        sendStatus(data) {{
                            const input = document.getElementById('{self._bridge_input_id}');
                            if (input) {{
                                const jsonStr = JSON.stringify(data);

                                // Hack for React 16+ to trigger onChange
                                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                                nativeInputValueSetter.call(input, jsonStr);

                                const event = new Event('input', {{ bubbles: true }});
                                input.dispatchEvent(event);
                            }}
                        }}
                    }};
                """
            ),
        ]


def bind_livekit(state_cls: Type[rx.State]) -> _LiveKitUI:
    return _LiveKitUI(state_cls)
