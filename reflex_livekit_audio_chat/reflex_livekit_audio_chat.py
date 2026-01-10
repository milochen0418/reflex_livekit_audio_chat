import reflex as rx
from reflex_livekit_audio_chat.states.settings_state import SettingsState
from reflex_livekit_audio_chat.livekit_bridge import LiveKitBridgeState, bind_livekit

# Single source of truth for how LiveKit JS binds to this UI.
LIVEKIT_UI = bind_livekit(LiveKitBridgeState)


def input_field(
    label: str, name: str, placeholder: str, type: str = "text", value: str = ""
) -> rx.Component:
    return rx.el.div(
        rx.el.label(label, class_name="block text-sm font-semibold text-gray-700 mb-1"),
        rx.el.input(
            name=name,
            type=type,
            placeholder=placeholder,
            default_value=value,
            key=value,
            class_name="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500 focus:border-transparent outline-none transition-all",
        ),
        class_name="w-full",
    )


def settings_page() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.a(
                    rx.el.div(
                        rx.icon("arrow-left", class_name="h-4 w-4"),
                        rx.el.span("Back to Lobby"),
                        class_name="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors",
                    ),
                    href="/",
                    class_name="mb-6 inline-block",
                ),
                rx.el.div(
                    rx.icon("settings", class_name="text-violet-500 h-8 w-8"),
                    rx.el.h1(
                        "LiveKit Configuration",
                        class_name="text-2xl font-bold text-gray-900",
                    ),
                    class_name="flex items-center gap-3 mb-2",
                ),
                rx.el.p(
                    "Configure your LiveKit Cloud credentials to enable real-time audio features.",
                    class_name="text-gray-500 text-sm mb-8",
                ),
                rx.el.form(
                    rx.el.div(
                        input_field(
                            "API Key",
                            "livekit_api_key",
                            "devkey...",
                            value=SettingsState.livekit_api_key,
                        ),
                        input_field(
                            "API Secret",
                            "livekit_api_secret",
                            "secret...",
                            type="password",
                            value=SettingsState.livekit_api_secret,
                        ),
                        input_field(
                            "LiveKit Server URL",
                            "livekit_url",
                            "wss://your-project.livekit.cloud",
                            value=SettingsState.livekit_url,
                        ),
                        rx.el.button(
                            rx.cond(
                                SettingsState.is_saving,
                                rx.el.span("Saving...", class_name="animate-pulse"),
                                rx.el.div(
                                    rx.icon("save", class_name="h-4 w-4"),
                                    "Save Configuration",
                                    class_name="flex items-center gap-2",
                                ),
                            ),
                            type="submit",
                            disabled=SettingsState.is_saving,
                            class_name="w-full bg-violet-600 hover:bg-violet-700 text-white font-semibold py-2.5 rounded-lg transition-colors flex items-center justify-center mt-4 disabled:opacity-50",
                        ),
                        class_name="space-y-5",
                    ),
                    on_submit=SettingsState.save_config,
                    reset_on_submit=False,
                ),
                class_name="w-full max-w-md bg-white p-8 rounded-2xl border border-gray-100 shadow-sm",
            ),
            class_name="flex flex-col items-center justify-center min-h-screen bg-gray-50 px-4",
        ),
        class_name="font-['Inter']",
    )


def lobby_view() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon("mic-vocal", class_name="h-12 w-12 text-violet-600"),
                rx.el.h1(
                    "Audio Rooms",
                    class_name="text-4xl font-extrabold text-gray-900 tracking-tight",
                ),
                class_name="flex flex-col items-center gap-4 mb-10",
            ),
            rx.el.div(
                rx.el.form(
                    rx.el.div(
                        rx.cond(
                            LiveKitBridgeState.error_message != "",
                            rx.el.div(
                                rx.icon(
                                    "circle-alert",
                                    class_name="h-5 w-5 text-red-500 shrink-0",
                                ),
                                rx.el.p(
                                    LiveKitBridgeState.error_message,
                                    class_name="text-red-700 text-sm",
                                ),
                                class_name="bg-red-50 p-4 rounded-lg flex items-center gap-3 border border-red-100 mb-2",
                            ),
                            rx.fragment(),
                        ),
                        input_field(
                            "Display Name",
                            "username",
                            "Enter your name",
                            value=LiveKitBridgeState.username,
                        ),
                        input_field(
                            "Room Name",
                            "room_name",
                            "Enter room to join",
                            value=LiveKitBridgeState.room_name,
                        ),
                        rx.el.button(
                            rx.cond(
                                LiveKitBridgeState.loading,
                                rx.el.div(
                                    rx.spinner(size="1"),
                                    rx.el.span("Joining..."),
                                    class_name="flex items-center gap-2 justify-center",
                                ),
                                "Join Room",
                            ),
                            type="submit",
                            disabled=LiveKitBridgeState.loading,
                            class_name="w-full bg-violet-600 hover:bg-violet-700 text-white font-bold py-3 rounded-xl transition-all shadow-lg shadow-violet-200 mt-2 disabled:opacity-70",
                        ),
                        class_name="space-y-6",
                    ),
                    on_submit=LiveKitBridgeState.join_room,
                    reset_on_submit=False,
                ),
                class_name="w-full max-w-md bg-white p-8 rounded-3xl border border-gray-100 shadow-xl shadow-gray-200/50",
            ),
            rx.el.div(
                rx.el.a(
                    "Configure Settings",
                    href="/settings",
                    class_name="text-sm text-gray-500 hover:text-violet-600 transition-colors",
                ),
                class_name="mt-8 text-center",
            ),
            class_name="w-full flex flex-col items-center justify-center min-h-screen bg-gray-50 px-4",
        ),
        class_name="font-['Inter']",
    )


