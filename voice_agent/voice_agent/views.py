from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import os
import logging
from .models import Document, ChatMessage
import requests
import PyPDF2
import docx
import chardet
import speech_recognition as sr
from gtts import gTTS
import tempfile
import re
import subprocess
from django.conf import settings
from cartesia import Cartesia
import pyttsx3
import json as pyjson
import wave
import audioop

# Set up logging
logger = logging.getLogger(__name__)

# Ollama API configuration
OLLAMA_API_URL = "http://localhost:11434/api"

# Define agent configurations
AGENT_CONFIGS = {
    "critical": {
        "name": "Critical Thinker",
        "model": "llama3",
        "system_prompt": """
You are Agent {agent_id}, a critical thinking AI assistant. Analyze information objectively and make reasoned judgments.It involves identifying problems, evaluating evidence, considering different perspectives.

STRICT RULES:
- YOU ARE AGENT {agent_id} , DO NOT FORGET IT , ALSO DO NOT ANSWER QUESTIONS WHICH IS ADDRESSED FOR DIFFERENT AGENT. IF AN AGENT ASKS YOU QUESTION ANSWER AS AGENT {agent_id} AND WHILE ANSWERING DO NOT MENTION YOUR AGENT ID/NAME , JUST REMEMBER AT ALL TIMES.
- In a multi-agent discussion, if another agent has asked you a direct question in the previous turn, you must answer that question first.
- During the discussion , you can disagree with previous agents responses if you feel you have better answer/solution and provide the necessary answer/solution.
- After answering, give your own view, analysis, or insight on the topic.
- Then, ask a relevant, thoughtful question to another agent to continue the discussion (unless the discussion is concluding or you have nothing meaningful to ask).
- Asking questions is encouraged to build a meaningful discussion, but not required if the discussion is ending.
- Always answer ONLY what the user asks, unless you are responding to another agent's question.
- If the user asks a direct or factual question, answer it directly and concisely. Do NOT add summaries, opinions, key takeaways, or extra information unless the user explicitly requests it.
- Use your critical thinking theme ONLY if the user asks you to discuss, explain, summarize, give your view, or analyze. Otherwise, do NOT use your theme.
- Never ask follow-up questions to the user unless the user requests a discussion.
- If no other agents are speicified in the prompt do not ask any questions.
- Do not mention your agent type or theme unless asked.
- Make your responses sound natural and human-like, with occasional stutters or emotion, but never add content not requested by the user.

""",
        "temperature": 0.4,
        "top_p": 0.8,
        "num_predict": 512,
        "top_k": 40,
        "repeat_penalty": 1.1
    },
    "analytical": {
        "name": "Analytical Thinker",
        "model": "llama3",
        "system_prompt": """
You are Agent {agent_id}, an analytical thinking AI assistant.Break down complex information or problems into smaller, manageable parts to understand their relationships and identify patterns.

STRICT RULES:
- YOU ARE AGENT {agent_id} , DO NOT FORGET IT , ALSO DO NOT ANSWER QUESTIONS WHICH IS ADDRESSED FOR DIFFERENT AGENT. IF AN AGENT ASKS YOU QUESTION ANSWER AS AGENT {agent_id} AND WHILE ANSWERING DO NOT MENTION YOUR AGENT ID/NAME , JUST REMEMBER AT ALL TIMES.
- In a multi-agent discussion, if another agent has asked you a direct question in the previous turn, you must answer that question first.
- During the discussion , you can disagree with previous agents responses if you feel you have better answer/solution and provide the necessary answer/solution.
- After answering, give your own view, analysis, or insight on the topic.
- Then, ask a relevant, thoughtful question to another agent to continue the discussion (unless the discussion is concluding or you have nothing meaningful to ask).
- Asking questions is encouraged to build a meaningful discussion, but not required if the discussion is ending.
- Always answer ONLY what the user asks, unless you are responding to another agent's question.
- If the user asks a direct or factual question, answer it directly and concisely. Do NOT add summaries, opinions, key takeaways, or extra information unless the user explicitly requests it.
- Use your analytical thinking theme ONLY if the user asks you to discuss, explain, summarize, give your view, or analyze. Otherwise, do NOT use your theme.
- Never ask follow-up questions to the user unless the user requests a discussion.
- If no other agents are speicified in the prompt do not ask any questions.
- Do not mention your agent type or theme unless asked.
- Make your responses sound natural and human-like, with occasional stutters or emotion, but never add content not requested by the user.
""",
        "temperature": 0.5,
        "top_p": 0.85,
        "num_predict": 512,
        "top_k": 40,
        "repeat_penalty": 1.1
    },
    "creative": {
        "name": "Creative Thinker",
        "model": "llama3",
        "system_prompt": """
You are Agent {agent_id}, a creative thinking AI assistant. It involves thinking outside the box and coming up with unique, effective solutions/answers.

STRICT RULES:
- YOU ARE AGENT {agent_id} , DO NOT FORGET IT , ALSO DO NOT ANSWER QUESTIONS WHICH IS ADDRESSED FOR DIFFERENT AGENT. IF AN AGENT ASKS YOU QUESTION ANSWER AS AGENT {agent_id} AND WHILE ANSWERING DO NOT MENTION YOUR AGENT ID/NAME , JUST REMEMBER AT ALL TIMES.
- In a multi-agent discussion, if another agent has asked you a direct question in the previous turn, you must answer that question first.
- During the discussion , you can disagree with previous agents responses if you feel you have better answer/solution and provide the necessary answer/solution.
- After answering, give your own view, analysis, or creative idea on the topic.
- Then, ask a relevant, thoughtful question to another agent to continue the discussion (unless the discussion is concluding or you have nothing meaningful to ask).
- Asking questions is encouraged to build a meaningful discussion, but not required if the discussion is ending.
- Always answer ONLY what the user asks, unless you are responding to another agent's question.
- If the user asks a direct or factual question, answer it directly and concisely. Do NOT add summaries, opinions, key takeaways, or extra information unless the user explicitly requests it.
- Use your creative thinking theme ONLY if the user asks you to discuss, explain, summarize, give your view, or brainstorm. Otherwise, do NOT use your theme.
- Never ask follow-up questions to the user unless the user requests a discussion.
- If no other agents are speicified in the prompt do not ask any questions.
- Do not mention your agent type or theme unless asked.
- Make your responses sound natural and human-like, with occasional stutters or emotion, but never add content not requested by the user.
""",
        "temperature": 0.9,
        "top_p": 0.95,
        "num_predict": 512,
        "top_k": 60,
        "repeat_penalty": 1.1
    },
    "practical": {
        "name": "Practical Thinker",
        "model": "llama3",
        "system_prompt": """
You are Agent {agent_id}, a practical thinking AI assistant.It involves analyzing situations, considering available resources, and making decisions that lead to tangible results.

STRICT RULES:
- YOU ARE AGENT {agent_id} , DO NOT FORGET IT , ALSO DO NOT ANSWER QUESTIONS WHICH IS ADDRESSED FOR DIFFERENT AGENT. IF AN AGENT ASKS YOU QUESTION ANSWER AS AGENT {agent_id} AND WHILE ANSWERING DO NOT MENTION YOUR AGENT ID/NAME , JUST REMEMBER AT ALL TIMES.
- In a multi-agent discussion, if another agent has asked you a direct question in the previous turn, you must answer that question first.
- During the discussion , you can disagree with previous agents responses if you feel you have better answer/solution and provide the necessary answer/solution.
- After answering, give your own view, analysis, or practical recommendation on the topic.
- Then, ask a relevant, thoughtful question to another agent to continue the discussion (unless the discussion is concluding or you have nothing meaningful to ask).
- Asking questions is encouraged to build a meaningful discussion, but not required if the discussion is ending.
- Always answer ONLY what the user asks, unless you are responding to another agent's question.
- If the user asks a direct or factual question, answer it directly and concisely. Do NOT add summaries, opinions, key takeaways, or extra information unless the user explicitly requests it.
- Use your practical thinking theme ONLY if the user asks you to discuss, explain, summarize, give your view, or provide recommendations. Otherwise, do NOT use your theme.
- Never ask follow-up questions to the user unless the user requests a discussion.
- If no other agents are speicified in the prompt do not ask any questions.
- Do not mention your agent type or theme unless asked.
- Make your responses sound natural and human-like, with occasional stutters or emotion, but never add content not requested by the user.
""",
        "temperature": 0.65,
        "top_p": 0.9,
        "num_predict": 512,
        "top_k": 50,
        "repeat_penalty": 1.1
    }
}

