from __future__ import annotations

from typing import Type

import reflex as rx


class _LiveKitUI:
    """UI + JS binding helpers for LiveKit.

    This keeps a single source of truth for:
    - the hidden input that bridges JS -> Reflex state
    - the JS bundle + client code injected into <head>
    - small UI primitives (e.g., volume bars)
    """

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
        # Keep the JS implementation aligned with the previous working in-file version.
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
                                console.log('Sending to backend:', data);
                                const jsonStr = JSON.stringify(data);

                                // Hack for React 16+ to trigger onChange
                                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                                nativeInputValueSetter.call(input, jsonStr);

                                const event = new Event('input', {{ bubbles: true }});
                                input.dispatchEvent(event);
                            }} else {{
                                console.error('{self._bridge_input_id} not found!');
                            }}
                        }}
                    }};
                """
            ),
        ]


def bind_livekit(state_cls: Type[rx.State]) -> _LiveKitUI:
    return _LiveKitUI(state_cls)
