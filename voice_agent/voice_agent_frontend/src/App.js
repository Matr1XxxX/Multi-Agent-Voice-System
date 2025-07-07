import React, { useState, useRef, useEffect } from 'react';
import { 
  Container, 
  Box, 
  Typography, 
  Paper, 
  TextField,
  Button,
  CircularProgress,
  Alert,
  Chip,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem
} from '@mui/material';
import MicIcon from '@mui/icons-material/Mic';
import MicOffIcon from '@mui/icons-material/MicOff';
import SendIcon from '@mui/icons-material/Send';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import AddIcon from '@mui/icons-material/Add';
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition';
import SettingsIcon from '@mui/icons-material/Settings';
import EditIcon from '@mui/icons-material/Edit';
import CloseIcon from '@mui/icons-material/Close';
import ReplayIcon from '@mui/icons-material/Replay';
import DownloadIcon from '@mui/icons-material/Download';
import './App.css';

// Mutex class for narration lock
class Mutex {
  constructor() {
    this._locked = false;
    this._waiting = [];
  }
  lock() {
    const unlock = () => {
      const next = this._waiting.shift();
      if (next) next(unlock);
      else this._locked = false;
    };
    if (this._locked) {
      return new Promise(resolve => this._waiting.push(resolve)).then(() => unlock);
    } else {
      this._locked = true;
      return Promise.resolve(unlock);
    }
  }
}