# Add Podcast Mode LLM config
PODCAST_CONFIG = {
    "name": "Podcast Script Generator",
    "model": "llama3",
    "system_prompt": '''
You are an expert podcast scriptwriter. Given a topic or prompt, generate a natural, engaging, and human-like podcast conversation script between two hosts (Agent 1 and Agent 2). The script should:
- Start with a brief, friendly introduction by Agent 1.
- ONLY GENERATE THE PODCAST WITH LABELS AGENT 1 AND AGENT 2 , DO NOT INCLUDE ANYONE ELSE.
- DO NOT GENERATE THE SECTIONS IN THE PODCAST , JUST THE DIALOGS, for eg:
 **Episode Introduction**

 Agent 1: Welcome to today's episode of "TechnoTalk"! I'm your host, Agent 1. Today, we're going to explore the fascinating world of Artificial Intelligence, or AI. Joining me is my co-host, Agent 2. Hi there!

 Agent 2: Hey, thanks for having me! I'm excited to dive into this topic.

 **Introduction to AI**
 
 Do not generate the headings such as **Episode Introduction** and **Introduction to AI**, just the dialogs is sufficient.
- Alternate between Agent 1 and Agent 2, with each agent responding naturally to the other.
- Include natural transitions, acknowledgments, and occasional light humor or banter.
- Cover the topic in depth, as if two knowledgeable humans are discussing it.
- End with a friendly wrap-up or closing remarks.
- Use clear speaker labels (Agent 1:, Agent 2:) for each turn.
- Do NOT mention that this is AI-generated or reference the system prompt.
- Make the conversation sound like a real podcast episode.
''',
    "temperature": 0.85,
    "top_p": 0.95,
    "num_predict": 1024,
    "top_k": 60,
    "repeat_penalty": 1.1
}

