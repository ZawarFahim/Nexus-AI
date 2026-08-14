import logging
from typing import Any

from nexus.core.config import Settings
from nexus.core.protocols import ToolResult
from nexus.tools.registry import Tool

logger = logging.getLogger(__name__)

def create_spotify_client(settings: Settings) -> Any:
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
    except ImportError:
        logger.warning("spotipy not installed; Spotify tool disabled")
        return None

    if not settings.spotipy_client_id or not settings.spotipy_client_secret:
        return None
    
    try:
        auth_manager = SpotifyOAuth(
            client_id=settings.spotipy_client_id,
            client_secret=settings.spotipy_client_secret,
            redirect_uri=settings.spotipy_redirect_uri,
            scope="user-modify-playback-state user-read-playback-state",
            open_browser=True
        )
        return spotipy.Spotify(auth_manager=auth_manager)
    except Exception as e:
        logger.error(f"Failed to initialize Spotify: {e}")
        return None


def spotify_tool(settings: Settings) -> Tool | None:
    sp = create_spotify_client(settings)
    if not sp:
        return None
        
    def execute(arguments: dict[str, Any]) -> ToolResult:
        action = arguments.get("action")
        query = arguments.get("query", "")
        try:
            if action == "play":
                if query:
                    # Search for the track
                    result = sp.search(q=query, type="track", limit=1)
                    tracks = result.get('tracks', {}).get('items', [])
                    if tracks:
                        uri = tracks[0]['uri']
                        name = tracks[0]['name']
                        artist = tracks[0]['artists'][0]['name']
                        sp.start_playback(uris=[uri])
                        return ToolResult(f"Playing '{name}' by {artist}.")
                    return ToolResult(f"Could not find any track matching '{query}'.")
                else:
                    sp.start_playback()
                    return ToolResult("Resumed playback.")
            elif action == "pause":
                sp.pause_playback()
                return ToolResult("Paused playback.")
            elif action == "next":
                sp.next_track()
                return ToolResult("Skipped to next track.")
            elif action == "previous":
                sp.previous_track()
                return ToolResult("Skipped to previous track.")
            elif action == "current":
                current = sp.current_playback()
                if current and current.get('is_playing'):
                    item = current.get('item')
                    if item:
                        name = item['name']
                        artist = item['artists'][0]['name']
                        return ToolResult(f"Currently playing '{name}' by {artist}.")
                return ToolResult("Nothing is currently playing.")
            else:
                return ToolResult(f"Unknown action: {action}")
        except Exception as e:
            logger.error(f"Spotify tool error: {e}")
            if "NO_ACTIVE_DEVICE" in str(e):
                return ToolResult("Error: No active Spotify device found. Please open the Spotify app on your computer or phone and start playing something first.")
            return ToolResult(f"Failed to execute Spotify action '{action}': {e}")

    return Tool(
        name="control_spotify",
        description="Controls Spotify playback. Use this to play music, pause, skip tracks, or check what is playing. Note: requires an active Spotify device (open the Spotify app first).",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "The action to perform: 'play', 'pause', 'next', 'previous', 'current'.",
                    "enum": ["play", "pause", "next", "previous", "current"]
                },
                "query": {
                    "type": "string",
                    "description": "The name of the song to search for and play. Only use this if action is 'play' and the user specifically requested a song."
                }
            },
            "required": ["action"]
        },
        run=execute,
    )
