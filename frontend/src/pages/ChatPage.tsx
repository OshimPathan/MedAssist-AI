import { useState, useEffect, useRef, useCallback } from 'react'
import WebSocketService, { sendMessageREST } from '../services/websocket'

interface Message {
    id: string
    role: 'user' | 'assistant' | 'system'
    content: string
    intent?: string
    urgency?: string
    isEmergency?: boolean
    suggestions?: string[]
    timestamp: Date
}

export default function ChatPage() {
    const [messages, setMessages] = useState<Message[]>([])
    const [input, setInput] = useState('')
    const [isConnected, setIsConnected] = useState(false)
    const [isTyping, setIsTyping] = useState(false)
    const [sessionId, setSessionId] = useState('')
    const wsRef = useRef<WebSocketService | null>(null)
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const inputRef = useRef<HTMLInputElement>(null)

    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [])

    useEffect(() => {
        scrollToBottom()
    }, [messages, scrollToBottom])

    useEffect(() => {
        const ws = new WebSocketService()
        wsRef.current = ws
        setSessionId(ws.getSessionId())

        ws.on('connected', () => setIsConnected(true))
        ws.on('disconnected', () => setIsConnected(false))

        ws.on('message', (data: any) => {
            setIsTyping(false)
            const msg: Message = {
                id: Date.now().toString() + '_ai',
                role: 'assistant',
                content: data.message,
                intent: data.intent,
                urgency: data.urgency,
                isEmergency: data.is_emergency,
                suggestions: data.suggestions,
                timestamp: new Date(),
            }
            setMessages(prev => [...prev, msg])
        })

        ws.on('error', () => setIsConnected(false))
        ws.connect().catch(() => setIsConnected(false))

        return () => ws.disconnect()
    }, [])

    const sendMessage = async (text: string) => {
        if (!text.trim()) return

        const userMsg: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: text.trim(),
            timestamp: new Date(),
        }
        setMessages(prev => [...prev, userMsg])
        setInput('')
        setIsTyping(true)

        if (wsRef.current?.isConnected()) {
            wsRef.current.sendMessage(text.trim())
        } else {
            try {
                const data = await sendMessageREST(text.trim(), sessionId)
                setIsTyping(false)
                const aiMsg: Message = {
                    id: Date.now().toString() + '_ai',
                    role: 'assistant',
                    content: data.message,
                    intent: data.intent,
                    urgency: data.urgency,
                    isEmergency: data.is_emergency,
                    suggestions: data.suggestions,
                    timestamp: new Date(),
                }
                setMessages(prev => [...prev, aiMsg])
            } catch {
                setIsTyping(false)
                setMessages(prev => [...prev, {
                    id: Date.now().toString() + '_err',
                    role: 'system',
                    content: '⚠️ Connection error. Please try again.',
                    timestamp: new Date(),
                }])
            }
        }

        inputRef.current?.focus()
    }

    const handleSuggestionClick = (suggestion: string) => {
        sendMessage(suggestion)
    }

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            sendMessage(input)
        }
    }

    return (
        <div className="flex flex-col h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-indigo-950">
            {/* Header */}
            <header className="flex items-center justify-between px-6 py-4 bg-white/5 backdrop-blur-xl border-b border-white/10">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-400 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/25">
                        <span className="text-lg">🏥</span>
                    </div>
                    <div>
                        <h1 className="text-white font-bold text-lg tracking-tight">MedAssist AI</h1>
                        <p className="text-blue-300/70 text-xs">24/7 Hospital Assistant</p>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10">
                        <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 shadow-lg shadow-emerald-400/50 animate-pulse' : 'bg-red-400'}`} />
                        <span className="text-xs text-white/60">{isConnected ? 'Connected' : 'Offline'}</span>
                    </div>
                    <a
                        href="/admin"
                        className="text-xs text-blue-400 hover:text-blue-300 transition-colors px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10"
                    >
                        Admin Panel
                    </a>
                </div>
            </header>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4 scrollbar-thin">
                {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full text-center animate-fade-in">
                        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center mb-6 shadow-2xl shadow-blue-500/30">
                            <span className="text-4xl">🏥</span>
                        </div>
                        <h2 className="text-2xl font-bold text-white mb-2">Welcome to MedAssist AI</h2>
                        <p className="text-blue-300/60 mb-8 max-w-md">
                            Your intelligent hospital assistant. I can help with appointments,
                            doctors, departments, and emergency situations.
                        </p>
                        <div className="grid grid-cols-2 gap-3 max-w-md w-full">
                            {['📅 Book Appointment', '👨‍⚕️ Find a Doctor', '🩺 Report Symptoms', '🏥 Hospital Info'].map((item) => (
                                <button
                                    key={item}
                                    onClick={() => sendMessage(item.substring(2).trim())}
                                    className="px-4 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-blue-500/30 text-white/80 text-sm transition-all duration-200 hover:shadow-lg hover:shadow-blue-500/5"
                                >
                                    {item}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {messages.map((msg) => (
                    <div
                        key={msg.id}
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-up`}
                    >
                        <div className={`max-w-[75%] ${msg.role === 'user' ? '' : ''}`}>
                            {/* Avatar + Message */}
                            <div className={`flex items-start gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                                {/* Avatar */}
                                <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${msg.role === 'user'
                                    ? 'bg-gradient-to-br from-violet-500 to-purple-600'
                                    : msg.isEmergency
                                        ? 'bg-gradient-to-br from-red-500 to-red-700 animate-pulse'
                                        : 'bg-gradient-to-br from-blue-500 to-indigo-600'
                                    }`}>
                                    <span className="text-xs">
                                        {msg.role === 'user' ? '👤' : msg.isEmergency ? '🚨' : '🤖'}
                                    </span>
                                </div>

                                {/* Message Bubble */}
                                <div
                                    className={`rounded-2xl px-4 py-3 ${msg.role === 'user'
                                        ? 'bg-gradient-to-r from-violet-600 to-purple-600 text-white shadow-lg shadow-violet-500/20'
                                        : msg.isEmergency
                                            ? 'bg-red-500/10 border border-red-500/30 text-red-100 shadow-lg shadow-red-500/10'
                                            : msg.role === 'system'
                                                ? 'bg-amber-500/10 border border-amber-500/30 text-amber-200'
                                                : 'bg-white/10 backdrop-blur-sm border border-white/10 text-white/90'
                                        }`}
                                >
                                    <div className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</div>
                                    {msg.intent && msg.role === 'assistant' && (
                                        <div className="flex items-center gap-2 mt-2 pt-2 border-t border-white/10">
                                            <span className={`text-[10px] px-2 py-0.5 rounded-full ${msg.urgency === 'critical' ? 'bg-red-500/20 text-red-300' :
                                                msg.urgency === 'urgent' ? 'bg-amber-500/20 text-amber-300' :
                                                    'bg-blue-500/20 text-blue-300'
                                                }`}>
                                                {msg.intent}
                                            </span>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Suggestion Chips */}
                            {msg.suggestions && msg.suggestions.length > 0 && (
                                <div className="flex flex-wrap gap-2 mt-2 ml-11">
                                    {msg.suggestions.map((s, i) => (
                                        <button
                                            key={i}
                                            onClick={() => handleSuggestionClick(s)}
                                            className="text-xs px-3 py-1.5 rounded-full bg-white/5 hover:bg-blue-500/20 border border-white/10 hover:border-blue-400/30 text-blue-300 transition-all duration-200"
                                        >
                                            {s}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                ))}

                {/* Typing Indicator */}
                {isTyping && (
                    <div className="flex justify-start animate-slide-up">
                        <div className="flex items-start gap-3">
                            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
                                <span className="text-xs">🤖</span>
                            </div>
                            <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-2xl px-4 py-3">
                                <div className="flex gap-1">
                                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:0ms]" />
                                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:150ms]" />
                                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:300ms]" />
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="px-4 py-4 bg-white/5 backdrop-blur-xl border-t border-white/10">
                <div className="max-w-3xl mx-auto flex items-center gap-3">
                    <div className="flex-1 relative">
                        <input
                            ref={inputRef}
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Type your message..."
                            className="w-full bg-white/10 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-white/30 focus:outline-none focus:border-blue-500/50 focus:ring-2 focus:ring-blue-500/20 transition-all text-sm"
                            disabled={!isConnected && false}
                        />
                    </div>
                    <button
                        onClick={() => sendMessage(input)}
                        disabled={!input.trim()}
                        className="w-11 h-11 rounded-xl bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 flex items-center justify-center text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-200 shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 active:scale-95"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                        </svg>
                    </button>
                </div>
                <div className="text-center mt-2">
                    <span className="text-[10px] text-white/20">
                        MedAssist AI • Cannot diagnose or prescribe • Always consult healthcare professionals
                    </span>
                </div>
            </div>
        </div>
    )
}