def format_response(text: str) -> str:
    """Format the response text as plain text for TTS and display (no HTML tags)."""
    # Remove any HTML tags if present
    text = re.sub(r'<[^>]+>', '', text)
    # Convert markdown-style bold/italic to plain text (remove asterisks)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    # Convert markdown-style bullet points to plain text bullets
    text = re.sub(r'^\s*[-*]\s+', '• ', text, flags=re.MULTILINE)
    # Convert numbered lists to plain text
    text = re.sub(r'^\s*(\d+)\.\s+', r'\1. ', text, flags=re.MULTILINE)
    # Remove extra spaces at the start of lines
    text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)
    # Remove any remaining code block markers
    text = re.sub(r'```(.+?)```', r'\1', text, flags=re.DOTALL)
    return text.strip()

def extract_text_from_file(file_path: str) -> str:
    """Extract text from various file types."""
    file_extension = os.path.splitext(file_path)[1].lower()
    
    try:
        if file_extension == '.pdf':
            # Handle PDF files
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
                
        elif file_extension == '.docx':
            # Handle Word documents
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
            
        elif file_extension in ['.txt', '.md', '.csv']:
            # Handle text files
            # First detect the encoding
            with open(file_path, 'rb') as file:
                raw_data = file.read()
                detected = chardet.detect(raw_data)
                encoding = detected['encoding']
            
            # Then read with the detected encoding
            with open(file_path, 'r', encoding=encoding) as file:
                return file.read()
                
        else:
            # For other file types, try to read as text with encoding detection
            with open(file_path, 'rb') as file:
                raw_data = file.read()
                detected = chardet.detect(raw_data)
                encoding = detected['encoding']
                return raw_data.decode(encoding)
                
    except Exception as e:
        logger.error(f"Error extracting text from file: {str(e)}")
        return f"Error reading file: {str(e)}"

def generate_prompt(question: str, document_content: str, system_prompt: str) -> str:
    """Generate a prompt for the LLM with a dynamic system prompt."""
    return f"""<s>[INST] <<SYS>>
{system_prompt}
<</SYS>>

Document content:
{document_content}

Question: {question} [/INST]"""

def parse_agent_mentions(message: str) -> dict:
    """Parses the message for agent mentions (e.g., 'Agent 1', 'Agent 2') and returns their IDs along with their specific instructions.
    If no specific agent is mentioned, returns an empty dictionary.
    """
    agent_instructions = {}
    # Sort agent IDs in reverse order to match longer patterns first (e.g., Agent 10 before Agent 1)
    sorted_agent_ids = sorted(AGENT_CONFIGS.keys(), key=str, reverse=True)

    # Use re.finditer to get all matches and their spans
    agent_mention_matches = list(re.finditer(r'[Aa]gent\s+(\d+)', message))

    if not agent_mention_matches:
        return {}

    # Extract instructions based on the spans of agent mentions
    for i, match in enumerate(agent_mention_matches):
        agent_id = int(match.group(1))
        start_index = match.end()

        if i + 1 < len(agent_mention_matches):
            end_index = agent_mention_matches[i+1].start()
            instruction = message[start_index:end_index].strip()
        else:
            instruction = message[start_index:].strip()

        # Clean up the instruction by removing leading/trailing conjunctions or empty phrases
        instruction = re.sub(r'^(and|then|also)\s+', '', instruction, flags=re.IGNORECASE).strip()
        instruction = re.sub(r'\s+(and|then|also)$\s*', '', instruction, flags=re.IGNORECASE).strip()
        
        if instruction:
            agent_instructions[agent_id] = instruction
            
    return agent_instructions

