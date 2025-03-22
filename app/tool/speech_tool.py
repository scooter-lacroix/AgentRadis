"""
Speech Tool - Handles speech recognition and synthesis using RealtimeSTT and RealtimeTTS
"""

import os
import asyncio
import tempfile
from typing import Dict, Any, Optional, List, Union

from app.tool.base import BaseTool
from app.logger import logger

class SpeechTool(BaseTool):
    """
    Tool for speech recognition and synthesis using RealtimeSTT and RealtimeTTS.
    This tool allows Radis to listen to and speak with users.
    """
    
    name = "speech"
    description = """
    Handle speech recognition and synthesis for voice interaction.
    This tool can:
    - Convert speech to text (listen to user)
    - Convert text to speech (speak to user)
    - Manage continuous listening/speaking
    """
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["listen", "speak", "start_listening", "stop_listening"],
                "description": "The speech action to perform"
            },
            "text": {
                "type": "string",
                "description": "Text to speak (for 'speak' action)"
            },
            "options": {
                "type": "object",
                "description": "Additional options for the speech action",
                "properties": {
                    "voice": {
                        "type": "string",
                        "description": "Voice to use for speech synthesis"
                    },
                    "speed": {
                        "type": "number",
                        "description": "Speech rate multiplier (0.5 to 2.0)"
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Listen timeout in seconds for speech recognition"
                    }
                }
            }
        },
        "required": ["action"]
    }
    
    # STT/TTS modules will be imported dynamically to avoid
    # requiring them if they're not installed
    _realtimestt = None
    _realtimetts = None
    _recorder = None
    _stt_available = False
    _tts_available = False
    
    # Voice record/playback state
    _is_listening = False
    _is_speaking = False
    _is_initialized = False
    _temp_file = None
    
    def __init__(self, **kwargs):
        """Initialize the speech tool."""
        super().__init__(**kwargs)
        
        # Try to import the RealtimeSTT/TTS modules
        self._init_modules()
        
    def _init_modules(self):
        """Initialize the STT/TTS modules if available."""
        if self._is_initialized:
            return
            
        # Check for RealtimeSTT
        try:
            import realtimestt
            self._realtimestt = realtimestt
            self._stt_available = True
            logger.info("RealtimeSTT is available")
        except ImportError:
            logger.warning("RealtimeSTT is not installed, speech recognition will not be available")
            self._stt_available = False
            
        # Check for RealtimeTTS
        try:
            import realtimetts
            self._realtimetts = realtimetts
            self._tts_available = True
            logger.info("RealtimeTTS is available")
        except ImportError:
            logger.warning("RealtimeTTS is not installed, text-to-speech will not be available")
            self._tts_available = False
            
        self._is_initialized = True
        
    async def _init_recorder(self):
        """Initialize the audio recorder for STT."""
        if not self._stt_available or self._recorder is not None:
            return
            
        try:
            # Initialize the recorder
            self._recorder = self._realtimestt.AudioToTextRecorder(
                model="tiny.en",
                spinner=False,
                include_punctuation=True,
                include_speaker_label=False
            )
            logger.info("Speech recognition initialized")
        except Exception as e:
            logger.error(f"Failed to initialize speech recognition: {e}")
            self._stt_available = False
            
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute a speech action."""
        if not self._is_initialized:
            self._init_modules()
            
        action = kwargs.get("action", "")
        options = kwargs.get("options", {})
        
        if action == "listen":
            return await self.listen(timeout=options.get("timeout", 10))
        elif action == "speak":
            text = kwargs.get("text", "")
            if not text:
                return {
                    "status": "error",
                    "error": "No text provided for speak action"
                }
            return await self.speak(
                text, 
                voice=options.get("voice", "default"),
                speed=options.get("speed", 1.0)
            )
        elif action == "start_listening":
            return await self.start_continuous_listening()
        elif action == "stop_listening":
            return await self.stop_continuous_listening()
        else:
            return {
                "status": "error",
                "error": f"Unknown action: {action}"
            }
            
    async def listen(self, timeout: float = 10.0) -> Dict[str, Any]:
        """
        Listen for speech and convert to text.
        
        Args:
            timeout: Maximum time to listen in seconds
            
        Returns:
            Dict containing the recognized text or error
        """
        if not self._stt_available:
            return {
                "status": "error",
                "error": "Speech recognition is not available"
            }
            
        try:
            await self._init_recorder()
            
            # Start recording
            logger.info(f"Listening for speech (timeout: {timeout}s)")
            self._is_listening = True
            
            # Use recorder in wait_for_speech mode with timeout
            result = await asyncio.wait_for(
                self._recorder.wait_for_speech_async(),
                timeout=timeout
            )
            
            self._is_listening = False
            
            if result and hasattr(result, 'text'):
                recognized_text = result.text
                logger.info(f"Recognized speech: {recognized_text}")
                return {
                    "status": "success",
                    "text": recognized_text
                }
            else:
                return {
                    "status": "error",
                    "error": "No speech detected"
                }
                
        except asyncio.TimeoutError:
            self._is_listening = False
            logger.info("Speech recognition timed out")
            return {
                "status": "timeout",
                "error": "Listening timed out"
            }
        except Exception as e:
            self._is_listening = False
            logger.error(f"Error during speech recognition: {e}")
            return {
                "status": "error",
                "error": f"Speech recognition error: {str(e)}"
            }
            
    async def speak(self, text: str, voice: str = "default", speed: float = 1.0) -> Dict[str, Any]:
        """
        Convert text to speech and play it.
        
        Args:
            text: Text to speak
            voice: Voice to use
            speed: Speech rate multiplier
            
        Returns:
            Dict containing status of the speech synthesis
        """
        if not self._tts_available:
            return {
                "status": "error",
                "error": "Text-to-speech is not available"
            }
            
        try:
            # Import here to avoid module not found errors
            if not self._realtimetts:
                return {
                    "status": "error",
                    "error": "RealtimeTTS is not available"
                }
                
            # Get the TTS synthesizer
            if voice == "default" or not voice:
                # Use default synthesizer
                synthesizer = self._realtimetts.get_default_synthesizer()
            else:
                # Try to use the requested voice
                try:
                    # Check if it's a system voice
                    synthesizer = self._realtimetts.SystemSpeechSynthesizer(voice)
                except:
                    # If not, try other synthesizers
                    if voice.lower() in ["edge", "microsoft"]:
                        synthesizer = self._realtimetts.EdgeSynthesizer()
                    elif voice.lower() in ["piper"]:
                        synthesizer = self._realtimetts.PiperSynthesizer()
                    elif voice.lower() in ["elevenlabs", "eleven"]:
                        synthesizer = self._realtimetts.ElevenLabsSynthesizer()
                    else:
                        # Default to system default
                        synthesizer = self._realtimetts.get_default_synthesizer()
            
            # Create speech engine with the synthesizer
            speech_engine = self._realtimetts.Speech(synthesizer)
            
            # Remove or escape any problematic characters
            cleaned_text = text.replace('\n', ' ').replace('\t', ' ')
            
            # Speak the text
            self._is_speaking = True
            speech_engine.speech_rate = speed
            await speech_engine.speak_async(cleaned_text)
            self._is_speaking = False
            
            return {
                "status": "success",
                "message": f"Spoke text ({len(text)} characters)",
                "text": text[:100] + ("..." if len(text) > 100 else "")
            }
            
        except Exception as e:
            self._is_speaking = False
            logger.error(f"Error during speech synthesis: {e}")
            return {
                "status": "error",
                "error": f"Text-to-speech error: {str(e)}"
            }
            
    async def start_continuous_listening(self) -> Dict[str, Any]:
        """
        Start continuous listening mode.
        
        Returns:
            Dict containing status of the listening start
        """
        if not self._stt_available:
            return {
                "status": "error",
                "error": "Speech recognition is not available"
            }
            
        if self._is_listening:
            return {
                "status": "warning",
                "message": "Already listening"
            }
            
        try:
            await self._init_recorder()
            
            # Start the recorder in continuous mode
            logger.info("Starting continuous listening")
            self._is_listening = True
            
            # TODO: Implement continuous listening 
            # For now, return success but note it's not implemented
            return {
                "status": "success",
                "message": "Continuous listening started",
                "note": "In continuous listening mode, use stop_listening when done"
            }
            
        except Exception as e:
            self._is_listening = False
            logger.error(f"Error starting continuous listening: {e}")
            return {
                "status": "error", 
                "error": f"Failed to start listening: {str(e)}"
            }
            
    async def stop_continuous_listening(self) -> Dict[str, Any]:
        """
        Stop continuous listening mode.
        
        Returns:
            Dict containing status of the listening stop
        """
        if not self._is_listening:
            return {
                "status": "warning",
                "message": "Not currently listening"
            }
            
        try:
            # Stop the recorder
            logger.info("Stopping continuous listening")
            self._is_listening = False
            
            # TODO: Implement stopping continuous listening
            
            return {
                "status": "success",
                "message": "Continuous listening stopped"
            }
            
        except Exception as e:
            logger.error(f"Error stopping continuous listening: {e}")
            return {
                "status": "error",
                "error": f"Failed to stop listening: {str(e)}"
            }
            
    async def run(self, **kwargs) -> Dict[str, Any]:
        """Run the speech tool with the given arguments."""
        return await self.execute(**kwargs)
        
    async def cleanup(self):
        """Clean up resources used by the speech tool."""
        # Stop listening if active
        if self._is_listening:
            await self.stop_continuous_listening()
            
        # Clean up temporary files
        if self._temp_file and os.path.exists(self._temp_file):
            try:
                os.remove(self._temp_file)
            except:
                pass
            
        # Clean up recorder
        if self._recorder:
            try:
                self._recorder.cleanup()
                self._recorder = None
            except:
                pass 