def participant_card(participant: dict) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.image(
                src=f"https://api.dicebear.com/9.x/notionists/svg?seed={participant['identity']}",
                class_name="size-12 rounded-full bg-gray-100",
            ),
            rx.cond(
                participant["is_speaking"],
                rx.el.div(
                    class_name="absolute -bottom-1 -right-1 size-4 bg-green-500 border-2 border-white rounded-full animate-pulse"
                ),
                rx.fragment(),
            ),
            class_name="relative",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    participant["identity"],
                    class_name="font-semibold text-gray-900 truncate",
                ),
                rx.el.p(
                    rx.cond(participant["is_local"], "You", "Participant"),
                    class_name="text-xs text-gray-500",
                ),
                class_name="flex justify-between items-baseline",
            ),
            rx.el.div(
                LIVEKIT_UI.volume_bar(
                    participant["identity"],
                    width=participant.get("audio_width", "0%"),
                ),
                class_name="h-1 bg-gray-100 rounded-full mt-2 w-full overflow-hidden",
            ),
            class_name="min-w-0 w-full",
        ),
        class_name="flex items-center gap-3 p-3 bg-white rounded-xl border border-gray-100 shadow-sm",
    )


def room_view() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.icon("hash", class_name="h-5 w-5 text-violet-500"),
                        rx.el.h2(
                            LiveKitBridgeState.room_name,
                            class_name="text-xl font-bold text-gray-900",
                        ),
                        class_name="flex items-center gap-2",
                    ),
                    rx.el.div(
                        rx.el.div(
                            class_name=rx.cond(
                                LiveKitBridgeState.connection_status == "Connected",
                                "size-2 rounded-full bg-green-500",
                                "size-2 rounded-full bg-yellow-500 animate-pulse",
                            )
                        ),
                        rx.el.span(
                            LiveKitBridgeState.connection_status,
                            class_name="text-sm font-medium text-gray-600",
                        ),
                        class_name="flex items-center gap-2 bg-white px-3 py-1 rounded-full border border-gray-100",
                    ),
                    class_name="flex items-center justify-between mb-8",
                ),
                rx.el.div(
                    rx.el.div(
                        rx.el.h3(
                            "Participants",
                            class_name="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4",
                        ),
                        rx.el.div(
                            rx.foreach(LiveKitBridgeState.participants, participant_card),
                            class_name="flex flex-col gap-3",
                        ),
                        class_name="flex-1 overflow-auto pr-2",
                    ),
                    class_name="flex flex-col h-[calc(100vh-280px)]",
                ),
                rx.el.div(
                    rx.el.div(
                        rx.el.button(
                            rx.icon(
                                rx.cond(LiveKitBridgeState.is_muted, "mic-off", "mic"),
                                class_name="h-6 w-6",
                            ),
                            on_click=LiveKitBridgeState.toggle_mute,
                            class_name=rx.cond(
                                LiveKitBridgeState.is_muted,
                                "p-4 rounded-full bg-red-100 text-red-600 hover:bg-red-200 transition-colors",
                                "p-4 rounded-full bg-violet-100 text-violet-600 hover:bg-violet-200 transition-colors",
                            ),
                        ),
                        rx.el.button(
                            rx.icon("phone-off", class_name="h-6 w-6"),
                            on_click=LiveKitBridgeState.leave_room,
                            class_name="p-4 rounded-full bg-gray-900 text-white hover:bg-gray-800 transition-colors",
                        ),
                        class_name="flex items-center justify-center gap-6",
                    ),
                    class_name="mt-8 pt-8 border-t border-gray-100",
                ),
                class_name="w-full max-w-2xl bg-white p-8 rounded-3xl border border-gray-100 shadow-xl",
            ),
            class_name="flex flex-col items-center justify-center min-h-screen bg-gray-50 px-4",
        ),
        class_name="font-['Inter']",
    )


def index() -> rx.Component:
    return rx.el.div(
        LIVEKIT_UI.bridge_input(),
        rx.cond(LiveKitBridgeState.is_connected, room_view(), lobby_view()),
    )


app = rx.App(
    theme=rx.theme(appearance="light"),
    head_components=[
        rx.el.link(rel="preconnect", href="https://fonts.googleapis.com"),
        rx.el.link(rel="preconnect", href="https://fonts.gstatic.com", cross_origin=""),
        rx.el.link(
            href="https://fonts.googleapis.com/css2?family=Inter:wght@400..700&display=swap",
            rel="stylesheet",
        ),
        *LIVEKIT_UI.head_components(),
    ],
)
app.add_page(index, route="/")
app.add_page(settings_page, route="/settings", on_load=SettingsState.load_config)