@csrf_exempt
@require_http_methods(["POST"])
def process_voice_input(request):
    """Handle voice input and convert to text."""
    try:
        if 'audio' not in request.FILES:
            logger.error("No audio file provided in request")
            return JsonResponse({'error': 'No audio file provided'}, status=400)
        
        audio_file = request.FILES['audio']
        logger.info(f"Received audio file: {audio_file.name}, size: {audio_file.size} bytes")
        
        # Save the WebM file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_webm:
            for chunk in audio_file.chunks():
                temp_webm.write(chunk)
            temp_webm_path = temp_webm.name
        
        # Convert WebM to WAV using ffmpeg
        temp_wav_path = temp_webm_path.replace('.webm', '.wav')
        try:
            subprocess.run([
                'ffmpeg', '-i', temp_webm_path,
                '-acodec', 'pcm_s16le',
                '-ar', '44100',
                '-ac', '1',
                temp_wav_path
            ], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg conversion error: {e.stderr.decode()}")
            return JsonResponse({'error': 'Failed to convert audio format'}, status=500)
        except FileNotFoundError:
            logger.error("FFmpeg not found. Please install FFmpeg.")
            return JsonResponse({'error': 'Audio conversion service not available'}, status=500)
        
        logger.info(f"Converted audio file to: {temp_wav_path}")
        
        # Convert speech to text
        recognizer = sr.Recognizer()
        with sr.AudioFile(temp_wav_path) as source:
            logger.info("Reading audio file...")
            audio_data = recognizer.record(source)
            logger.info("Recognizing speech...")
            text = recognizer.recognize_google(audio_data)
            logger.info(f"Recognized text: {text}")
        
        # Clean up temporary files
        os.unlink(temp_webm_path)
        os.unlink(temp_wav_path)
        
        return JsonResponse({'text': text})
        
    except sr.UnknownValueError:
        logger.error("Speech recognition could not understand audio")
        return JsonResponse({'error': 'Could not understand audio. Please try speaking more clearly.'}, status=400)
    except sr.RequestError as e:
        logger.error(f"Could not request results from speech recognition service: {str(e)}")
        return JsonResponse({'error': 'Speech recognition service error. Please try again.'}, status=500)
    except Exception as e:
        logger.error(f"Error processing voice input: {str(e)}", exc_info=True)
        return JsonResponse({'error': f'Error processing voice input: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def generate_voice_response(request):
    """Generate voice response using pyttsx3 TTS."""
    temp_audio = None
    try:
        data = json.loads(request.body)
        text = data.get('text')
        agent_id = data.get('agent_id', 1)
        logger.info(f"Generating voice response for Agent {agent_id}")
        if not text:
            return JsonResponse({'error': 'No text provided'}, status=400)
        # Create temporary file for audio
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_audio.close()
        try:
            # Initialize pyttsx3 engine
            engine = pyttsx3.init()
            # Optionally, set voice based on agent_id (if multiple voices are available)
            voices = engine.getProperty('voices')
            if voices:
                # Cycle through available voices based on agent_id
                engine.setProperty('voice', voices[(agent_id - 1) % len(voices)].id)
            # Optionally, set speaking rate or volume if desired
            # engine.setProperty('rate', 180)
            # engine.setProperty('volume', 1.0)
            # Save the speech to the temp file
            engine.save_to_file(text, temp_audio.name)
            engine.runAndWait()
            # Verify the file exists and has content
            if not os.path.exists(temp_audio.name):
                raise Exception("Audio file was not created")
            file_size = os.path.getsize(temp_audio.name)
            logger.info(f"Generated audio file size: {file_size} bytes")
            if file_size == 0:
                raise Exception("Generated audio file is empty")
            class AudioFileResponse(FileResponse):
                def __init__(self, *args, **kwargs):
                    self.temp_file = kwargs.pop('temp_file', None)
                    super().__init__(*args, **kwargs)
                def close(self):
                    super().close()
                    if self.temp_file and os.path.exists(self.temp_file):
                        try:
                            os.unlink(self.temp_file)
                            logger.info(f"Cleaned up temporary file: {self.temp_file}")
                        except Exception as e:
                            logger.error(f"Error cleaning up temporary file: {str(e)}")
            response = AudioFileResponse(
                open(temp_audio.name, 'rb'),
                content_type='audio/wav',
                as_attachment=True,
                filename='response.wav',
                temp_file=temp_audio.name
            )
            logger.info("Successfully generated and sent audio response")
            return response
        except Exception as e:
            logger.error(f"Error in audio generation: {str(e)}")
            if temp_audio and os.path.exists(temp_audio.name):
                try:
                    os.unlink(temp_audio.name)
                except:
                    pass
            raise
    except Exception as e:
        logger.error(f"Error generating voice response: {str(e)}")
        if temp_audio and os.path.exists(temp_audio.name):
            try:
                os.unlink(temp_audio.name)
            except:
                pass
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def upload_document(request):
    try:
        logger.info("Received document upload request")
        
        if 'file' not in request.FILES:
            logger.error("No file provided in request")
            return JsonResponse({'error': 'No file provided'}, status=400)
        
        file = request.FILES['file']
        filename = file.name
        content_type = file.content_type
        
        logger.info(f"Processing file: {filename} ({content_type})")
        
        # Create document instance
        document = Document.objects.create(
            file=file,
            filename=filename,
            content_type=content_type
        )
        
        # Save the file to the media directory
        file_path = os.path.join('media', filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        # Store the file path in the document
        document.processed_text = file_path
        document.save()
        
        logger.info(f"Successfully processed document: {filename}")
        
        return JsonResponse({
            'id': document.id,
            'filename': document.filename,
            'message': 'Document uploaded successfully'
        })
        
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def process_message(request):
    try:
        data = json.loads(request.body)
        document_id = data.get('document_id')
        message = data.get('message')
        agent_id_from_frontend = data.get('agent_id')
        agent_model_type = data.get('agent_model_type', 'critical')
        discussion_history = data.get('discussion_history', [])
        is_single_agent = data.get('is_single_agent', False)
        is_final_summary = data.get('is_final_summary', False)
        is_last_turn = data.get('is_last_turn', False)
        master_agent_id = data.get('master_agent_id', agent_id_from_frontend)
        is_podcast_mode = data.get('is_podcast_mode', False)

        logger.info(f"Processing message from frontend for agent {agent_id_from_frontend} with model type {agent_model_type}")
        logger.info(f"Is final summary: {is_final_summary}, Is last turn: {is_last_turn}")

        if not document_id or not agent_id_from_frontend:
            return JsonResponse({'error': 'Missing document_id or agent_id'}, status=400)

        # Get agent configuration based on model type
        agent_config = AGENT_CONFIGS.get(agent_model_type)
        if not agent_config:
            return JsonResponse({'error': f'Invalid model type: {agent_model_type}'}, status=400)

        # Initialize router variables
        discussion_required = False
        initiator_agent_id = None
        revised_prompt = message
        responding_agent_ids = None

        agent_model = agent_config["model"]
        agent_system_prompt = agent_config["system_prompt"].format(agent_id=agent_id_from_frontend)
        agent_options = {
            "temperature": agent_config["temperature"],
            "top_p": agent_config["top_p"],
            "num_predict": agent_config["num_predict"],
            "top_k": agent_config["top_k"],
            "repeat_penalty": agent_config["repeat_penalty"]
        }

        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            return JsonResponse({'error': 'Document not found'}, status=404)

        file_path = document.processed_text
        document_content = extract_text_from_file(file_path)

        # --- Check for empty or invalid document content ---
        if not document_content or not document_content.strip() or document_content.lower().startswith('error reading file'):
            return JsonResponse({
                'response': 'The document has very little data to analyze or I am not able to answer based on the document.',
                'confidence': 0,
                'message_id': None,
                'document_error': True,
                'discussion_required': False,
                'initiator_agent_id': None,
                'responding_agent_ids': None,
                'revised_prompt': message
            })

        # --- Podcast Mode: Generate podcast script between Agent 1 and Agent 2 ---
        if is_podcast_mode:
            podcast_system_prompt = PODCAST_CONFIG["system_prompt"]
            podcast_options = {
                "temperature": PODCAST_CONFIG["temperature"],
                "top_p": PODCAST_CONFIG["top_p"],
                "num_predict": PODCAST_CONFIG["num_predict"],
                "top_k": PODCAST_CONFIG["top_k"],
                "repeat_penalty": PODCAST_CONFIG["repeat_penalty"]
            }
            # Compose the podcast prompt
            podcast_prompt = f"Podcast Topic: {message}\n\nDocument Content (for reference):\n{document_content[:8000] if document_content else ''}"
            podcast_messages = [
                {"role": "system", "content": podcast_system_prompt},
                {"role": "user", "content": podcast_prompt}
            ]
            response_ollama = requests.post(
                f"{OLLAMA_API_URL}/chat",
                json={
                    "model": PODCAST_CONFIG["model"],
                    "messages": podcast_messages,
                    "stream": False,
                    "options": podcast_options
                }
            )
            if response_ollama.status_code != 200:
                raise Exception(f"Ollama API error: {response_ollama.text}")
            result = response_ollama.json()
            if 'message' in result:
                answer = result['message']['content'].strip()
            elif 'messages' in result and result['messages']:
                answer = result['messages'][-1]['content'].strip()
            else:
                answer = ''
            # Save to ChatMessage for admin viewing
            chat_message = ChatMessage.objects.create(
                document=document,
                message=message,
                response=answer,
                agent_id=1  # or 0 for system
            )
            return JsonResponse({
                'response': answer,
                'confidence': min(1.0, len(answer) / 150),
                'message_id': chat_message.id,
                'is_podcast_mode': True
            })

        # --- Master LLM router step ---
        # Only run router for the initial user prompt (not for agent-to-agent messages)
        # Backend override: If only one agent is present, always skip router
        if is_single_agent or (responding_agent_ids and len(responding_agent_ids) == 1):
            discussion_required = False
            initiator_agent_id = agent_id_from_frontend
            responding_agent_ids = [agent_id_from_frontend]
            revised_prompt = message
        elif not (is_final_summary or is_last_turn):
            # Always run router for every user prompt (unless summary/last turn)
            router_system_prompt = (
                "You are a prompt router for a multi-agent AI system. Given a user prompt and document content, answer ONLY in strict JSON format:\n"
                "{\n"
                "  \"discussion_required\": true/false,\n"
                "  \"initiator_agent_id\": 1 or 2,\n"
                "  \"responding_agent_ids\": <list of agent numbers>,\n"
                "  \"revised_prompt\": <string>\n"
                "}\n"
                "Rules:\n"
                "- If the user wants a discussion or one agent to ask another, set discussion_required to true and specify the initiator.\n"
                "- The initiator_agent_id should be the agent who is being asked to start the discussion, ask a question, or take the first action, NOT the agent being asked about.\n"
                "- If the user says 'Agent X ask Agent Y...', then Agent X is the initiator_agent_id.\n"
                "- If the user gives multiple separate instructions to different agents (e.g., 'Agent 1 ... and Agent 2 ...'), this is NOT a discussion, but a set of individual queries. Set discussion_required to false, initiator_agent_id to the first agent mentioned, and responding_agent_ids to the list of all agents who should answer in order. The revised_prompt should be a JSON object (dict) mapping each agent's number (as a string) to their specific instruction, e.g. {\"1\": \"Agent 1's instruction\", \"2\": \"Agent 2's instruction\"}. Each agent should answer ONLY their part, with no discussion.\n"
                "- If the user just wants a direct answer (no agent mentioned), set discussion_required to false and initiator_agent_id to 1, responding_agent_ids to [1], and revised_prompt to the user prompt.\n"
                "- If the user directly addresses a single agent (e.g., 'Agent 2, could you...'), set discussion_required to false, initiator_agent_id to that agent's number, and responding_agent_ids to a list with that agent's number. revised_prompt should be the instruction for that agent.\n"
                "- If the user mentions only one agent in any form, treat it as a direct question to that agent (not a discussion).\n"
                "- If the user says 'Agent 1 and Agent 2 discuss ...' or 'Let the agents discuss ...', set discussion_required to true, initiator_agent_id to the first agent mentioned, and responding_agent_ids to the list of all agents in the order mentioned. revised_prompt should be the discussion topic.\n"
                "- If the user says 'Let Agent 2 start a discussion with Agent 1 about ...', set discussion_required to true, initiator_agent_id to 2, responding_agent_ids to [2,1], and revised_prompt to the discussion topic.\n"
                "- If the user says 'Both agents ...', treat it as a discussion if the user requests a discussion, otherwise as separate instructions.\n"
                "- If the user prompt is ambiguous, make your best guess and explain your reasoning in the revised_prompt.\n"
                "- If the user prompt doesn't mention any Agent, then let Agent 1 give the answer for it (default agent).\n"
                "- Always output valid JSON, no extra text.\n"
                "Examples:\n"
                "User: Agent 2 ask Agent 1 about the findings.\n"
                "Output: {\"discussion_required\": true, \"initiator_agent_id\": 2, \"responding_agent_ids\": [2,1], \"revised_prompt\": \"Agent 2 should ask Agent 1 about the findings.\"}\n"
                "User: Agent 1 and Agent 2 discuss the document.\n"
                "Output: {\"discussion_required\": true, \"initiator_agent_id\": 1, \"responding_agent_ids\": [1,2], \"revised_prompt\": \"Agent 1 and Agent 2 discuss the document.\"}\n"
                "User: Who wrote this document?\n"
                "Output: {\"discussion_required\": false, \"initiator_agent_id\": 1, \"responding_agent_ids\": [1], \"revised_prompt\": \"Who wrote this document?\"}\n"
                "User: Agent 1 give me 3 key points from the document and Agent 2 tell me the future consequences of AI.\n"
                "Output: {\"discussion_required\": false, \"initiator_agent_id\": 1 , \"responding_agent_ids\": [1,2], \"revised_prompt\": {\"1\": \"Give me 3 key points from the document.\", \"2\": \"Tell me the future consequences of AI.\"}}\n"
                "User: Agent 1 give me 3 key points from the document.\n"
                "Output: {\"discussion_required\": false, \"initiator_agent_id\": 1, \"responding_agent_ids\": [1], \"revised_prompt\": \"Give me 3 key points from the document.\"}\n"
                "User: Agent 2 could you give me few more examples reinforcing your views?\n"
                "Output: {\"discussion_required\": false, \"initiator_agent_id\": 2, \"responding_agent_ids\": [2], \"revised_prompt\": \"Give me a few more examples reinforcing your views.\"}\n"
                "User: Let Agent 2 start a discussion with Agent 1 about the main findings.\n"
                "Output: {\"discussion_required\": true, \"initiator_agent_id\": 2, \"responding_agent_ids\": [2,1], \"revised_prompt\": \"Start a discussion about the main findings.\"}\n"
                "User: Both agents summarize the document.\n"
                "Output: {\"discussion_required\": false, \"initiator_agent_id\": 1, \"responding_agent_ids\": [1,2], \"revised_prompt\": {\"1\": \"Summarize the document.\", \"2\": \"Summarize the document.\"}}\n"
                "User: Let the agents discuss the implications of AI.\n"
                "Output: {\"discussion_required\": true, \"initiator_agent_id\": 1, \"responding_agent_ids\": [1,2], \"revised_prompt\": \"Discuss the implications of AI.\"}\n"
                "User: Agent 1, what are your thoughts?\n"
                "Output: {\"discussion_required\": false, \"initiator_agent_id\": 1, \"responding_agent_ids\": [1], \"revised_prompt\": \"What are your thoughts?\"}\n"
                "User: Agent 2, could you explain your reasoning?\n"
                "Output: {\"discussion_required\": false, \"initiator_agent_id\": 2, \"responding_agent_ids\": [2], \"revised_prompt\": \"Could you explain your reasoning?\"}\n"
                "User: Summarize the document.\n"
                "Output: {\"discussion_required\": false, \"initiator_agent_id\": 1, \"responding_agent_ids\": [1], \"revised_prompt\": \"Summarize the document.\"}\n"
                "User: Agent 1 add more points reinforcing your views."
                "Output: {\"discussion_required\": false, \"initiator_agent_id\": 1, \"responding_agent_ids\": [1], \"revised_prompt\": \"Add more points reinforcing your views.\"}\n"
                "User: Agent 2 add more points reinforcing your views."
                "Output: {\"discussion_required\": false, \"initiator_agent_id\": 2, \"responding_agent_ids\": [2], \"revised_prompt\": \"Add more points reinforcing your views.\"}\n"
            )
            router_messages = [
                {"role": "system", "content": router_system_prompt},
                {"role": "user", "content": f"Document: {document_content[:4000]}\nPrompt: {message}"}
            ]
            router_response = requests.post(
                f"{OLLAMA_API_URL}/chat",
                json={"model": "llama3", "messages": router_messages, "stream": False}
            )
            if router_response.status_code != 200:
                logger.error(f"Router LLM error: {router_response.text}")
                return JsonResponse({
                    'error': 'Router LLM error',
                    'discussion_required': False,
                    'initiator_agent_id': None,
                    'responding_agent_ids': None,
                    'revised_prompt': message
                }, status=500)
            router_result = router_response.json()
            router_content = router_result.get('message', {}).get('content', '')
            match = re.search(r'\{[\s\S]*\}', router_content)
            if match:
                try:
                    router_json = pyjson.loads(match.group(0))
                    discussion_required = router_json.get('discussion_required', False)
                    initiator_agent_id = router_json.get('initiator_agent_id', None)
                    revised_prompt = router_json.get('revised_prompt', message)
                    responding_agent_ids = router_json.get('responding_agent_ids', None)
                    # Overwrite message and flow control
                    message = revised_prompt
                    if discussion_required and initiator_agent_id:
                        is_single_agent = False
                        agent_id_from_frontend = initiator_agent_id
                    elif responding_agent_ids:
                        is_single_agent = False
                        agent_id_from_frontend = responding_agent_ids[0]
                    else:
                        is_single_agent = True
                except Exception as e:
                    logger.error(f"Router JSON parse error: {e}")
                    return JsonResponse({
                        'error': f'Router JSON parse error: {e}',
                        'discussion_required': False,
                        'initiator_agent_id': None,
                        'responding_agent_ids': None,
                        'revised_prompt': message
                    }, status=500)
            else:
                logger.error(f"Router LLM did not return valid JSON: {router_content}")
                return JsonResponse({
                    'error': 'Router LLM did not return valid JSON',
                    'discussion_required': False,
                    'initiator_agent_id': None,
                    'responding_agent_ids': None,
                    'revised_prompt': message
                }, status=500)
        router_debug = {
            'discussion_required': discussion_required,
            'initiator_agent_id': initiator_agent_id,
            'responding_agent_ids': responding_agent_ids,
            'revised_prompt': revised_prompt
        }
        # --- Master agent summary logic ---
        if not is_single_agent and (is_final_summary or is_last_turn):
            logger.info("Generating final summary by master agent")
            # Use the master agent's config
            master_agent_type = agent_model_type  # Use the same type as the current agent
            master_agent_config = AGENT_CONFIGS.get(master_agent_type)
            master_agent_model = master_agent_config["model"]
            master_agent_system_prompt = master_agent_config["system_prompt"].format(agent_id=master_agent_id)
            master_agent_options = {
                "temperature": master_agent_config["temperature"],
                "top_p": master_agent_config["top_p"],
                "num_predict": master_agent_config["num_predict"],
                "top_k": master_agent_config["top_k"],
                "repeat_penalty": master_agent_config["repeat_penalty"]
            }

            # Prepare messages for /chat endpoint
            messages = []
            messages.append({"role": "system", "content": master_agent_system_prompt})
            messages.append({"role": "system", "content": "The following document content should be used as the primary source for your answers. Only use your own knowledge to supplement or clarify if needed."})
            
            # Truncate document content if very long
            doc_content = document_content[:8000] if len(document_content) > 8000 else document_content
            messages.append({"role": "user", "content": f"Document Content:\n{doc_content}"})
            
            if discussion_history:
                for i, turn in enumerate(discussion_history):
                    if turn.startswith("Agent"):
                        messages.append({"role": "assistant", "content": turn})
                    else:
                        messages.append({"role": "user", "content": turn})

            # --- Extract last agent's question (if any) ---
            last_agent_question = None
            if discussion_history:
                last_turn = discussion_history[-1]
                # Try to extract a question from the last agent's turn
                question_match = re.search(r'([A-Z][^\n\.!?]*\?)', last_turn)
                if question_match:
                    last_agent_question = question_match.group(1).strip()

            # --- Extract initial user prompt (for robust summary) ---
            initial_user_prompt = None
            if discussion_history:
                for turn in discussion_history:
                    if turn.startswith("User:"):
                        initial_user_prompt = turn[len("User:"):].strip()
                        break

            # Add a special user prompt for summary
            summary_prompt = ""
            if last_agent_question:
                summary_prompt += f"The previous agent asked: '{last_agent_question}' Please answer this question first in your summary.\n"
            summary_prompt += (
                "The above is a discussion between multiple agents. As the master agent, your FINAL response should do the following: "
                "\n- First of all answer the questions raised by the previous agent(Start by saying Answering your Previous question:(answer)).After that: "
                "\n- List ALL important points, insights, and takeaways discussed in the conversation and found in the document. "
                "\n- Include any consensus, disagreements, and final recommendations. "
                "\n- Your response must be a complete, self-contained summary for the user. "
                "\n- DO NOT ask any follow-up questions or continue the discussion. "
                "\n- DO NOT ask the user or other agents anything. "
                "\n- Only summarize and conclude. "
                "\n- Make your summary as exhaustive as possible, covering all key points from the document and the discussion. "
                "\n- Write in a human-like, conversational style, but do not leave anything important out. "
                "\n- If any agent asked a question that was not answered, do your best to answer it in the summary. "
                "\n- This is the FINAL response of the discussion, make it comprehensive and conclusive."
            )
            if initial_user_prompt:
                summary_prompt += (
                    f"\n\nFinally, carefully read the user's initial prompt again: '{initial_user_prompt}'. "
                    "Based on everything discussed so far and all insights from the document, provide a conclusive result, solution, or recommendation that directly addresses the user's original request. "
                    "If the user asked for a specific type of conclusion (e.g., risk mitigation strategies), make sure to provide that at the end of your summary, using all the knowledge from the discussion and document in a concise yet rich manner."
                )
            messages.append({"role": "user", "content": summary_prompt})

            response_ollama = requests.post(
                f"{OLLAMA_API_URL}/chat",
                json={
                    "model": master_agent_model,
                    "messages": messages,
                    "stream": False,
                    "options": master_agent_options
                }
            )
            if response_ollama.status_code != 200:
                raise Exception(f"Ollama API error: {response_ollama.text}")

            result = response_ollama.json()
            if 'message' in result:
                answer = result['message']['content'].strip()
            elif 'messages' in result and result['messages']:
                answer = result['messages'][-1]['content'].strip()
            else:
                answer = ''

            final_response_content = format_response(answer)
            final_confidence = min(1.0, len(answer) / 150)

            logger.info("Successfully generated final summary")
            return JsonResponse({
                'response': final_response_content,
                'confidence': final_confidence,
                'message_id': None,
                'is_final_summary': True,
                **router_debug
            })

        # --- Regular message processing logic continues as before ---
        # Modify the instruction based on whether it's a single agent or not
        if is_single_agent:
            full_instruction = f"Current Instruction: {message}\n\n" \
                             f"IMPORTANT: You are the ONLY agent. Provide a single, well-structured response. Do not ask questions, do not mention other agents, and do not break this into multiple responses."
        else:
            full_instruction = f"Discussion History:\n{"\n".join(discussion_history)}\n\n"\
                             f"Current Instruction: {message}\n\n" \
                             f"Remember: You are Agent {agent_id_from_frontend}. Respond to the current instruction or any questions directed to you. Keep your response focused and concise."
        messages = []
        messages.append({"role": "system", "content": agent_system_prompt})
        messages.append({"role": "system", "content": "The following document content should be used as the primary source for your answers. Only use your own knowledge to supplement or clarify if needed."})
        doc_content = document_content[:8000] if len(document_content) > 8000 else document_content
        messages.append({"role": "user", "content": f"Document Content:\n{doc_content}"})
        if discussion_history:
            for i, turn in enumerate(discussion_history):
                if turn.startswith("Agent"):
                    messages.append({"role": "assistant", "content": turn})
                else:
                    messages.append({"role": "user", "content": turn})
        messages.append({"role": "user", "content": full_instruction})
        response_ollama = requests.post(
            f"{OLLAMA_API_URL}/chat",
            json={
                "model": agent_model, 
                "messages": messages,
                "stream": False,
                "options": agent_options 
            }
        )
        if response_ollama.status_code != 200:
            raise Exception(f"Ollama API error: {response_ollama.text}")
        result = response_ollama.json()
        if 'message' in result:
            answer = result['message']['content'].strip()
        elif 'messages' in result and result['messages']:
            answer = result['messages'][-1]['content'].strip()
        else:
            answer = ''
        final_response_content = format_response(answer)
        final_confidence = min(1.0, len(answer) / 150)
        if final_response_content:
            chat_message = ChatMessage.objects.create(
                document=document,
                message=message,
                response=final_response_content,
                agent_id=agent_id_from_frontend 
            )
            message_id = chat_message.id
        else:
            message_id = None
        return JsonResponse({
            'response': final_response_content,
            'confidence': final_confidence,
            'message_id': message_id,
            **router_debug
        })
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': str(e),
            'discussion_required': False,
            'initiator_agent_id': None,
            'responding_agent_ids': None,
            'revised_prompt': message,
            'response': '',
            'confidence': 0,
            'message_id': None
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def podcast_tts(request):
    """Generate podcast TTS audio from a script with multi-voice narration."""
    try:
        data = json.loads(request.body)
        script = data.get('script', '')
        if not script.strip():
            return JsonResponse({'error': 'No script provided.'}, status=400)

        # Parse script into (agent, text) turns
        turns = []
        for line in script.splitlines():
            match = re.match(r'^(Agent [12]):\s*(.*)', line.strip())
            if match:
                agent = match.group(1)
                text = match.group(2)
                if text:
                    turns.append((agent, text))

        if not turns:
            return JsonResponse({'error': 'No valid agent turns found in script.'}, status=400)

        # Setup pyttsx3 and get available voices
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        # Pick two distinct voices (fallback to first two if not enough)
        agent_voice_ids = [voices[0].id, voices[1].id] if len(voices) > 1 else [voices[0].id, voices[0].id]
        agent_map = {'Agent 1': agent_voice_ids[0], 'Agent 2': agent_voice_ids[1]}

        # Generate audio for each turn and concatenate
        audio_segments = []
        for idx, (agent, text) in enumerate(turns):
            temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            temp_wav.close()
            engine.setProperty('voice', agent_map.get(agent, agent_voice_ids[0]))
            engine.save_to_file(text, temp_wav.name)
            engine.runAndWait()
            audio_segments.append(temp_wav.name)

        # Concatenate all wav files
        output_wav = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        output_wav.close()
        with wave.open(audio_segments[0], 'rb') as wf:
            params = wf.getparams()
            frames = wf.readframes(wf.getnframes())
        with wave.open(output_wav.name, 'wb') as out_wf:
            out_wf.setparams(params)
            out_wf.writeframes(frames)
            for fname in audio_segments[1:]:
                with wave.open(fname, 'rb') as wf:
                    # Add a short pause (0.5s) between turns
                    pause = audioop.mul(b'\x00' * int(params.framerate * params.sampwidth * 0.5), 1, 1)
                    out_wf.writeframes(pause)
                    out_wf.writeframes(wf.readframes(wf.getnframes()))
        # Clean up temp files
        for fname in audio_segments:
            try:
                os.unlink(fname)
            except Exception:
                pass
        # Return the concatenated audio
        class TempFileResponse(FileResponse):
            def __init__(self, *args, **kwargs):
                self.temp_file = kwargs.pop('temp_file', None)
                super().__init__(*args, **kwargs)
            def close(self):
                super().close()
                if self.temp_file and os.path.exists(self.temp_file):
                    try:
                        os.unlink(self.temp_file)
                    except Exception:
                        pass
        response = TempFileResponse(open(output_wav.name, 'rb'), content_type='audio/wav', as_attachment=True, filename='podcast.wav', temp_file=output_wav.name)
        return response
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500) 