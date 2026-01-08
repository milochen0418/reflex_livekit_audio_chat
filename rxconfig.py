import reflex as rx
from dotenv import load_dotenv

load_dotenv()

config = rx.Config(app_name="reflex_livekit_audio_chat", plugins=[rx.plugins.TailwindV3Plugin()])
