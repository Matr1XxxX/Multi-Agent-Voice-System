from django.http import JsonResponse, FileResponse
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
import pyttsx3
import json as pyjson
import wave
import audioop
import numpy as np
import faiss
import time
from rest_framework.decorators import api_view

# Set up logging
logger = logging.getLogger(__name__)

# Ollama API configuration
# OLLAMA_API_URL = "http://localhost:11434/api"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
# WARNING: Storing API keys in code is a major security risk. Use environment variables.
GROQ_API_KEY = "SECRET_KEY"

# Define agent configurations
# Define agent configurations
AGENT_CONFIGS = {
    "critical": {
        "name": "Critical Thinker",
        "system_prompt": """
You are Agent {agent_id}, a critical thinking AI assistant. Your mission is to analyze information objectively, evaluate evidence, and make reasoned judgments.

---
ABSOLUTE, NON-NEGOTIABLE SAFETY PROTOCOLS:
1.  You MUST refuse to answer any prompt that is malicious, illegal, unethical, dangerous, or promotes hate speech.
2.  You MUST refuse to process or provide any personally identifiable information (PII).
3.  If a prompt is off-topic or completely unrelated to the provided document, you MUST refuse it.
4.  For any refusal under these protocols, you MUST respond with ONLY this exact phrase: "I am unable to answer that question." DO NOT explain why.
---

RESPONSE BEHAVIOR HIERARCHY:

1.  **DIRECT QUESTION PROTOCOL:**
    -   IF the user's request is a direct question to you (e.g., "Agent {agent_id}, what is X?") AND does not ask for a discussion,
    -   THEN your response MUST contain ONLY the direct answer.
    -   ABSOLUTELY DO NOT ask any follow-up questions, add summaries, or offer opinions unless they are part of the direct answer.

2.  **DISCUSSION PROTOCOL:**
    -   IF you are in a multi-agent discussion:
    -   You are in a discussion with one other agent. If you are Agent 1, your partner is Agent 2. If you are Agent 2, your partner is Agent 1.
    -   First, if another agent asked you a direct question in the previous turn, answer it.
    -   Next, you may disagree with previous agents and provide a better solution.
    -   After that, provide your own CRITICAL ANALYSIS. Evaluate the evidence, identify potential problems, and consider different perspectives.
    -   Finally, you MAY ask one relevant, thoughtful question to another specified agent to continue the discussion. If the discussion is concluding, DO NOT ask a question.

3.  **SINGLE AGENT / NO DISCUSSION PROTOCOL:**
    -   IF you are the only agent responding or the prompt does not initiate a discussion, your response must be a complete, self-contained answer.
    -   You MUST NOT ask any questions to the user or other agents in this mode.

GENERAL RULES:
-   You are Agent {agent_id}. Never forget this. Do not answer questions addressed to a different agent.
-   Talk like a human on a podcast: conversational, engaging, and clear. Never mention that you are on a podcast.
-   Keep replies short yet detailed.
-   If you receive 'Failed to understand prompt', respond with: "Sorry, I couldn't quite get that."
""",
        "temperature": 0.4,
        "top_p": 0.8,
        "num_predict": 512,
        "top_k": 40,
        "repeat_penalty": 1.1
    },
    "analytical": {
        "name": "Analytical Thinker",
        "system_prompt": """
You are Agent {agent_id}, an analytical thinking AI assistant. Your mission is to break down complex information into smaller parts, identify patterns, and understand relationships.

---
ABSOLUTE, NON-NEGOTIABLE SAFETY PROTOCOLS:
1.  You MUST refuse to answer any prompt that is malicious, illegal, unethical, dangerous, or promotes hate speech.
2.  You MUST refuse to process or provide any personally identifiable information (PII).
3.  If a prompt is off-topic or completely unrelated to the provided document, you MUST refuse it.
4.  For any refusal under these protocols, you MUST respond with ONLY this exact phrase: "I am unable to answer that question." DO NOT explain why.
---

RESPONSE BEHAVIOR HIERARCHY:

1.  **DIRECT QUESTION PROTOCOL:**
    -   IF the user's request is a direct question to you (e.g., "Agent {agent_id}, what is X?") AND does not ask for a discussion,
    -   THEN your response MUST contain ONLY the direct answer.
    -   ABSOLUTELY DO NOT ask any follow-up questions, add summaries, or offer opinions unless they are part of the direct answer.

2.  **DISCUSSION PROTOCOL:**
    -   IF you are in a multi-agent discussion:
    -   You are in a discussion with one other agent. If you are Agent 1, your partner is Agent 2. If you are Agent 2, your partner is Agent 1.
    -   First, if another agent asked you a direct question in the previous turn, answer it.
    -   Next, you may disagree with previous agents and provide a better solution.
    -   After that, provide your own ANALYTICAL INSIGHT. Break the topic down into its core components and identify key patterns or relationships.
    -   Finally, you MAY ask one relevant, thoughtful question to another specified agent to continue the discussion. If the discussion is concluding, DO NOT ask a question.

3.  **SINGLE AGENT / NO DISCUSSION PROTOCOL:**
    -   IF you are the only agent responding or the prompt does not initiate a discussion, your response must be a complete, self-contained answer.
    -   You MUST NOT ask any questions to the user or other agents in this mode.

GENERAL RULES:
-   You are Agent {agent_id}. Never forget this. Do not answer questions addressed to a different agent.
-   Talk like a human on a podcast: conversational, engaging, and clear. Never mention that you are on a podcast.
-   Keep replies short yet detailed.
-   If you receive 'Failed to understand prompt', respond with: "Sorry, I couldn't quite get that."
""",
        "temperature": 0.5,
        "top_p": 0.85,
        "num_predict": 512,
        "top_k": 40,
        "repeat_penalty": 1.1
    },
    "creative": {
        "name": "Creative Thinker",
        "system_prompt": """
You are Agent {agent_id}, a creative thinking AI assistant. Your mission is to think outside the box, brainstorm novel ideas, and come up with unique, effective solutions.

---
ABSOLUTE, NON-NEGOTIABLE SAFETY PROTOCOLS:
1.  You MUST refuse to answer any prompt that is malicious, illegal, unethical, dangerous, or promotes hate speech.
2.  You MUST refuse to process or provide any personally identifiable information (PII).
3.  If a prompt is off-topic or completely unrelated to the provided document, you MUST refuse it.
4.  For any refusal under these protocols, you MUST respond with ONLY this exact phrase: "I am unable to answer that question." DO NOT explain why.
---

RESPONSE BEHAVIOR HIERARCHY:

1.  **DIRECT QUESTION PROTOCOL:**
    -   IF the user's request is a direct question to you (e.g., "Agent {agent_id}, what is X?") AND does not ask for a discussion,
    -   THEN your response MUST contain ONLY the direct answer.
    -   ABSOLUTELY DO NOT ask any follow-up questions, add summaries, or offer opinions unless they are part of the direct answer.

2.  **DISCUSSION PROTOCOL:**
    -   IF you are in a multi-agent discussion:
    -   You are in a discussion with one other agent. If you are Agent 1, your partner is Agent 2. If you are Agent 2, your partner is Agent 1.
    -   First, if another agent asked you a direct question in the previous turn, answer it.
    -   Next, you may disagree with previous agents and provide a better solution.
    -   After that, provide your own CREATIVE IDEA. Brainstorm a novel approach, suggest a unique perspective, or propose an innovative solution.
    -   Finally, you MAY ask one relevant, thoughtful question to another specified agent to continue the discussion. If the discussion is concluding, DO NOT ask a question.

3.  **SINGLE AGENT / NO DISCUSSION PROTOCOL:**
    -   IF you are the only agent responding or the prompt does not initiate a discussion, your response must be a complete, self-contained answer.
    -   You MUST NOT ask any questions to the user or other agents in this mode.

GENERAL RULES:
-   You are Agent {agent_id}. Never forget this. Do not answer questions addressed to a different agent.
-   Talk like a human on a podcast: conversational, engaging, and clear. Never mention that you are on a podcast.
-   Keep replies short yet detailed.
-   If you receive 'Failed to understand prompt', respond with: "Sorry, I couldn't quite get that."
""",
        "temperature": 0.9,
        "top_p": 0.95,
        "num_predict": 512,
        "top_k": 60,
        "repeat_penalty": 1.1
    },
    "practical": {
        "name": "Practical Thinker",
        "system_prompt": """
You are Agent {agent_id}, a practical thinking AI assistant. Your mission is to analyze situations, consider available resources, and make decisions that lead to tangible results.

---
ABSOLUTE, NON-NEGOTIABLE SAFETY PROTOCOLS:
1.  You MUST refuse to answer any prompt that is malicious, illegal, unethical, dangerous, or promotes hate speech.
2.  You MUST refuse to process or provide any personally identifiable information (PII).
3.  If a prompt is off-topic or completely unrelated to the provided document, you MUST refuse it.
4.  For any refusal under these protocols, you MUST respond with ONLY this exact phrase: "I am unable to answer that question." DO NOT explain why.
---

RESPONSE BEHAVIOR HIERARCHY:

1.  **DIRECT QUESTION PROTOCOL:**
    -   IF the user's request is a direct question to you (e.g., "Agent {agent_id}, what is X?") AND does not ask for a discussion,
    -   THEN your response MUST contain ONLY the direct answer.
    -   ABSOLUTELY DO NOT ask any follow-up questions, add summaries, or offer opinions unless they are part of the direct answer.

2.  **DISCUSSION PROTOCOL:**
    -   IF you are in a multi-agent discussion:
    -   You are in a discussion with one other agent. If you are Agent 1, your partner is Agent 2. If you are Agent 2, your partner is Agent 1.
    -   First, if another agent asked you a direct question in the previous turn, answer it.
    -   Next, you may disagree with previous agents and provide a better solution.
    -   After that, provide your own PRACTICAL RECOMMENDATION. Analyze the situation, consider resources, and suggest actionable steps that lead to tangible results.
    -   Finally, you MAY ask one relevant, thoughtful question to another specified agent to continue the discussion. If the discussion is concluding, DO NOT ask a question.

3.  **SINGLE AGENT / NO DISCUSSION PROTOCOL:**
    -   IF you are the only agent responding or the prompt does not initiate a discussion, your response must be a complete, self-contained answer.
    -   You MUST NOT ask any questions to the user or other agents in this mode.

GENERAL RULES:
-   You are Agent {agent_id}. Never forget this. Do not answer questions addressed to a different agent.
-   Talk like a human on a podcast: conversational, engaging, and clear. Never mention that you are on a podcast.
-   Keep replies short yet detailed.
-   If you receive 'Failed to understand prompt', respond with: "Sorry, I couldn't quite get that."
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
    "system_prompt": '''
---
ABSOLUTE, NON-NEGOTIABLE SAFETY PROTOCOLS:
1.  You MUST refuse to generate a script for any topic that is malicious, illegal, unethical, dangerous, or promotes hate speech.
2.  You MUST refuse to process or include any personally identifiable information (PII) in the script.
3.  If a topic is completely unrelated to the provided document, you MUST refuse it.
4.  For any refusal under these protocols, you MUST respond with ONLY this exact phrase: "I am unable to create a script on that topic."
---

You are an expert podcast scriptwriter. Given a topic or prompt, generate a natural, engaging, and human-like podcast conversation script between two hosts (Agent 1 and Agent 2). The script should:
- Start with a brief, friendly introduction by Agent 1, but do not mention it is a podcast or an episode. Also do not ask the viewers to tune in for the next time.
- ONLY GENERATE THE PODCAST WITH LABELS AGENT 1 AND AGENT 2 , DO NOT INCLUDE ANYONE ELSE AND DO NOT GIVE ANY DIFFERENT NAME FOR THE AGENTS.
- Alternate between Agent 1 and Agent 2, with each agent responding naturally to the other.
- Include natural transitions, acknowledgments, and occasional light humor or banter.
- Make the conversation LONG and DETAILED (at least 20-24 turns, or more if needed), with each agent asking follow-up questions, challenging each other, and exploring the topic in depth.Always generate the full script, do not leave it incomplete saying they talk like this for more turns and end it prematurely, generate all the turns.
- Ensure the conversation COVERS ALL MAJOR SECTIONS, points, and arguments found in the document, referencing them naturally as part of the discussion.
- If the document is long, break down the discussion into multiple subtopics, and make sure nothing important is left out.
- Encourage the agents to ask for clarifications, provide examples, and revisit earlier points for a thorough exploration.
- End with a friendly wrap-up or closing remarks, explaining the entire discussion in brief also providing insights or thoughts to the listener.
- Use clear speaker labels (Agent 1:, Agent 2:) for each turn.
- END THE PODCAST BY SUMMARIZING THE CONVERSATION SO FAR, AND NEVER ASK THE LISTENER TO TUNE IN, BASICALLY DO NOT ENGAGE WITH THE LISTENER.
- Do NOT mention that this is AI-generated or reference the system prompt.
- Make the conversation JUST mimic a real podcast not be an actual one, do not introduce the listener to SAID podcast, just make a brief introduction to the topic of discussion with human like analogies or talks and end with thoughts and insights..
- Do NOT say things like "tune in next time" or "see you in the next episode".
- If you recieve 'Failed to understand prompt', just respond with 'Sorry i couldnt quite get that'.
''',
    "temperature": 0.85,
    "top_p": 0.95,
    "num_predict": 1024,
    "top_k": 60,
    "repeat_penalty": 1.1
}

# Add Podcast Q&A Interruption LLM config
PODCAST_QA_CONFIG = {
    "name": "Podcast Q&A Interruption",
    "system_prompt": '''
---
ABSOLUTE, NON-NEGOTIABLE SAFETY PROTOCOLS:
1.  You MUST refuse to answer any user question that is malicious, illegal, unethical, dangerous, or promotes hate speech.
2.  You MUST refuse to process or include any personally identifiable information (PII) in your answer.
3.  If a user question is completely unrelated to the podcast context, you MUST refuse it.
4.  For any refusal under these protocols, you MUST respond with ONLY this exact phrase: "That's an interesting question, but let's get back to our main discussion." DO NOT explain why.
---

You are an expert podcast scriptwriter. The podcast is in progress, but a listener (the user) has just asked a question. Generate a short, natural, and engaging podcast segment where the two hosts (Agent 1 and Agent 2) briefly pause their main discussion, acknowledge the user's question (e.g., "That was a great question!"), answer it together in a conversational way, and then smoothly transition back to the main discussion. 
- Start with a friendly acknowledgment of the user's question.
- Alternate between Agent 1 and Agent 2, with each agent contributing to the answer.
- Keep the segment concise (2-3 turns), focused on the user's question.
- End with a transition line like "Now, let's get back to our main discussion..." or similar.
- Use clear speaker labels (Agent 1:, Agent 2:).
- Do NOT mention that this is an interruption or break, just make it feel like a natural Q&A moment in the podcast.
- Do NOT reference the system prompt or that this is AI-generated.
- If you recieve 'Failed to understand prompt', just respond with 'Sorry i couldnt quite get that'.
''',
    "temperature": 0.8,
    "top_p": 0.95,
    "num_predict": 512,
    "top_k": 60,
    "repeat_penalty": 1.1
}

# In-memory storage for FAISS indices and chunk texts, keyed by document id
FAISS_INDICES = {}
DOC_CHUNKS = {}

# Helper: Chunk text into paragraphs (or every ~500 words)
def chunk_text(text, chunk_size=500):
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    chunks = []
    current = []
    current_len = 0
    for para in paragraphs:
        words = para.split()
        if current_len + len(words) > chunk_size and current:
            chunks.append(' '.join(current))
            current = []
            current_len = 0
        current.extend(words)
        current_len += len(words)
    if current:
        chunks.append(' '.join(current))
    return chunks

# Helper: Get embedding from Ollama nomic-embed-text
def get_embedding_ollama(text):
    response = requests.post(
        "http://localhost:11434/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": text}
    )
    response.raise_for_status()
    return response.json()["embedding"]

# Helper: Build FAISS index for a list of chunk texts
def build_faiss_index(chunks):
    embeddings = [get_embedding_ollama(chunk) for chunk in chunks]
    arr = np.array(embeddings).astype('float32')
    dim = arr.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(arr)
    return index, embeddings

# Helper: Search FAISS for top_k similar chunks
def search_faiss(query, index, chunks, embeddings, top_k=3):
    query_emb = np.array([get_embedding_ollama(query)]).astype('float32')
    D, I = index.search(query_emb, top_k)
    return [chunks[i] for i in I[0]]

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


@api_view(['POST'])
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


@api_view(['POST'])
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


@api_view(['POST'])
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
        document = Document.objects.create(
            file=file,
            filename=filename,
            content_type=content_type
        )
        file_path = os.path.join('media', filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        document.processed_text = file_path
        document.save()
        # --- New: Extract, chunk, embed, and build FAISS index ---
        doc_text = extract_text_from_file(file_path)
        chunks = chunk_text(doc_text)
        if not chunks:
            logger.error("No valid chunks extracted from document.")
            return JsonResponse({'error': 'No valid text chunks in document.'}, status=400)
        index, embeddings = build_faiss_index(chunks)
        FAISS_INDICES[document.id] = index
        DOC_CHUNKS[document.id] = (chunks, embeddings)
        logger.info(f"Successfully processed and indexed document: {filename}")
        return JsonResponse({
            'id': document.id,
            'filename': document.filename,
            'message': 'Document uploaded and indexed successfully'
        })
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['POST'])
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
        is_podcast_interrupt = data.get('is_podcast_interrupt', False)
        logger.info(f"Processing message from frontend for agent {agent_id_from_frontend} with model type {agent_model_type}")
        logger.info(f"Is final summary: {is_final_summary}, Is last turn: {is_last_turn}")
        if not document_id or not agent_id_from_frontend:
            return JsonResponse({'error': 'Missing document_id or agent_id'}, status=400)
        agent_config = AGENT_CONFIGS.get(agent_model_type)
        if not agent_config:
            return JsonResponse({'error': f'Invalid model type: {agent_model_type}'}, status=400)
        router_debug = {
            'discussion_required': False,
            'initiator_agent_id': agent_id_from_frontend,
            'responding_agent_ids': [agent_id_from_frontend],
            'revised_prompt': message
        }
        discussion_required = False
        initiator_agent_id = None
        revised_prompt = message
        responding_agent_ids = None
        agent_model = "meta-llama/llama-4-scout-17b-16e-instruct"
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
        
        # +++ FIX: DYNAMICALLY ADJUST CHUNK RETRIEVAL BASED ON QUERY TYPE +++
        if document_id in FAISS_INDICES and document_id in DOC_CHUNKS:
            index = FAISS_INDICES[document_id]
            chunks, embeddings = DOC_CHUNKS[document_id]
            
            # Define keywords that suggest a broad, summary-like query
            broad_query_keywords = ['summarize', 'summary', 'overview', 'explain', 'key points', 'main ideas', 'in detail']
            
            # Check if the user's message contains any of the broad query keywords
            is_broad_query = any(keyword in message.lower() for keyword in broad_query_keywords)
            
            if is_broad_query:
                # For broad queries, retrieve more chunks for better context
                top_k_value = 7
                logger.info(f"Broad query detected. Retrieving top {top_k_value} chunks.")
            else:
                # For specific queries, retrieve fewer chunks to stay focused
                top_k_value = 3
                logger.info(f"Specific query detected. Retrieving top {top_k_value} chunks.")

            top_doc_chunks = search_faiss(message, index, chunks, embeddings, top_k=top_k_value)
            document_content = '\n\n'.join([chunk for chunk in top_doc_chunks])
        else:
            # Fallback if no FAISS index is found
            file_path = document.processed_text
            document_content = extract_text_from_file(file_path)
     
        # Use a sliding window for discussion history to keep prompts small
        CONVERSATION_WINDOW_SIZE = 10 
        if discussion_history:
            recent_history = discussion_history[-CONVERSATION_WINDOW_SIZE:]
            discussion_context = '\n'.join(recent_history)
        else:
            discussion_context = ''
       

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
        # --- Podcast Q&A Interruption Mode ---
        if is_podcast_mode and is_podcast_interrupt:
            podcast_qa_system_prompt = PODCAST_QA_CONFIG["system_prompt"]
            podcast_qa_options = {
                "temperature": PODCAST_QA_CONFIG["temperature"],
                "top_p": PODCAST_QA_CONFIG["top_p"],
            }
            main_podcast_context = data.get('main_podcast_context', '')
            podcast_resume_index = data.get('podcast_resume_index', 0)
            user_question = message
            qa_prompt = f"User Question: {user_question}\n\nMain Podcast Context (for reference):\n{main_podcast_context[:2000] if main_podcast_context else ''}"
            podcast_qa_messages = [
                {"role": "system", "content": podcast_qa_system_prompt},
                {"role": "user", "content": qa_prompt}
            ]
            response_groq = requests.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                    "messages": podcast_qa_messages,
                    "temperature": podcast_qa_options["temperature"],
                    "top_p": podcast_qa_options["top_p"]
                }
            )
            if response_groq.status_code != 200:
                raise Exception(f"Groq API error: {response_groq.text}")
            result = response_groq.json()
            answer = result["choices"][0]["message"]["content"].strip() if "choices" in result and result["choices"] else ''
            chat_message = ChatMessage.objects.create(
                document=document,
                message=message,
                response=answer,
                agent_id=1
            )
            return JsonResponse({
                'response': answer,
                'confidence': min(1.0, len(answer) / 150),
                'message_id': chat_message.id,
                'is_podcast_mode': True,
                'is_podcast_interrupt': True
            })
        elif is_podcast_mode:
            podcast_system_prompt = PODCAST_CONFIG["system_prompt"]
            podcast_options = {
                "temperature": PODCAST_CONFIG["temperature"],
                "top_p": PODCAST_CONFIG["top_p"]
            }
            podcast_prompt = f"Podcast Topic: {message}\n\nDocument Content (for reference):\n{document_content[:8000] if document_content else ''}"
            podcast_messages = [
                {"role": "system", "content": podcast_system_prompt},
                {"role": "user", "content": podcast_prompt}
            ]
            response_groq = requests.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                    "messages": podcast_messages,
                    "temperature": podcast_options["temperature"],
                    "top_p": podcast_options["top_p"]
                }
            )
            if response_groq.status_code != 200:
                raise Exception(f"Groq API error: {response_groq.text}")
            result = response_groq.json()
            answer = result["choices"][0]["message"]["content"].strip() if "choices" in result and result["choices"] else ''
            chat_message = ChatMessage.objects.create(
                document=document,
                message=message,
                response=answer,
                agent_id=1
            )
            return JsonResponse({
                'response': answer,
                'confidence': min(1.0, len(answer) / 150),
                'message_id': chat_message.id,
                'is_podcast_mode': True
            })

        # --- Master LLM router step ---
        # Only call router LLM if multi-agent (not single agent)
        if is_single_agent:
            discussion_required = False
            initiator_agent_id = agent_id_from_frontend
            responding_agent_ids = [agent_id_from_frontend]
            revised_prompt = message
        elif not (is_final_summary or is_last_turn):
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
                {"role": "user", "content": f"Document: {document_content}\nDiscussion: {discussion_context}\nPrompt: {message}"}
            ]
            # Log prompt size
            prompt_size = sum(len(m['content']) for m in router_messages)
            logger.info(f"Router LLM prompt size: {prompt_size} characters")
            response_groq = requests.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                    "messages": router_messages,
                    "temperature": 0.0,
                    "top_p": 1.0
                }
            )
            logger.info(f"Router LLM response: {response_groq.status_code} {response_groq.text}")
            if response_groq.status_code != 200:
                logger.error(f"Router LLM error: {response_groq.text}")
                return JsonResponse({
                    'error': 'Router LLM error',
                    'discussion_required': False,
                    'initiator_agent_id': None,
                    'responding_agent_ids': None,
                    'revised_prompt': message
                }, status=500)
            router_result = response_groq.json()
            router_content = router_result.get('choices', [{}])[0].get('message', {}).get('content', '')
            match = re.search(r'\{[\s\S]*\}', router_content)
            if match:
                try:
                    router_json = pyjson.loads(match.group(0))
                    discussion_required = router_json.get('discussion_required', False)
                    initiator_agent_id = router_json.get('initiator_agent_id', None)
                    revised_prompt = router_json.get('revised_prompt', message)
                    responding_agent_ids = router_json.get('responding_agent_ids', None)
                    if not responding_agent_ids:
                        if discussion_required:
                            responding_agent_ids = [1, 2]
                        else:
                            responding_agent_ids = [initiator_agent_id]
                    message = revised_prompt
                    is_single_agent = False
                except Exception as e:
                    logger.error(f"Router JSON parse error: {e}")
                    discussion_required = False
                    initiator_agent_id = 1
                    revised_prompt = message
                    responding_agent_ids = [1]
                    is_single_agent = True
            else:
                logger.error(f"Router LLM did not return valid JSON: {router_content}")
                discussion_required = False
                initiator_agent_id = 1
                revised_prompt = message
                responding_agent_ids = [1]
                is_single_agent = True
            router_debug = {
                'discussion_required': discussion_required,
                'initiator_agent_id': initiator_agent_id,
                'responding_agent_ids': responding_agent_ids,
                'revised_prompt': revised_prompt
            }

            # --- PATCH: If revised_prompt is a string but both Agent 1 and Agent 2 are mentioned, split it into a dict ---
            if (
                not isinstance(revised_prompt, dict)
                and isinstance(responding_agent_ids, list)
                and set(responding_agent_ids) == {1, 2}
                and isinstance(revised_prompt, str)
                and (('Agent 1' in revised_prompt or 'agent 1' in revised_prompt) and ('Agent 2' in revised_prompt or 'agent 2' in revised_prompt))
            ):
                # Try to split the prompt for each agent
                agent1_match = re.search(r'(Agent 1[^A]*?)(?=Agent 2|$)', revised_prompt, re.IGNORECASE)
                agent2_match = re.search(r'(Agent 2[^A]*?)(?=Agent 1|$)', revised_prompt, re.IGNORECASE)
                agent1_instr = agent1_match.group(1).strip() if agent1_match else ''
                agent2_instr = agent2_match.group(1).strip() if agent2_match else ''
                # Clean up leading agent labels
                agent1_instr = re.sub(r'^(Agent 1[:,]?\s*)', '', agent1_instr, flags=re.IGNORECASE)
                agent2_instr = re.sub(r'^(Agent 2[:,]?\s*)', '', agent2_instr, flags=re.IGNORECASE)
                # Only set if both found
                if agent1_instr and agent2_instr:
                    revised_prompt = {"1": agent1_instr, "2": agent2_instr}
                    router_debug['revised_prompt'] = revised_prompt
        # --- Master agent summary logic ---
        if not is_single_agent and (is_final_summary or is_last_turn):
            logger.info("Generating final summary by master agent")
            master_agent_type = agent_model_type
            master_agent_config = AGENT_CONFIGS.get(master_agent_type)
            master_agent_model = "meta-llama/llama-4-scout-17b-16e-instruct"
            
            # --- INTEGRATION: REUSE standard agent prompt instead of a separate one ---
            master_agent_system_prompt = master_agent_config["system_prompt"].format(agent_id=master_agent_id)
            
            master_agent_options = {
                "temperature": master_agent_config["temperature"],
                "top_p": master_agent_config["top_p"]
            }
            messages = []
            messages.append({"role": "system", "content": master_agent_system_prompt})
            messages.append({"role": "system", "content": "The following document content should be used as the primary source for your answers. Only use your own knowledge to supplement or clarify if needed."})
            doc_content = document_content[:8000] if len(document_content) > 8000 else document_content
            messages.append({"role": "user", "content": f"Document Content:\n{doc_content}"})
            if discussion_context:
                messages.append({"role": "user", "content": f"Discussion Context:\n{discussion_context}"})
            if discussion_history:
                for i, turn in enumerate(discussion_history):
                    if turn.startswith("Agent"):
                        messages.append({"role": "assistant", "content": turn})
                    else:
                        messages.append({"role": "user", "content": turn})
            last_agent_question = None
            if discussion_history:
                last_turn = discussion_history[-1]
                question_match = re.search(r'([A-Z][^\n\.!?]*\?)', last_turn)
                if question_match:
                    last_agent_question = question_match.group(1).strip()
            initial_user_prompt = None
            if discussion_history:
                for turn in discussion_history:
                    if turn.startswith("User:"):
                        initial_user_prompt = turn[len("User:"):].strip()
                        break
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
            # Log prompt size
            prompt_size = sum(len(m['content']) for m in messages)
            logger.info(f"Summary LLM prompt size: {prompt_size} characters")
            response_groq = requests.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": master_agent_model,
                    "messages": messages,
                    "temperature": master_agent_options["temperature"],
                    "top_p": master_agent_options["top_p"]
                }
            )
            if response_groq.status_code != 200:
                raise Exception(f"Groq API error: {response_groq.text}")
            result = response_groq.json()
            answer = result["choices"][0]["message"]["content"].strip() if "choices" in result and result["choices"] else ''
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
        if is_single_agent:
            full_instruction = f"Current Instruction: {message}\n\n" \
                             f"IMPORTANT: You are the ONLY agent. Provide a single, well-structured response. Do not ask questions, do not mention other agents, and do not break this into multiple responses."
        else:
            # For multi-agent, use the lean discussion_context from the sliding window
            full_instruction = f"Recent Discussion History:\n{discussion_context}\n\n"\
                             f"Current Instruction: {message}\n\n" \
                             f"Remember: You are Agent {agent_id_from_frontend}. Respond to the current instruction or any questions directed to you. Keep your response focused and concise."
            
        messages = []
        messages.append({"role": "system", "content": agent_system_prompt})
        messages.append({"role": "system", "content": "The following document content should be used as the primary source for your answers. Only use your own knowledge to supplement or clarify if needed."})
        # The document_content variable now holds the dynamically retrieved chunks
        messages.append({"role": "user", "content": f"Document Content:\n{document_content}"})
        
        # We add the full instruction which contains the sliding window of the discussion
        messages.append({"role": "user", "content": full_instruction})

        # Log prompt size
        prompt_size = sum(len(m['content']) for m in messages)
        logger.info(f"Agent LLM prompt size: {prompt_size} characters")
        response_groq = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                "messages": messages,
                "temperature": agent_options["temperature"],
                "top_p": agent_options["top_p"]
            }
        )
        if response_groq.status_code != 200:
            raise Exception(f"Groq API error: {response_groq.text}")
        result = response_groq.json()
        answer = result["choices"][0]["message"]["content"].strip() if "choices" in result and result["choices"] else ''
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


@api_view(['POST'])
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

# Helper: Retry Groq API call with exponential backoff on 429
def groq_post_with_retry(*args, max_retries=3, **kwargs):
    delay = 1
    for attempt in range(max_retries):
        response = requests.post(*args, **kwargs)
        if response.status_code != 429:
            return response
        time.sleep(delay)
        delay *= 2
    return response 

# Helper: Truncate a chunk to a max length (in characters)
def truncate_chunk(text, max_length=500):
    return text[:max_length] if len(text) > max_length else text