function App() {
  const [agents, setAgents] = useState([{ id: 1, messages: [] }]);
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentDocument, setCurrentDocument] = useState(null);
  const [error, setError] = useState(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [lastUserPrompt, setLastUserPrompt] = useState(null);
  // New state for discussion management
  const [isDiscussionActive, setIsDiscussionActive] = useState(false);
  const [discussionTurn, setDiscussionTurn] = useState(0);
  const [discussionAgents, setDiscussionAgents] = useState([]); // IDs of agents in discussion
  const [discussionHistory, setDiscussionHistory] = useState([]); // To keep context of conversation
  const [audioQueue, setAudioQueue] = useState([]);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [modelSelectionOpen, setModelSelectionOpen] = useState(false);
  const [newAgentModel, setNewAgentModel] = useState('');
  const [agentModels, setAgentModels] = useState({});
  const [hasInitialized, setHasInitialized] = useState(false);
  // Add new state for tracking which agent is being configured
  const [configuringAgentId, setConfiguringAgentId] = useState(null);
  // Add new state for tracking narration status
  const [isNarrating, setIsNarrating] = useState(false);
  // Remove per-agent listening state, use a single listening state
  const [listening, setListening] = useState(false);
  const [speakingAgentId, setSpeakingAgentId] = useState(null);
  const [thinkingAgentId, setThinkingAgentId] = useState(null);
  const [discussionLimit, setDiscussionLimit] = useState(5); // default odd number
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [tempDiscussionLimit, setTempDiscussionLimit] = useState(discussionLimit);
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [pendingResetAction, setPendingResetAction] = useState(null); // 'manual', 'model', 'document'
  // Add flags to track initial setup
  const [hasInitialModel, setHasInitialModel] = useState(false);
  const [hasInitialDocument, setHasInitialDocument] = useState(false);
  // Add state for router processing
  const [isRouterProcessing, setIsRouterProcessing] = useState(false);
  // Add state for Podcast Mode
  const [isPodcastMode, setIsPodcastMode] = useState(false);
  // Add state for podcast script and narration
  const [podcastScript, setPodcastScript] = useState(null);
  const [podcastTurns, setPodcastTurns] = useState([]);
  const [podcastNarrationActive, setPodcastNarrationActive] = useState(false);
  const [podcastCurrentTurn, setPodcastCurrentTurn] = useState(0);
  // Add state for podcast loading
  const [isPodcastLoading, setIsPodcastLoading] = useState(false);
  // --- Transcript State ---
  const [conversationTranscript, setConversationTranscript] = useState([]); // Array of strings, each is a line (User: ... or Agent X: ...)
  const [contextResetFlag, setContextResetFlag] = useState(0); // Incremented on context reset
  // --- Podcast Q&A Interruption State ---
  const [isPodcastInterrupted, setIsPodcastInterrupted] = useState(false);
  const [podcastResumeIndex, setPodcastResumeIndex] = useState(0);
  const [podcastMainScript, setPodcastMainScript] = useState(null); // store main script for context
  // --- Add narration queue state ---
  const [narrationQueue, setNarrationQueue] = useState([]);
  const [isNarratingQueue, setIsNarratingQueue] = useState(false);
  const [isPodcastQALoading, setIsPodcastQALoading] = useState(false); // Q&A loading state
  // Add state for podcast narration dialog number
  const [mainDialogNumber, setMainDialogNumber] = useState(0);
  // Add state for mini script (Q&A) narration
  const [miniScriptTurns, setMiniScriptTurns] = useState([]);
  const [miniScriptNarrationActive, setMiniScriptNarrationActive] = useState(false);

  const fileInputRef = useRef(null);
  const audioRef = useRef(null);
  const speechSynthesisRef = useRef(window.speechSynthesis);
  const messagesEndRefs = useRef({});

  const { 
    transcript: speechRecognitionTranscript,
    listening: speechRecognitionListening,
    resetTranscript,
    browserSupportsSpeechRecognition
  } = useSpeechRecognition();

  // Add a ref to track the latest request token
  const currentRequestToken = useRef(0);

  // Add new ref for narration mutex
  const narrationMutex = useRef(new Mutex());
  // Add ref to track current unlock function for interruption
  const currentUnlockRef = useRef(null);

  // Modify the useEffect for initialization
  useEffect(() => {
    if (!hasInitialized) {
      setConfiguringAgentId(1); // Set to configure Agent 1
      setModelSelectionOpen(true);
      setHasInitialized(true);
    }
  }, [hasInitialized]);

  // Utility to parse agent mentions on the frontend
  const parseAgentMentionsFrontend = (message) => {
    const agentMentions = {};
    const sortedAgentIds = agents.map(a => a.id).sort((a,b) => b - a);
    const agentPattern = '(' + sortedAgentIds.map(id => `[Aa]gent\\s+${id}`).join('|') + ')';
    
    const agentMentionMatches = [...message.matchAll(new RegExp(agentPattern, 'g'))];

    if (!agentMentionMatches.length) {
      return {};
    }

    for (let i = 0; i < agentMentionMatches.length; i++) {
      const match = agentMentionMatches[i];
      const agentId = parseInt(match[1].match(/\d+/)[0]);
      const startIndex = match.index + match[0].length;

      let instruction = '';
      if (i + 1 < agentMentionMatches.length) {
        const nextMatch = agentMentionMatches[i+1];
        const endIndex = nextMatch.index;
        instruction = message.substring(startIndex, endIndex).trim();
      } else {
        instruction = message.substring(startIndex).trim();
      }

      instruction = instruction.replace(/^(and|then|also)\s+/i, '').trim();
      instruction = instruction.replace(/\s+(and|then|also)$/i, '').trim();
      
      if (instruction) {
        agentMentions[agentId] = instruction;
      }
    }
    return agentMentions;
  };

  const formatResponse = (text) => {
    const lines = text.split('\n');
    const formattedLines = lines.map(line => {
      if (/^\d+\.\s/.test(line)) {
        return `<div style="margin-left: 20px; margin-bottom: 12px;">${line}</div>`;
      }
      if (/^[-*•]\s/.test(line)) {
        return `<div style="margin-left: 20px; margin-bottom: 12px;">${line}</div>`;
      }
      if (line.toLowerCase().includes('key points') || line.toLowerCase().includes('key features')) {
        return `<div style="font-weight: bold; margin-bottom: 12px;">${line}</div>`;
      }
      return `<div style="margin-bottom: 8px;">${line}</div>`;
    });
    return formattedLines.join('');
  };

  // Helper function to clean text for transcript (remove HTML, normalize spacing)
  const cleanTextForTranscript = (text) => {
    // Remove any HTML tags
    let cleaned = text.replace(/<[^>]*>/g, '');
    // Normalize line breaks and spacing
    cleaned = cleaned.replace(/\n\s*\n/g, '\n\n'); // Remove excessive blank lines
    cleaned = cleaned.replace(/\s+$/gm, ''); // Remove trailing spaces from lines
    cleaned = cleaned.trim(); // Remove leading/trailing whitespace
    return cleaned;
  };

  useEffect(() => {
    agents.forEach(agent => {
      if (messagesEndRefs.current[agent.id]) {
        messagesEndRefs.current[agent.id].scrollIntoView({ behavior: 'smooth' });
      }
    });
  }, [agents]);

  // Modify the discussion effect to pipeline LLM and narration
  useEffect(() => {
    if (isDiscussionActive && !isLoading && discussionAgents.length > 0 && agents.length > 1) {
      const maxTurns = discussionLimit - 2; // 2n-1 normal responses, then 1 final summary (total discussionLimit responses)
      const isSummaryTurn = discussionTurn === maxTurns;
      if (isSummaryTurn) {
        // --- Pipeline: trigger summary LLM call immediately, push to narration queue when ready ---
        const summaryAgentId = discussionAgents[0];
        const summaryAgent = agents.find(a => a.id === summaryAgentId);
        if (summaryAgent) {
          setIsDiscussionActive(false);
          processAgentTurn(
            summaryAgentId,
            discussionHistory.join('\n'),
            false,
            null,
            true, // isLastTurn
            true  // isFinalSummary
          ).then((summaryResponse) => {
            if (summaryResponse) {
              setLastUserPrompt('Final Summary of Discussion');
            }
          });
        }
        setDiscussionAgents([]);
        setDiscussionHistory([]);
      } else if (discussionTurn < maxTurns) {
        // Pipeline: trigger next agent LLM call immediately after previous response
        const nextTurn = discussionTurn + 1;
        const nextAgentIndex = nextTurn % discussionAgents.length;
        const nextAgentId = discussionAgents[nextAgentIndex];
        const latestDiscussion = discussionHistory.join('\n');
        // Only trigger if not already in progress
        processAgentTurn(nextAgentId, latestDiscussion, false, null, false).then((responseContent) => {
          if (responseContent) {
            setDiscussionTurn(nextTurn);
          }
        });
      }
    }
  }, [isDiscussionActive, isLoading, discussionTurn, discussionAgents, discussionHistory, currentDocument, isNarratingQueue, narrationQueue.length, agents.length, discussionLimit]);

  // --- Narration queue handler ---
  useEffect(() => {
    if (!isNarratingQueue && narrationQueue.length > 0) {
      const { agentId, text, token } = narrationQueue[0];
      // Only play if token matches
      if (token !== currentRequestToken.current) {
        setNarrationQueue(q => q.slice(1));
        return;
      }
      setIsNarratingQueue(true);
      playVoiceResponse(text, agentId).finally(() => {
        setNarrationQueue(q => q.slice(1));
        setIsNarratingQueue(false);
      });
    }
  }, [narrationQueue, isNarratingQueue]);

  // Modify processAgentTurn to await playVoiceResponse and return its promise
  const processAgentTurn = async (
    agentId, 
    messageContext, 
    isInitialPrompt = false, 
    requestToken = null,
    isLastTurn = false,
    isFinalSummary = false
  ) => {
    // Podcast Mode: skip normal agent LLM, just set up narration
    if (isPodcastMode) {
      // Only trigger narration if we don't already have a script
      if (podcastScript) return;
      setIsPodcastLoading(true);
      setError(null);
      // Request podcast script from backend
      try {
        const agentInstruction = isInitialPrompt 
          ? messageContext 
          : `Continue the discussion. The current conversation is:\n${messageContext}`;
        const isSingleAgent = agents.length === 1;
        const response = await fetch('http://127.0.0.1:8000/api/process-message/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            document_id: currentDocument.id,
            message: agentInstruction,
            agent_id: agentId,
            agent_model_type: agents.find(a => a.id === agentId)?.model || 'critical',
            discussion_history: discussionHistory,
            is_single_agent: isSingleAgent,
            is_final_summary: isFinalSummary,
            is_last_turn: isLastTurn,
            master_agent_id: isFinalSummary ? agentId : undefined,
            is_podcast_mode: isPodcastMode
          }),
        });
        const data = await response.json();
        if (!response.ok) {
          setIsPodcastLoading(false);
          setError(data.error || 'Failed to process message for podcast script');
          return;
        }
        if (data.is_podcast_mode && data.response && typeof data.response === 'string' && data.response.trim().length > 0) {
          setPodcastTurns([]);
          setPodcastCurrentTurn(0);
          setPodcastNarrationActive(false);
          setIsPodcastInterrupted(false);
          setPodcastResumeIndex(0);
          setIsPodcastLoading(false);
          setThinkingAgentId(null);
          setPodcastMainScript(null);
          // Now proceed to parse and start the new podcast
          setPodcastMainScript(data.response);
          if (!discussionHistory.some(line => line.startsWith('PODCAST_SCRIPT:'))) {
            setDiscussionHistory(prev => [...prev, `PODCAST_SCRIPT:${data.response}`]);
          }
          // Robust parsing: trim lines, ignore empty lines, handle markdown
          const turns = [];
          const lines = data.response.split('\n');
          let turnCounter = 0;
          for (let line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue;
            const match = trimmed.match(/^\**\s*Agent\s([12])\s*\**:?\s*(.*)$/i);
            if (match) {
              turns.push({ agent: `Agent ${match[1]}`, text: match[2], turnNumber: turnCounter++ });
            }
          }
          console.log('Parsed podcast turns:', turns);
          if (turns.length === 0) {
            setIsPodcastLoading(false);
            setError('Podcast script was empty or invalid. Raw script: ' + data.response);
            return;
          }
          setPodcastTurns(turns);
          setPodcastCurrentTurn(0);
          setPodcastNarrationActive(true);
          setIsPodcastLoading(false);
          setThinkingAgentId(null);
          return;
        }
      } catch (err) {
        setIsPodcastLoading(false);
        setError('Podcast script error: ' + err.message);
        return;
      }
    }
    // --- Normal mode ---
    setIsLoading(true);
    setError(null);
    setThinkingAgentId(agentId);
    const myToken = requestToken !== null ? requestToken : currentRequestToken.current;
    try {
      const agentInstruction = isInitialPrompt 
        ? messageContext 
        : `Continue the discussion. The current conversation is:\n${messageContext}`;
      const isSingleAgent = agents.length === 1;
      const response = await fetch('http://127.0.0.1:8000/api/process-message/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: currentDocument.id,
          message: agentInstruction,
          agent_id: agentId,
          agent_model_type: agents.find(a => a.id === agentId)?.model || 'critical',
          discussion_history: discussionHistory,
          is_single_agent: isSingleAgent,
          is_final_summary: isFinalSummary,
          is_last_turn: isLastTurn,
          master_agent_id: isFinalSummary ? agentId : undefined,
          is_podcast_mode: isPodcastMode
        }),
      });
      if (myToken !== currentRequestToken.current) return null;
      const data = await response.json();
      if (!response.ok) {
        setThinkingAgentId(null);
        throw new Error(data.error || 'Failed to process message for agent turn');
      }
      if (data.response) {
        setAgents(prev => prev.map(agent =>
          agent.id === agentId
            ? {
                ...agent,
                messages: [
                  ...agent.messages,
                  {
                    type: 'ai',
                    content: formatResponse(data.response),
                    confidence: data.confidence,
                    isFinalSummary: isFinalSummary
                  }
                ]
              }
            : agent
        ));
        if (isSingleAgent) {
          setDiscussionHistory(prev => {
            setConversationTranscript(tprev => [...tprev, `Agent: ${cleanTextForTranscript(data.response)}`]);
            return [...prev, `User: ${messageContext}`, `Agent: ${data.response}`];
          });
        } else {
          setDiscussionHistory(prev => {
            setConversationTranscript(tprev => [...tprev, `Agent ${agentId}: ${cleanTextForTranscript(data.response)}`]);
            return [...prev, `Agent ${agentId}: ${data.response}`];
          });
        }
        setThinkingAgentId(null);
        // --- Pipeline: push to narration queue instead of awaiting narration ---
        setNarrationQueue(q => [...q, { agentId, text: data.response, token: myToken }]);
      }
      if (myToken === currentRequestToken.current) {
        setIsLoading(false);
      }
      return data.response;
    } catch (err) {
      if (myToken === currentRequestToken.current) {
        setThinkingAgentId(null);
        setError(err.message);
        setIsLoading(false);
        setIsNarrating(false);
      }
      return null;
    }
  };

  // Reset context logic
  const resetContext = () => {
    setDiscussionHistory([]);
    setLastUserPrompt(null);
    setAgents(prev => prev.map(agent => ({ ...agent, messages: [] })));
    setConversationTranscript([]);
    setContextResetFlag(flag => flag + 1);
  };

  // Show reset dialog and store what triggered it
  const handleAskResetContext = (action) => {
    // Check if there's actually context to reset
    if (discussionHistory.length === 0 && !lastUserPrompt && agents.every(agent => agent.messages.length === 0)) {
      // Context is already empty, show a message instead of dialog
      setError('Context is already reset - no conversation history to clear.');
      return;
    }
    
    setPendingResetAction(action);
    setResetDialogOpen(true);
  };

  const handleConfirmReset = () => {
    resetContext();
    setResetDialogOpen(false);
    setPendingResetAction(null);
  };

  const handleCancelReset = () => {
    setResetDialogOpen(false);
    setPendingResetAction(null);
  };

  // --- Patch model selection to ask for reset ---
  const handleModelSelection = (model) => {
    if (isDiscussionActive || isRouterProcessing || isNarrating || isPodcastLoading) return; // Prevent model change during discussion, router processing, narration, or podcast loading
    setNewAgentModel('');
    setModelSelectionOpen(false);

    if (configuringAgentId) {
      if (agents.length === 0) {
        setAgents([{ id: 1, messages: [], model: model }]);
        setAgentModels({ 1: model });
      } else {
        if (configuringAgentId <= agents.length) {
          setAgents(prev => prev.map(agent => 
            agent.id === configuringAgentId 
              ? { ...agent, model: model }
              : agent
          ));
          setAgentModels(prev => ({ ...prev, [configuringAgentId]: model }));
        } else {
          setAgents(prev => [...prev, { id: configuringAgentId, messages: [], model: model }]);
          setAgentModels(prev => ({ ...prev, [configuringAgentId]: model }));
        }
      }
      // Only ask to reset context if it's not the initial model setup and there's context to reset
      if (hasInitialModel && (discussionHistory.length > 0 || lastUserPrompt || agents.some(agent => agent.messages.length > 0))) {
        handleAskResetContext('model');
      } else if (!hasInitialModel) {
        setHasInitialModel(true);
      }
    }
    setConfiguringAgentId(null);
  };

  // --- Patch file upload to ask for reset ---
  const handleFileUpload = async (event) => {
    if (isDiscussionActive || isRouterProcessing || isNarrating || isPodcastLoading) return; // Prevent file upload during discussion, router processing, narration, or podcast loading
    const file = event.target.files[0];
    if (!file) return;

    setIsLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/upload/', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to upload document');
      }

      setCurrentDocument(data);
      // Only ask to reset context if it's not the initial document upload and there's context to reset
      if (hasInitialDocument && (discussionHistory.length > 0 || lastUserPrompt || agents.some(agent => agent.messages.length > 0))) {
        handleAskResetContext('document');
      } else if (!hasInitialDocument) {
        setHasInitialDocument(true);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // --- Reset Context Button ---
  const ResetContextButton = () => (
    <Button
      variant="outlined"
      startIcon={<ReplayIcon />}
      onClick={() => handleAskResetContext('manual')}
      color="warning"
      sx={{ minWidth: '150px', fontWeight: 'bold', mr: 2 }}
      disabled={isDiscussionActive || isRouterProcessing || isNarrating || isPodcastLoading}
    >
      Reset Context
    </Button>
  );

  // --- Reset Context Dialog ---
  const ResetContextDialog = () => (
    <Dialog open={resetDialogOpen} onClose={handleCancelReset}>
      <DialogTitle>Reset Context?</DialogTitle>
      <DialogContent>
        <Typography>
          {pendingResetAction === 'model' && 'You changed an agent\'s model. Would you like to reset the conversation context to avoid confusion?'}
          {pendingResetAction === 'document' && 'You uploaded a new document. Would you like to reset the conversation context to avoid confusion?'}
          {pendingResetAction === 'manual' && 'Are you sure you want to reset the conversation context? This will clear all agent messages and discussion history.'}
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleCancelReset}>Cancel</Button>
        <Button onClick={handleConfirmReset} color="warning" variant="contained">Reset</Button>
      </DialogActions>
    </Dialog>
  );

  // Utility: Interrupt all ongoing narration, audio, and discussion (soft interrupt)
  const interruptAll = () => {
    // Stop TTS/audio for previous requests
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      if (audioRef.current.src) {
        URL.revokeObjectURL(audioRef.current.src);
        audioRef.current.src = '';
      }
    }
    if (speechSynthesisRef.current) {
      speechSynthesisRef.current.cancel();
    }
    setIsNarrating(false);
    setIsPlayingAudio(false);
    setSpeakingAgentId(null);
    setThinkingAgentId(null);
    setIsDiscussionActive(false);
    setDiscussionTurn(0);
    setDiscussionAgents([]);
    setPodcastScript(null);
    // DO NOT clear podcastTurns or reset podcastCurrentTurn
    setPodcastNarrationActive(false);
    setIsPodcastLoading(false);
    if (currentUnlockRef.current) {
      currentUnlockRef.current();
      currentUnlockRef.current = null;
    }
    setNarrationQueue([]);
    setIsNarratingQueue(false);
    currentRequestToken.current += 1;
  };

  // Utility: Strict interrupt that clears all podcast turns and resets narration index
  const strictInterruptAll = () => {
    // Stop TTS/audio for previous requests
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      if (audioRef.current.src) {
        URL.revokeObjectURL(audioRef.current.src);
        audioRef.current.src = '';
      }
    }
    if (speechSynthesisRef.current) {
      speechSynthesisRef.current.cancel();
    }
    setIsNarrating(false);
    setIsPlayingAudio(false);
    setSpeakingAgentId(null);
    setThinkingAgentId(null);
    setIsDiscussionActive(false);
    setDiscussionTurn(0);
    setDiscussionAgents([]);
    setPodcastScript(null);
    setPodcastTurns([]); // Clear all podcast turns
    setPodcastCurrentTurn(0); // Reset narration index
    setPodcastNarrationActive(false);
    setIsPodcastLoading(false);
    if (currentUnlockRef.current) {
      currentUnlockRef.current();
      currentUnlockRef.current = null;
    }
    setNarrationQueue([]);
    setIsNarratingQueue(false);
    currentRequestToken.current += 1;
    // Do NOT clear discussionHistory so LLM can use it for future context
  };

  // Accept optional prompt param for handleSend
  const handleSend = async (promptOverride) => {
    interruptAll();
    const prompt = typeof promptOverride === 'string' ? promptOverride : input.trim();
    if (!prompt || !currentDocument) return;
    setInput('');
    // If podcast narration is active, interrupt and do Q&A
    if (isPodcastMode && podcastNarrationActive && podcastTurns.length > 0) {
      // Only stop audio/narration, do NOT clear podcastTurns or reset podcastCurrentTurn
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
        if (audioRef.current.src) {
          URL.revokeObjectURL(audioRef.current.src);
          audioRef.current.src = '';
        }
      }
      if (speechSynthesisRef.current) {
        speechSynthesisRef.current.cancel();
      }
      setIsNarrating(false);
      setIsPlayingAudio(false);
      setSpeakingAgentId(null);
      setThinkingAgentId(null);
      // Do NOT clear podcastTurns or reset podcastCurrentTurn
      setIsPodcastInterrupted(true);
      setIsPodcastQALoading(true); // Show Q&A loading indicator
      setError(null);
      try {
        const response = await fetch('http://127.0.0.1:8000/api/process-message/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            document_id: currentDocument.id,
            message: prompt,
            agent_id: agents[0].id,
            agent_model_type: agents[0].model || 'critical',
            discussion_history: discussionHistory,
            is_single_agent: agents.length === 1,
            is_final_summary: false,
            is_last_turn: false,
            master_agent_id: agents[0].id,
            is_podcast_mode: true,
            is_podcast_interrupt: true,
            main_podcast_context: podcastMainScript || podcastScript,
            podcast_resume_index: podcastResumeIndex
          })
        });
        const data = await response.json();
        if (!response.ok) {
          setError(data.error || 'Failed to process podcast Q&A');
          setIsPodcastQALoading(false);
          return;
        }
        if (data.is_podcast_interrupt && data.response) {
          // Robust parsing: trim lines, ignore empty lines, handle markdown
          const qaTurns = [];
          const lines = data.response.split('\n');
          for (let line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue;
            const match = trimmed.match(/^\**\s*Agent\s([12])\s*\**:?\s*(.*)$/i);
            if (match) {
              qaTurns.push({ agent: `Agent ${match[1]}`, text: match[2] });
            }
          }
          if (qaTurns.length === 0) {
            setIsPodcastQALoading(false);
            setError('Podcast Q&A script was empty or invalid. Raw script: ' + data.response);
            return;
          }
          setMiniScriptTurns(qaTurns);
          setMiniScriptNarrationActive(true);
          setPodcastNarrationActive(false);
          setIsPodcastQALoading(false);
          return;
        }
      } catch (err) {
        setIsPodcastQALoading(false);
        setError('Podcast Q&A error: ' + err.message);
        return;
      }
      return;
    }
    // --- Podcast Mode: Direct script generation, skip router logic ---
    if (isPodcastMode) {
      setIsPodcastLoading(true);
      setError(null);
      setPodcastScript(null);
      setPodcastTurns([]);
      setPodcastCurrentTurn(0);
      setPodcastNarrationActive(false);
      try {
        const response = await fetch('http://127.0.0.1:8000/api/process-message/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            document_id: currentDocument.id,
            message: prompt,
            agent_id: agents[0].id,
            agent_model_type: agents[0].model || 'critical',
            discussion_history: discussionHistory,
            is_single_agent: agents.length === 1,
            is_final_summary: false,
            is_last_turn: false,
            master_agent_id: agents[0].id,
            is_podcast_mode: true
          })
        });
        const data = await response.json();
        if (!response.ok) {
          setError(data.error || 'Failed to process podcast script');
          setIsPodcastLoading(false);
          return;
        }
        if (data.is_podcast_mode && data.response && typeof data.response === 'string' && data.response.trim().length > 0) {
          setPodcastTurns([]);
          setPodcastCurrentTurn(0);
          setPodcastNarrationActive(false);
          setIsPodcastInterrupted(false);
          setPodcastResumeIndex(0);
          setIsPodcastLoading(false);
          setThinkingAgentId(null);
          setPodcastMainScript(null);
          setPodcastMainScript(data.response);
          if (!discussionHistory.some(line => line.startsWith('PODCAST_SCRIPT:'))) {
            setDiscussionHistory(prev => [...prev, `PODCAST_SCRIPT:${data.response}`]);
          }
          // Robust parsing: trim lines, ignore empty lines, handle markdown
          const turns = [];
          const lines = data.response.split('\n');
          let turnCounter = 0;
          for (let line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue;
            const match = trimmed.match(/^\**\s*Agent\s([12])\s*\**:?\s*(.*)$/i);
            if (match) {
              turns.push({ agent: `Agent ${match[1]}`, text: match[2], turnNumber: turnCounter++ });
            }
          }
          console.log('Parsed podcast turns:', turns);
          if (turns.length === 0) {
            setIsPodcastLoading(false);
            setError('Podcast script was empty or invalid. Raw script: ' + data.response);
            return;
          }
          setPodcastTurns(turns);
          setPodcastCurrentTurn(0);
          setPodcastNarrationActive(true);
          setIsPodcastLoading(false);
          setThinkingAgentId(null);
          return;
        }
      } catch (err) {
        setIsPodcastLoading(false);
        setError('Podcast script error: ' + err.message);
        return;
      }
      return;
    }
    // --- Normal prompt routing logic (never runs in podcast mode) ---
    const thisRequestToken = ++currentRequestToken.current;
    setLastUserPrompt(prompt);
    setDiscussionHistory(prev => [...prev, `User: ${prompt}`]);
    setIsLoading(true);
    setIsRouterProcessing(true);
    setError(null);
    // Podcast Mode: clear previous script/turns
    if (isPodcastMode) {
      setPodcastScript(null);
      setPodcastTurns([]);
      setPodcastCurrentTurn(0);
      setPodcastNarrationActive(false);
      setIsPodcastLoading(false);
    }
    // Always send to backend and let backend decide the flow
    try {
      if (!isPodcastMode) {
        setConversationTranscript(tprev => [...tprev, `User: ${cleanTextForTranscript(prompt)}`]);
      }
      const response = await fetch('http://127.0.0.1:8000/api/process-message/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: currentDocument.id,
          message: prompt,
          agent_id: agents[0].id, // Always send Agent 1 as default, backend will override if needed
          agent_model_type: agents[0].model || 'critical',
          discussion_history: discussionHistory,
          is_single_agent: agents.length === 1,
          is_final_summary: false,
          is_last_turn: false,
          master_agent_id: agents[0].id,
          is_podcast_mode: isPodcastMode
        })
      });
      const data = await response.json();
      if (!response.ok) {
        setError(data.error || 'Failed to process message');
        setIsLoading(false);
        setIsRouterProcessing(false);
        return;
      }
      // Debug: Log router output
      console.log('Router output:', {
        discussion_required: data.discussion_required,
        initiator_agent_id: data.initiator_agent_id,
        revised_prompt: data.revised_prompt
      });
      
      setIsRouterProcessing(false); // End router processing indicator
      
      // If backend signals a discussion, start discussion flow with correct initiator
      if (data.discussion_required && data.initiator_agent_id) {
        setIsDiscussionActive(true);
        // Set the initiator as the first agent for this discussion
        setDiscussionAgents(agents.map(a => a.id).sort((a, b) => (a === data.initiator_agent_id ? -1 : b === data.initiator_agent_id ? 1 : a - b)));
        setDiscussionTurn(0);
        await processAgentTurn(data.initiator_agent_id, typeof data.revised_prompt === 'object' ? data.revised_prompt[String(data.initiator_agent_id)] : data.revised_prompt || prompt, true, thisRequestToken);
      } else if (Array.isArray(data.responding_agent_ids) && data.responding_agent_ids.length > 0) {
        // Multi-agent, non-discussion: trigger each agent in order, using their specific prompt if revised_prompt is a dict
        for (const agentId of data.responding_agent_ids) {
          let agentPrompt = data.revised_prompt;
          if (typeof data.revised_prompt === 'object' && data.revised_prompt !== null) {
            agentPrompt = data.revised_prompt[String(agentId)] || prompt;
          }
          await processAgentTurn(agentId, agentPrompt, true, thisRequestToken);
        }
      } else {
        // Normal single-agent or fallback
        await processAgentTurn(data.initiator_agent_id || agents[0].id, typeof data.revised_prompt === 'object' ? data.revised_prompt[String(data.initiator_agent_id || agents[0].id)] : data.revised_prompt || prompt, true, thisRequestToken);
      }
    } catch (err) {
      setError(err.message);
      setIsRouterProcessing(false);
    } finally {
      setIsLoading(false);
    }
  };

  // Add back the handleKeyPress function (for text box)
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Model color mapping
  const modelColors = {
    critical: '#FFD600', // yellow
    analytical: '#42A5F5', // blue
    creative: '#AB47BC', // purple
    practical: '#66BB6A', // green
  };

  // Update playVoiceResponse to set speakingAgentId and return a promise that resolves when narration is done
  const playVoiceResponse = async (text, agentId) => {
    return new Promise(async (resolve, reject) => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/voice-response/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, agent_id: agentId })
        });
        if (!response.ok) {
          const errorData = await response.json();
          setSpeakingAgentId(null);
          setIsPlayingAudio(false);
          setIsNarrating(false);
          setError(errorData.error || 'Failed to generate voice response');
          return reject(errorData.error || 'Failed to generate voice response');
        }
        const audioBlob = await response.blob();
        if (audioBlob.size === 0) throw new Error('Received empty audio blob');
        const audioUrl = URL.createObjectURL(audioBlob);
        if (audioRef.current) {
          if (audioRef.current.src) URL.revokeObjectURL(audioRef.current.src);
          audioRef.current.src = audioUrl;
          audioRef.current.onended = () => {
            setSpeakingAgentId(null);
            URL.revokeObjectURL(audioUrl);
            setIsPlayingAudio(false);
            setIsNarrating(false);
            resolve();
          };
          audioRef.current.onerror = (e) => {
            setSpeakingAgentId(null);
            URL.revokeObjectURL(audioUrl);
            setIsPlayingAudio(false);
            setIsNarrating(false);
            reject('Voice playback error');
          };
          try {
            setSpeakingAgentId(agentId);
            await audioRef.current.play();
            setIsPlayingAudio(true);
          } catch (playError) {
            setSpeakingAgentId(null);
            URL.revokeObjectURL(audioUrl);
            setIsPlayingAudio(false);
            setIsNarrating(false);
            reject('Voice playback error');
          }
        } else {
          setSpeakingAgentId(null);
          setIsPlayingAudio(false);
          setIsNarrating(false);
          reject('No audio element');
        }
      } catch (error) {
        setSpeakingAgentId(null);
        setError(`Voice playback error: ${error.message}`);
        setIsPlayingAudio(false);
        setIsNarrating(false);
        reject(error.message);
      }
    });
  };

  // Central mic handlers (interrupt on listen)
  const startListening = () => {
    interruptAll();
    resetTranscript();
    setListening(true);
    SpeechRecognition.startListening({ continuous: true });
  };
  const stopListening = () => {
    setListening(false);
    SpeechRecognition.stopListening();
    if (speechRecognitionTranscript.trim()) handleSend(speechRecognitionTranscript.trim());
  };

  // Status logic for each agent
  const getAgentStatus = (agentId) => {
    if (isPodcastMode && podcastNarrationActive && podcastTurns.length > 0) {
      if (speakingAgentId === agentId) return 'Speaking';
      return 'Listening';
    }
    if (listening) return 'Listening';
    if (speakingAgentId === agentId) return 'Speaking';
    if (thinkingAgentId === agentId) return 'Thinking';
    if (speakingAgentId || thinkingAgentId) return 'Listening';
    return 'Idle';
  };

  const addAgent = () => {
    if (agents.length < 2) {
      setConfiguringAgentId(agents.length + 1);
      setModelSelectionOpen(true);
    }
  };

  const changeModel = (agentId) => {
    setConfiguringAgentId(agentId);
    setModelSelectionOpen(true);
  };

  const removeAgent = (id) => {
    if (agents.length > 1) {
      setAgents(prev => {
        const filtered = prev.filter(agent => agent.id !== id);
        // If only one agent remains, reindex as Agent 1 and make it master
        if (filtered.length === 1) {
          return [{ ...filtered[0], id: 1 }];
        }
        // If two agents remain, keep their ids as 1 and 2
        return filtered.map((agent, idx) => ({ ...agent, id: idx + 1 }));
      });
    }
  };

  useEffect(() => {
    return () => {
      if (speechSynthesisRef.current) {
        speechSynthesisRef.current.cancel();
      }
    };
  }, []);

  useEffect(() => {
    if (!browserSupportsSpeechRecognition) {
      setError('Your browser does not support speech recognition. Please use Chrome or Edge.');
    }
  }, [browserSupportsSpeechRecognition]);

  useEffect(() => {
    if (speechRecognitionTranscript) {
      setInput(speechRecognitionTranscript);
    }
  }, [speechRecognitionTranscript]);

  // Modify the Model Selection Dialog
  const ModelSelectionDialog = () => {
    // Get models already in use (except for the agent being configured)
    const usedModels = agents
      .filter(a => a.id !== configuringAgentId)
      .map(a => a.model);
    const modelOptions = [
      { value: 'critical', label: 'Critical Thinker' },
      { value: 'analytical', label: 'Analytical Thinker' },
      { value: 'creative', label: 'Creative Thinker' },
      { value: 'practical', label: 'Practical Thinker' },
    ];
    return (
    <Dialog open={modelSelectionOpen} onClose={() => {}}>
      <DialogTitle>
        {configuringAgentId === 1 ? 'Select Initial Agent Model' : 
         configuringAgentId <= agents.length ? 'Change Agent Model' : 'Select New Agent Model'}
      </DialogTitle>
      <DialogContent>
        <FormControl fullWidth sx={{ mt: 2 }}>
          <InputLabel>Model Type</InputLabel>
          <Select
            value={newAgentModel}
            label="Model Type"
            onChange={(e) => setNewAgentModel(e.target.value)}
              disabled={isDiscussionActive || isRouterProcessing || isNarrating || isPodcastLoading}
            >
              {modelOptions.map(option => (
                <MenuItem 
                  key={option.value} 
                  value={option.value}
                  disabled={usedModels.includes(option.value)}
                >
                  {option.label}
                  {usedModels.includes(option.value) ? ' (Already in use)' : ''}
                </MenuItem>
              ))}
          </Select>
        </FormControl>
      </DialogContent>
      <DialogActions>
        <Button 
          onClick={() => handleModelSelection(newAgentModel)} 
            disabled={!newAgentModel || isDiscussionActive || usedModels.includes(newAgentModel) || isRouterProcessing || isNarrating || isPodcastLoading}
          variant="contained"
        >
          Confirm
        </Button>
      </DialogActions>
    </Dialog>
  );
  };

  const handleOpenSettings = () => setSettingsOpen(true);
  const handleCloseSettings = () => setSettingsOpen(false);
  const handleSaveSettings = () => {
    setDiscussionLimit(tempDiscussionLimit);
    setSettingsOpen(false);
  };

  // Add Settings Dialog and Button
  const SettingsDialog = () => (
    <Dialog open={settingsOpen} onClose={handleCloseSettings}>
      <DialogTitle>Discussion Settings</DialogTitle>
      <DialogContent>
        <TextField
          label="Discussion Limit (odd number, min 3)"
          type="number"
          value={tempDiscussionLimit}
          onChange={e => {
            let val = parseInt(e.target.value, 10);
            if (isNaN(val)) val = 3;
            if (val < 3) val = 3;
            if (val % 2 === 0) val += 1;
            setTempDiscussionLimit(val);
          }}
          inputProps={{ min: 3, step: 2 }}
          fullWidth
          sx={{ mt: 2 }}
          disabled={isDiscussionActive || isRouterProcessing || isNarrating || isPodcastLoading}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={handleCloseSettings}>Cancel</Button>
        <Button onClick={handleSaveSettings} variant="contained" disabled={isDiscussionActive || isRouterProcessing || isNarrating || isPodcastLoading}>Save</Button>
      </DialogActions>
    </Dialog>
  );

  // --- Podcast Narration Effect ---
  useEffect(() => {
    if (isPodcastMode && podcastNarrationActive && podcastTurns.length > 0) {
      let cancelled = false;
      const narrationToken = currentRequestToken.current;
      const narrate = async () => {
        for (let i = podcastCurrentTurn; i < podcastTurns.length; i++) {
          if (cancelled || narrationToken !== currentRequestToken.current) break;
          const turn = podcastTurns[i];
          setSpeakingAgentId(turn.agent === 'Agent 1' ? 1 : 2);
          setThinkingAgentId(null);
          setIsNarrating(true);
          // Request TTS for this line
          try {
            const ttsRes = await fetch('http://127.0.0.1:8000/api/podcast-tts/', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ script: `${turn.agent}: ${turn.text}` })
            });
            if (!ttsRes.ok) throw new Error('TTS failed');
            const audioBlob = await ttsRes.blob();
            if (!audioBlob || audioBlob.size === 0) throw new Error('TTS returned empty audio');
            const audioUrl = URL.createObjectURL(audioBlob);
            if (audioRef.current) {
              if (audioRef.current.src) URL.revokeObjectURL(audioRef.current.src);
              audioRef.current.src = audioUrl;
              await new Promise((resolve, reject) => {
                audioRef.current.onended = () => {
                  URL.revokeObjectURL(audioUrl);
                  resolve();
                };
                audioRef.current.onerror = (e) => {
                  if (narrationToken !== currentRequestToken.current || cancelled) {
                    // Interruption: do not set error state, just exit
                    resolve();
                    return;
                  }
                  setError('Podcast TTS error: playback failed.');
                  setIsNarrating(false);
                  setPodcastNarrationActive(false);
                  setIsPodcastLoading(false);
                  resolve(); // resolve instead of reject for interruption safety
                };
                audioRef.current.play();
              });
            }
          } catch (err) {
            if (narrationToken !== currentRequestToken.current || cancelled) {
              // Interruption: do not set error state
              break;
            }
            setError('Podcast TTS error: ' + (err && err.message ? err.message : 'Unknown error'));
            setIsNarrating(false);
            setPodcastNarrationActive(false);
            setIsPodcastLoading(false);
            break;
          }
          // Advance the narration index after each turn
          setPodcastCurrentTurn(prev => prev + 1);
          setMainDialogNumber(turn.turnNumber + 1); // Track dialog number for resuming
        }
        // End narration when all turns are done
        if (narrationToken === currentRequestToken.current && !cancelled) {
          setSpeakingAgentId(null);
          setIsNarrating(false);
          setPodcastNarrationActive(false);
          console.log('[Main Narration] Finished all turns', {
            podcastCurrentTurn,
            mainDialogNumber,
            podcastTurnsLength: podcastTurns.length
          });
        }
        setIsPodcastLoading(false); // Always clear loading popup after narration ends or is interrupted
      };
      narrate();
      return () => {
        cancelled = true;
        setIsPodcastLoading(false); // Always clear loading popup on cleanup/interruption
      };
    }
  }, [isPodcastMode, podcastNarrationActive, podcastTurns]);

  // Add Stop/Interrupt Button component
  const StopInterruptButton = () => (
    <Button
      variant="contained"
      color="error"
      onClick={strictInterruptAll}
      sx={{
        mt: 2,
        minWidth: 0,
        p: 1.5,
        borderRadius: '50%',
        boxShadow: 2,
        fontWeight: 'bold',
        fontSize: 24,
        width: 56,
        height: 56,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
      aria-label="Stop/Interrupt"
      title="Stop/Interrupt"
    >
      &#10006;
    </Button>
  );

  // Show Stop/Interrupt button only if something is active (but NOT during prompt processing)
  const showStopButton = isNarrating || isDiscussionActive || isPodcastLoading || podcastNarrationActive || isPlayingAudio;

  // --- Mini Script (Q&A) Narration Effect ---
  useEffect(() => {
    if (miniScriptNarrationActive && miniScriptTurns.length > 0) {
      let cancelled = false;
      const narrationToken = currentRequestToken.current;
      const narrateMini = async () => {
        for (let i = 0; i < miniScriptTurns.length; i++) {
          if (cancelled || narrationToken !== currentRequestToken.current) break;
          const turn = miniScriptTurns[i];
          setSpeakingAgentId(turn.agent === 'Agent 1' ? 1 : 2);
          setThinkingAgentId(null);
          setIsNarrating(true);
          try {
            const ttsRes = await fetch('http://127.0.0.1:8000/api/podcast-tts/', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ script: `${turn.agent}: ${turn.text}` })
            });
            if (!ttsRes.ok) throw new Error('TTS failed');
            const audioBlob = await ttsRes.blob();
            if (!audioBlob || audioBlob.size === 0) throw new Error('TTS returned empty audio');
            const audioUrl = URL.createObjectURL(audioBlob);
            if (audioRef.current) {
              if (audioRef.current.src) URL.revokeObjectURL(audioRef.current.src);
              audioRef.current.src = audioUrl;
              await new Promise((resolve, reject) => {
                audioRef.current.onended = () => {
                  URL.revokeObjectURL(audioUrl);
                  resolve();
                };
                audioRef.current.onerror = (e) => {
                  if (narrationToken !== currentRequestToken.current || cancelled) {
                    resolve();
                    return;
                  }
                  setError('Podcast TTS error: playback failed.');
                  setIsNarrating(false);
                  setMiniScriptNarrationActive(false);
                  resolve();
                };
                audioRef.current.play();
              });
            }
          } catch (err) {
            if (narrationToken !== currentRequestToken.current || cancelled) {
              break;
            }
            setError('Podcast TTS error: ' + (err && err.message ? err.message : 'Unknown error'));
            setIsNarrating(false);
            setMiniScriptNarrationActive(false);
            break;
          }
        }
        // After Q&A, resume main script at mainDialogNumber
        setSpeakingAgentId(null);
        setIsNarrating(false);
        setMiniScriptNarrationActive(false);
        const resumeIndex = Math.min(mainDialogNumber, podcastTurns.length - 1);
        console.log('[Mini Script Narration] Finished Q&A, resuming main script', {
          requestedResumeAt: mainDialogNumber,
          actualResumeIndex: resumeIndex,
          podcastTurnsLength: podcastTurns.length
        });
        if (resumeIndex < podcastTurns.length) {
          setPodcastCurrentTurn(resumeIndex);
          setPodcastNarrationActive(true);
        } else {
          console.log('[Mini Script Narration] No more main script turns to resume.');
        }
      };
      narrateMini();
      return () => { cancelled = true; };
    }
  }, [miniScriptNarrationActive, miniScriptTurns, mainDialogNumber]);

  return (
    <Container maxWidth="xl" sx={{ height: '100vh', display: 'flex', flexDirection: 'column', py: 2, position: 'relative' }}>
      {agents.length > 1 && (
        <Box sx={{ position: 'fixed', bottom: 24, right: 24, zIndex: 10 }}>
          <Button onClick={handleOpenSettings} variant="outlined" startIcon={<SettingsIcon />} sx={{ minWidth: 0, p: 1, borderRadius: '50%' }} disabled={isDiscussionActive || isRouterProcessing || isNarrating || isPodcastLoading} />
        </Box>
      )}
      {agents.length > 1 && (
        <Box sx={{ position: 'fixed', top: 32, right: 32, zIndex: 11, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 2 }}>
          <Button
            variant={isPodcastMode ? 'contained' : 'outlined'}
            color={isPodcastMode ? 'secondary' : 'primary'}
            onClick={() => setIsPodcastMode((prev) => !prev)}
            sx={{ minWidth: 160, borderRadius: 1, boxShadow: isPodcastMode ? 3 : 1, fontWeight: 'bold', px: 3 }}
          >
            {isPodcastMode ? '🎙️ Podcast Mode ON' : '🎙️ Podcast Mode'}
          </Button>
          {conversationTranscript.length > 0 && !isPodcastMode && (
            <Button
              variant="contained"
              color="success"
              startIcon={<DownloadIcon />}
              onClick={() => {
                const formattedTranscript = conversationTranscript.map((line, index) => {
                  if (index > 0 && (line.startsWith('User:') || line.startsWith('Agent'))) {
                    return `\n${line}`;
                  }
                  return line;
                }).join('\n');
                const header = `Conversation Transcript\n${'='.repeat(50)}\n`;
                const documentInfo = currentDocument ? `Document: ${currentDocument.filename}\n` : '';
                const timestamp = `Generated: ${new Date().toLocaleString()}\n${'='.repeat(50)}\n\n`;
                const fullTranscript = header + documentInfo + timestamp + formattedTranscript;
                const blob = new Blob([fullTranscript], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = currentDocument ? `${currentDocument.filename.replace(/\.[^/.]+$/, '')}_transcript.txt` : 'transcript.txt';
                document.body.appendChild(a);
                a.click();
                setTimeout(() => {
                  document.body.removeChild(a);
                  URL.revokeObjectURL(url);
                }, 0);
              }}
              sx={{ minWidth: 180, borderRadius: 1, fontWeight: 'bold', px: 3 }}
            >
              Download Transcript
            </Button>
          )}
        </Box>
      )}
      <SettingsDialog />
      <ModelSelectionDialog />
      <ResetContextDialog />
      <Paper 
        elevation={3} 
        sx={{
          p: 2, 
          mb: 2, 
          display: 'flex', 
          flexDirection: 'column',
          gap: 2,
          backgroundColor: '#f5f5f5'
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <input
            type="file"
            accept=".pdf,.doc,.docx,.txt"
            style={{ display: 'none' }}
            ref={fileInputRef}
            onChange={handleFileUpload}
          />
          <ResetContextButton />
          <Button
            variant="contained"
            startIcon={<CloudUploadIcon />}
            onClick={() => fileInputRef.current.click()}
            disabled={isLoading || isDiscussionActive || isRouterProcessing || isNarrating || isPodcastLoading}
          >
            Upload Document
          </Button>
          <Typography variant="body2" color="text.secondary">
            {currentDocument ? `Current document: ${currentDocument.filename}` : 'Supported formats: PDF, DOC, DOCX, TXT'}
          </Typography>
          <Box sx={{ flexGrow: 1 }} />
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={addAgent}
            color="secondary"
            sx={{
              minWidth: '150px',
              backgroundColor: '#4caf50',
              '&:hover': {
                backgroundColor: '#388e3c',
              },
              boxShadow: 2,
              fontWeight: 'bold',
              display: agents.length >= 2 ? 'none' : 'flex'
            }}
            disabled={agents.length >= 2 || isDiscussionActive || isRouterProcessing || isNarrating || isPodcastLoading}
          >
            Add New Agent
          </Button>
        </Box>
        {lastUserPrompt && (
          <Paper
            elevation={1}
            sx={{
              p: 2,
              mt: 1,
              backgroundColor: '#e0e0e0',
              color: '#333',
              fontWeight: 'bold'
            }}
          >
            <Typography variant="subtitle1">Your Question:</Typography>
            <Typography variant="body1" sx={{ mt: 0.5 }}>{lastUserPrompt}</Typography>
          </Paper>
        )}
      </Paper>
      {error && (
        <Alert 
          severity="error" 
          sx={{ mb: 2 }}
          onClose={() => setError(null)}
        >
          {error}
        </Alert>
      )}
      {/* --- Voice Circle UI --- */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 0 }}>
        {/* Podcast Loading Indicator */}
        {isPodcastMode && isPodcastLoading && (
          <Box sx={{ 
            position: 'absolute', 
            top: '50%', 
            left: '50%', 
            transform: 'translate(-50%, -50%)', 
            zIndex: 15,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 2,
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            padding: 3,
            borderRadius: 2,
            boxShadow: 3
          }}>
            <CircularProgress size={60} color="secondary" />
            <Typography variant="h6" color="secondary" sx={{ fontWeight: 'bold' }}>
              🎙️ Generating ...
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Creating an engaging conversation between the agents
            </Typography>
          </Box>
        )}
        {isPodcastQALoading && (
          <Box sx={{ 
            position: 'absolute', 
            top: '50%', 
            left: '50%', 
            transform: 'translate(-50%, -50%)', 
            zIndex: 15,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 2,
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            padding: 3,
            borderRadius: 2,
            boxShadow: 3
          }}>
            <CircularProgress size={60} color="secondary" />
            <Typography variant="h6" color="secondary" sx={{ fontWeight: 'bold' }}>
              🎙️ Processing your question for the podcast...
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Generating a natural Q&A segment and resuming the main discussion
            </Typography>
          </Box>
        )}
        <Box sx={{ mb: 4, display: 'flex', justifyContent: agents.length === 2 ? 'center' : 'flex-start', width: '100%' }}>
          {agents.length === 2 && (
            <Box sx={{ position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%, -50%)', zIndex: 2 }}>
              <div className="voice-mic-x-stack">
                <Button
                  variant="contained"
                  color={listening ? 'error' : 'primary'}
                  onClick={listening ? stopListening : startListening}
                  disabled={!currentDocument || !browserSupportsSpeechRecognition || isPodcastLoading}
                  sx={{
                    width: 90,
                    height: 90,
                    borderRadius: '50%',
                    minWidth: 0,
                    minHeight: 0,
                    boxShadow: listening ? '0 0 0 8px #ff5252' : '0 0 0 8px #fffde7',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 48,
                    position: 'relative',
                    zIndex: 2,
                    transition: 'box-shadow 0.3s',
                    backgroundColor: listening ? '#ff5252' : '#1976d2',
                    '&:hover': {
                      backgroundColor: listening ? '#d32f2f' : '#1565c0',
                    },
                  }}
                >
                  {listening ? <MicOffIcon sx={{ fontSize: 48 }} /> : <MicIcon sx={{ fontSize: 48 }} />}
                </Button>
                {showStopButton && <StopInterruptButton />}
              </div>
            </Box>
          )}
        </Box>
        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, alignItems: 'center', justifyContent: 'center', gap: 4, width: '100%' }}>
          {agents.map((agent, idx) => {
            const status = getAgentStatus(agent.id);
            const color = modelColors[agent.model] || '#FFD600';
            return (
              <Box key={agent.id} sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1, minWidth: 220, position: 'relative' }}>
                {/* Edit/Delete buttons */}
                <Box sx={{ position: 'absolute', top: 8, right: 16, display: 'flex', gap: 1, zIndex: 3 }}>
                  <Button size="small" onClick={() => changeModel(agent.id)} sx={{ minWidth: 0, p: 0.5 }} disabled={isDiscussionActive || isRouterProcessing || isNarrating || isPodcastLoading}><EditIcon fontSize="small" /></Button>
                  {agents.length > 1 && (
                    <Button size="small" onClick={() => removeAgent(agent.id)} sx={{ minWidth: 0, p: 0.5 }} disabled={isDiscussionActive || isRouterProcessing || isNarrating || isPodcastLoading}><CloseIcon fontSize="small" /></Button>
                  )}
                </Box>
                <Box
                  className={`voice-circle${status === 'Speaking' ? ' speaking' : ''}${status === 'Listening' ? ' listening' : ''}`}
                  sx={{
                    width: { xs: 220, sm: 320 },
                    height: { xs: 220, sm: 320 },
                    borderRadius: '50%',
                    background: `radial-gradient(circle at 60% 40%, ${color} 60%, #fff 100%)`,
                    boxShadow: status === 'Speaking' ? `0 0 60px 20px ${color}` : `0 0 30px 8px ${color}`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    position: 'relative',
                    transition: 'box-shadow 0.3s',
                    animation: status === 'Speaking' ? 'voicePulse 1.1s infinite' : undefined,
                  }}
                />
                <Typography variant="h6" sx={{ mt: 3, fontWeight: 600, letterSpacing: 1 }}>
                  {status}
                </Typography>
                <Typography variant="subtitle2" sx={{ mt: 1, color: '#888' }}>
                  Agent {agent.id} ({agent.model})
                </Typography>
                {isLoading && thinkingAgentId === agent.id && status === 'Thinking' && (
                  <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
                    <CircularProgress size={36} />
                  </Box>
                )}
              </Box>
            );
          })}
          <audio ref={audioRef} style={{ display: 'none' }} />
        </Box>
        {/* Show mic button at top if only one agent */}
        {agents.length === 1 && (
          <Box sx={{ mb: 4, display: 'flex', justifyContent: 'center', width: '100%' }}>
            <Button
              variant="contained"
              color={listening ? 'error' : 'primary'}
              onClick={listening ? stopListening : startListening}
              disabled={!currentDocument || !browserSupportsSpeechRecognition || isPodcastLoading}
              sx={{
                width: 90,
                height: 90,
                borderRadius: '50%',
                minWidth: 0,
                minHeight: 0,
                boxShadow: listening ? '0 0 0 8px #ff5252' : '0 0 0 8px #fffde7',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 48,
                position: 'relative',
                zIndex: 2,
                transition: 'box-shadow 0.3s',
                backgroundColor: listening ? '#ff5252' : '#1976d2',
                '&:hover': {
                  backgroundColor: listening ? '#d32f2f' : '#1565c0',
                },
              }}
            >
              {listening ? <MicOffIcon sx={{ fontSize: 48 }} /> : <MicIcon sx={{ fontSize: 48 }} />}
            </Button>
            {showStopButton && <StopInterruptButton />}
          </Box>
        )}
        {/* --- Text Input for Prompt --- */}
        <Box sx={{ mt: 4, width: { xs: '90%', sm: 500 }, display: 'flex', alignItems: 'center', gap: 2 }}>
          {isRouterProcessing && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'text.secondary', fontSize: '0.875rem' }}>
              <CircularProgress size={16} />
              <span>Processing prompt...</span>
            </Box>
          )}
          <TextField
            fullWidth
            variant="outlined"
            placeholder={currentDocument ? 'Type your question or prompt...' : 'Upload a document to start'}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            disabled={!currentDocument || isPodcastLoading}
            multiline
            minRows={1}
            maxRows={4}
          />
          <Button
            variant="contained"
            color="primary"
            endIcon={<SendIcon />}
            onClick={() => handleSend()}
            disabled={!input.trim() || !currentDocument || isPodcastLoading}
            sx={{ height: 56 }}
          >
            Send
          </Button>
        </Box>
      </Box>
    </Container>
  );
}

export default App;
