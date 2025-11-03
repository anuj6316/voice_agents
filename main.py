# Imports
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentSession, RunContext
from livekit.agents.llm import function_tool
from livekit.plugins import openai, deepgram, silero, google
from datetime import datetime
import os
load_dotenv()
# Creating agent class
class Assistant(Agent):
    """Basic voice assistant with Airbnb booking capabilities."""

    def __init__(self):
        super().__init__(
            instructions="""You are a helpful and friendly Airbnb voice assistant.
            You can help users search for Airbnbs in different cities and book their stays.
            Keep your responses concise and natural, as if having a conversation."""
        )


async def entrypoint(ctx: agents.JobContext):
    """Entry point for the agent"""
    session = AgentSession(
        stt=openai.STT(model="gpt-4o-transcribe"),
        llm=google.LLM(model='gemini-2.0-flash', api_key=os.getenv('GOOGLE_API_KEY')),
        tts=openai.TTS(
            model="gpt-4o-mini-tts",
            voice="alloy",  # or "verse", "aria", etc.
            api_key=os.getenv("OPENAI_API_KEY")
        ),
        vad=silero.VAD.load()
    )
    await session.start(
        room=ctx.room,
        agent=Assistant()
    )
    await session.generate_reply(
        instructions="Greet the user warmly."
    )

if __name__=="__main__":
    print(os.getenv('OPENAI_API_KEY'))
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))