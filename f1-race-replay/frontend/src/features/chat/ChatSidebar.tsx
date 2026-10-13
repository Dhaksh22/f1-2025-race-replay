import React, { useState } from 'react';
import { ChatResponse } from '../../types/f1';
import { sendChatQuestion } from '../../services/api';
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Info,
  Lightbulb,
  MessageSquare,
  Send,
  Sparkles,
  TrendingUp,
} from 'lucide-react';

interface ChatSidebarProps {
  roundNumber: number;
  sessionType: string;
  eventName: string;
  currentFrameIndex: number;
  currentLap: number;
  selectedDriver: string | null;
  compareDriver: string | null;
  isOpen: boolean;
  onToggleOpen: () => void;
}

interface MessageItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  structured?: ChatResponse;
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
  roundNumber,
  sessionType,
  eventName,
  currentFrameIndex,
  currentLap,
  selectedDriver,
  compareDriver,
  isOpen,
  onToggleOpen,
}) => {
  const [messages, setMessages] = useState<MessageItem[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        `Welcome to the **2025 F1 Race Strategist & FIA Knowledge Chatbot**! ` +
        `I am grounded in official FIA 2025 sporting regulations and calibrated session telemetry for the **${eventName} (${sessionType})**. ` +
        `Ask me about race rules, flags, Safety Car regulations, DRS zones, or live driver pace and tyre stint telemetry.`,
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [expandedDetails, setExpandedDetails] = useState<Record<string, boolean>>({});

  const toggleSection = (msgId: string, sectionKey: string) => {
    const key = `${msgId}-${sectionKey}`;
    setExpandedDetails((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSend = async (userText: string) => {
    const trimmed = userText.trim();
    if (!trimmed || loading) return;

    const userMsgId = `user-${Date.now()}`;
    const newMessages: MessageItem[] = [
      ...messages,
      { id: userMsgId, role: 'user', content: trimmed },
    ];
    setMessages(newMessages);
    setInput('');
    setLoading(true);

    try {
      const history = newMessages
        .slice(-6)
        .map((m) => ({ role: m.role, content: m.content }));

      const res = await sendChatQuestion({
        message: trimmed,
        roundNumber,
        sessionType,
        currentFrameIndex,
        currentLap,
        selectedDriver: selectedDriver || undefined,
        compareDriver: compareDriver || undefined,
        history,
      });

      setMessages((prev) => [
        ...prev,
        {
          id: `bot-${Date.now()}`,
          role: 'assistant',
          content: res.answer,
          structured: res,
        },
      ]);
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : 'Unknown chat error';
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `⚠️ **Unable to retrieve answer:** ${errMsg}. (Note: Telemetry tools are strictly locked to the 2025 Formula 1 season).`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const promptSuggestions = [
    `Who is leading the race and what is their tyre stint age?`,
    selectedDriver
      ? `Analyze ${selectedDriver}'s pace and compare to ${compareDriver || 'the leader'}.`
      : 'Compare Norris and Verstappen pace.',
    `How do DRS activation rules work in 2025?`,
    `Explain the Safety Car delta regulations and restarts.`,
  ];

  if (!isOpen) {
    return (
      <button
        type="button"
        onClick={onToggleOpen}
        className="fixed bottom-6 right-6 z-40 bg-[#E10600] hover:bg-red-600 text-white p-3.5 rounded-full shadow-2xl flex items-center gap-2 font-mono text-xs font-bold transition hover:scale-105 border border-white/20"
        title="Open Formula 1 AI Strategist Chatbot"
      >
        <Bot className="w-5 h-5" />
        <span className="hidden sm:inline">F1 STRATEGIST</span>
      </button>
    );
  }

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-[450px] bg-[#0f131d] border-l border-[#263046] shadow-2xl z-40 flex flex-col">
      {/* Sidebar Header */}
      <div className="p-3.5 bg-[#121722] border-b border-[#263046] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-[#E10600]/20 border border-[#E10600] flex items-center justify-center text-[#E10600]">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-white">
              F1 Pit-Wall AI Strategist
            </h3>
            <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              2025 FIA Grounded RAG
            </span>
          </div>
        </div>

        <button
          type="button"
          onClick={onToggleOpen}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#192030] transition text-xs font-mono"
        >
          CLOSE ✕
        </button>
      </div>

      {/* Active Session Context Pill */}
      <div className="px-3.5 py-2 bg-[#161c2a] border-b border-[#263046] text-[11px] font-mono text-slate-300 flex items-center justify-between">
        <span className="truncate">
          R{roundNumber} • {eventName} ({sessionType})
        </span>
        <span className="text-emerald-400 font-bold shrink-0">Lap {currentLap || 1}</span>
      </div>

      {/* Message History List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => {
          const isUser = msg.role === 'user';
          const s = msg.structured;

          return (
            <div
              key={msg.id}
              className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
            >
              <div
                className={`max-w-[92%] rounded-xl p-3 text-xs leading-relaxed ${
                  isUser
                    ? 'bg-[#E10600] text-white rounded-br-xs font-sans'
                    : 'bg-[#192030] text-slate-100 rounded-bl-xs border border-[#263046]'
                }`}
              >
                {/* Main Text Content */}
                <div className="whitespace-pre-wrap font-sans">{msg.content}</div>

                {/* Structured Evidence Accordions for Grounded Responses */}
                {s && (
                  <div className="mt-3 pt-2.5 border-t border-[#263046] space-y-2 font-mono text-[11px]">
                    {/* Verified 2025 Session Facts */}
                    {s.verified_session_facts?.length > 0 && (
                      <div className="bg-[#121722] rounded p-2 border border-emerald-500/30">
                        <button
                          type="button"
                          onClick={() => toggleSection(msg.id, 'facts')}
                          className="w-full flex items-center justify-between text-emerald-400 font-bold text-left"
                        >
                          <span className="flex items-center gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Verified Session Facts ({s.verified_session_facts.length})
                          </span>
                          {expandedDetails[`${msg.id}-facts`] ? (
                            <ChevronDown className="w-3 h-3" />
                          ) : (
                            <ChevronRight className="w-3 h-3" />
                          )}
                        </button>
                        {expandedDetails[`${msg.id}-facts`] && (
                          <ul className="mt-2 space-y-1 text-slate-300 list-disc pl-4 text-[10px]">
                            {s.verified_session_facts.map((fact, idx) => (
                              <li key={idx}>{fact}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}

                    {/* Calculated Telemetry Metrics */}
                    {s.calculated_metrics?.length > 0 && (
                      <div className="bg-[#121722] rounded p-2 border border-sky-500/30">
                        <button
                          type="button"
                          onClick={() => toggleSection(msg.id, 'metrics')}
                          className="w-full flex items-center justify-between text-sky-400 font-bold text-left"
                        >
                          <span className="flex items-center gap-1">
                            <TrendingUp className="w-3.5 h-3.5" />
                            Calculated Metrics ({s.calculated_metrics.length})
                          </span>
                          {expandedDetails[`${msg.id}-metrics`] ? (
                            <ChevronDown className="w-3 h-3" />
                          ) : (
                            <ChevronRight className="w-3 h-3" />
                          )}
                        </button>
                        {expandedDetails[`${msg.id}-metrics`] && (
                          <ul className="mt-2 space-y-1 text-slate-300 list-disc pl-4 text-[10px]">
                            {s.calculated_metrics.map((metric, idx) => (
                              <li key={idx}>{metric}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}

                    {/* Uncertainties & Scope Limitations */}
                    {s.uncertainties?.length > 0 && (
                      <div className="bg-[#121722] rounded p-2 border border-amber-500/30">
                        <button
                          type="button"
                          onClick={() => toggleSection(msg.id, 'uncertainties')}
                          className="w-full flex items-center justify-between text-amber-300 font-bold text-left"
                        >
                          <span className="flex items-center gap-1">
                            <AlertTriangle className="w-3.5 h-3.5" />
                            Evidence Limitations ({s.uncertainties.length})
                          </span>
                          {expandedDetails[`${msg.id}-uncertainties`] ? (
                            <ChevronDown className="w-3 h-3" />
                          ) : (
                            <ChevronRight className="w-3 h-3" />
                          )}
                        </button>
                        {expandedDetails[`${msg.id}-uncertainties`] && (
                          <ul className="mt-2 space-y-1 text-amber-200/90 list-disc pl-4 text-[10px]">
                            {s.uncertainties.map((unc, idx) => (
                              <li key={idx}>{unc}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}

                    {/* Grounding Source Citations */}
                    {s.sources?.length > 0 && (
                      <div className="text-[10px] text-slate-400 pt-1 flex flex-wrap items-center gap-1.5">
                        <span className="font-semibold text-slate-300">Sources:</span>
                        {s.sources.map((src, idx) => (
                          <span
                            key={idx}
                            className="px-1.5 py-0.5 rounded bg-[#121722] border border-[#263046] text-slate-300"
                          >
                            {src}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {loading && (
          <div className="flex items-center gap-2 text-slate-400 font-mono text-xs animate-pulse p-2">
            <Sparkles className="w-4 h-4 text-emerald-400 animate-spin" />
            Synthesizing grounded race strategy & FIA regulations...
          </div>
        )}
      </div>

      {/* Suggested Followups Pill Bar */}
      <div className="p-2.5 bg-[#121722] border-t border-[#263046] space-y-1.5">
        <div className="flex items-center gap-1 text-[10px] font-mono text-slate-400">
          <Lightbulb className="w-3 h-3 text-amber-400" />
          <span>SUGGESTED QUESTIONS:</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {promptSuggestions.map((q, idx) => (
            <button
              key={idx}
              type="button"
              disabled={loading}
              onClick={() => handleSend(q)}
              className="text-[10px] font-mono px-2 py-1 rounded bg-[#192030] hover:bg-[#263046] text-slate-300 border border-[#263046] text-left transition truncate max-w-full disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Input Form Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend(input);
        }}
        className="p-3 bg-[#0f131d] border-t border-[#263046] flex items-center gap-2"
      >
        <input
          type="text"
          value={input}
          disabled={loading}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about 2025 rules, telemetry, tyres..."
          className="flex-1 bg-[#192030] border border-[#263046] rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#E10600]"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="bg-[#E10600] hover:bg-red-600 disabled:opacity-40 text-white p-2 rounded-lg transition"
          title="Send message"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
