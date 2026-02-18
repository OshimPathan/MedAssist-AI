import { useState, useEffect, useCallback } from 'react'
import { api } from '../services/api'

interface DashboardStats {
    total_conversations: number
    active_emergencies: number
    appointments_today: number
    total_patients: number
    emergency_count_week: number
    avg_response_time: number
}

interface Emergency {
    id: string
    severity: string
    symptoms: string
    dispatch_status: string
    contact_number: string
    created_at: string
    notes?: string
}

interface Conversation {
    id: string
    session_id: string
    patient_name?: string
    message: string
    ai_response: string
    intent?: string
    urgency?: string
    timestamp: string
}

export default function AdminDashboard() {
    const [isAuthenticated, setIsAuthenticated] = useState(api.isAuthenticated())
    const [activeTab, setActiveTab] = useState<'overview' | 'conversations' | 'emergencies' | 'knowledge' | 'triage'>('overview')
    const [stats, setStats] = useState<DashboardStats | null>(null)
    const [emergencies, setEmergencies] = useState<Emergency[]>([])
    const [conversations, setConversations] = useState<Conversation[]>([])
    const [loginForm, setLoginForm] = useState({ email: '', password: '' })
    const [loginError, setLoginError] = useState('')
    const [loading, setLoading] = useState(false)

    // Knowledge state
    const [knowledgeSearch, setKnowledgeSearch] = useState('')
    const [searchResults, setSearchResults] = useState<any[]>([])
    const [newKb, setNewKb] = useState({ title: '', content: '', category: 'hospital_info' })

    // Triage state
    const [triageInput, setTriageInput] = useState('')
    const [triageResult, setTriageResult] = useState<any>(null)

    const fetchData = useCallback(async () => {
        if (!isAuthenticated) return
        try {
            const [s, e, c] = await Promise.all([
                api.getDashboardStats().catch(() => null),
                api.getEmergencies(true).catch(() => []),
                api.getConversations(1, 20).catch(() => ({ data: [] })),
            ])
            if (s) setStats(s)
            if (Array.isArray(e)) setEmergencies(e)
            if (c?.data) setConversations(c.data)
        } catch { /* graceful fallback */ }
    }, [isAuthenticated])

    useEffect(() => {
        fetchData()
        const interval = setInterval(fetchData, 15000)
        return () => clearInterval(interval)
    }, [fetchData])

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoginError('')
        setLoading(true)
        try {
            await api.login(loginForm.email, loginForm.password)
            setIsAuthenticated(true)
        } catch (err: any) {
            setLoginError(err.message || 'Login failed')
        }
        setLoading(false)
    }

    const handleLogout = () => {
        api.logout()
        setIsAuthenticated(false)
    }

    const handleSearchKnowledge = async () => {
        if (!knowledgeSearch.trim()) return
        try {
            const data = await api.searchKnowledge(knowledgeSearch)
            setSearchResults(data.results || [])
        } catch { setSearchResults([]) }
    }

    const handleAddKnowledge = async (e: React.FormEvent) => {
        e.preventDefault()
        try {
            await api.addKnowledge(newKb)
            setNewKb({ title: '', content: '', category: 'hospital_info' })
        } catch { /* error handling */ }
    }

    const handleTriage = async () => {
        if (!triageInput.trim()) return
        try {
            const result = await api.assessSymptoms(triageInput)
            setTriageResult(result)
        } catch { setTriageResult(null) }
    }

    const handleUpdateEmergency = async (id: string, status: string) => {
        try {
            await api.updateEmergency(id, { dispatch_status: status })
            fetchData()
        } catch { /* error */ }
    }

    if (!isAuthenticated) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-indigo-950 flex items-center justify-center p-4">
                <div className="w-full max-w-md">
                    <div className="text-center mb-8">
                        <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-2xl shadow-lg shadow-blue-500/30">🏥</div>
                        <h1 className="text-2xl font-bold text-white">MedAssist Admin</h1>
                        <p className="text-slate-400 text-sm mt-1">Hospital Management Console</p>
                    </div>
                    <form onSubmit={handleLogin} className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 p-6 space-y-4">
                        {loginError && <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-400 text-sm">{loginError}</div>}
                        <input type="email" placeholder="Email" value={loginForm.email} onChange={e => setLoginForm(p => ({ ...p, email: e.target.value }))}
                            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-500 outline-none focus:border-blue-500/50 transition" />
                        <input type="password" placeholder="Password" value={loginForm.password} onChange={e => setLoginForm(p => ({ ...p, password: e.target.value }))}
                            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-500 outline-none focus:border-blue-500/50 transition" />
                        <button type="submit" disabled={loading}
                            className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold py-3 rounded-xl transition-all duration-200 shadow-lg shadow-blue-500/25 disabled:opacity-50">
                            {loading ? 'Signing in...' : 'Sign In'}
                        </button>
                    </form>
                </div>
            </div>
        )
    }

    const tabs = [
        { id: 'overview', label: '📊 Overview', icon: '📊' },
        { id: 'conversations', label: '💬 Conversations', icon: '💬' },
        { id: 'emergencies', label: '🚨 Emergencies', icon: '🚨' },
        { id: 'knowledge', label: '📚 Knowledge Base', icon: '📚' },
        { id: 'triage', label: '🩺 Triage Test', icon: '🩺' },
    ] as const

    const severityColor = (s: string) => {
        switch (s) {
            case 'CRITICAL': return 'text-red-400 bg-red-500/10 border-red-500/30'
            case 'URGENT': return 'text-amber-400 bg-amber-500/10 border-amber-500/30'
            default: return 'text-blue-400 bg-blue-500/10 border-blue-500/30'
        }
    }

    const statusColor = (s: string) => {
        switch (s) {
            case 'PENDING': return 'text-amber-400'
            case 'DISPATCHED': return 'text-blue-400'
            case 'ARRIVED': return 'text-green-400'
            case 'COMPLETED': return 'text-slate-400'
            default: return 'text-slate-400'
        }
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-indigo-950">
            {/* Header */}
            <header className="bg-white/5 backdrop-blur-xl border-b border-white/10 px-6 py-4">
                <div className="max-w-7xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-lg shadow-lg shadow-blue-500/30">🏥</div>
                        <div>
                            <h1 className="text-lg font-bold text-white">MedAssist Admin</h1>
                            <p className="text-xs text-slate-400">Real-Time Hospital Dashboard</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2 text-sm text-green-400">
                            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></span> Live
                        </div>
                        <a href="/analytics" className="text-sm text-indigo-400 hover:text-indigo-300 transition px-3 py-1.5 rounded-lg hover:bg-white/5">📊 Analytics</a>
                        <a href="/" className="text-sm text-slate-400 hover:text-white transition px-3 py-1.5 rounded-lg hover:bg-white/5">💬 Chat</a>
                        <button onClick={handleLogout} className="text-sm text-slate-400 hover:text-white transition px-3 py-1.5 rounded-lg hover:bg-white/5">Logout</button>
                    </div>
                </div>
            </header>

            <div className="max-w-7xl mx-auto p-6">
                {/* Tab Navigation */}
                <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
                    {tabs.map(tab => (
                        <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                            className={`px-4 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-all duration-200 
                                ${activeTab === tab.id
                                    ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-lg shadow-blue-500/10'
                                    : 'text-slate-400 hover:text-white hover:bg-white/5 border border-transparent'}`}>
                            {tab.label}
                        </button>
                    ))}
                </div>

                {/* Overview Tab */}
                {activeTab === 'overview' && (
                    <div className="space-y-6">
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                            {[
                                { label: 'Conversations', value: stats?.total_conversations || 0, icon: '💬', color: 'from-blue-500 to-cyan-500' },
                                { label: 'Active Emergencies', value: stats?.active_emergencies || 0, icon: '🚨', color: 'from-red-500 to-rose-500' },
                                { label: 'Appointments Today', value: stats?.appointments_today || 0, icon: '📅', color: 'from-green-500 to-emerald-500' },
                                { label: 'Total Patients', value: stats?.total_patients || 0, icon: '👥', color: 'from-purple-500 to-violet-500' },
                            ].map(s => (
                                <div key={s.label} className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 p-5 hover:border-white/20 transition-all duration-300 group">
                                    <div className="flex items-center justify-between mb-3">
                                        <span className="text-2xl">{s.icon}</span>
                                        <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${s.color} opacity-20 group-hover:opacity-40 transition`}></div>
                                    </div>
                                    <div className="text-3xl font-bold text-white mb-1">{s.value}</div>
                                    <div className="text-xs text-slate-400">{s.label}</div>
                                </div>
                            ))}
                        </div>

                        <div className="grid lg:grid-cols-2 gap-6">
                            {/* Recent Emergencies */}
                            <div className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 p-5">
                                <h3 className="text-white font-semibold mb-4 flex items-center gap-2">🚨 Recent Emergencies</h3>
                                <div className="space-y-3 max-h-80 overflow-y-auto">
                                    {emergencies.length === 0 ? (
                                        <p className="text-slate-500 text-sm text-center py-8">No active emergencies</p>
                                    ) : emergencies.slice(0, 5).map(em => (
                                        <div key={em.id} className={`rounded-xl border p-3 ${severityColor(em.severity)}`}>
                                            <div className="flex items-center justify-between mb-1">
                                                <span className="font-semibold text-sm">{em.severity}</span>
                                                <span className={`text-xs ${statusColor(em.dispatch_status)}`}>{em.dispatch_status}</span>
                                            </div>
                                            <p className="text-xs opacity-80 line-clamp-2">{em.symptoms}</p>
                                            <p className="text-xs opacity-60 mt-1">{new Date(em.created_at).toLocaleString()}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Recent Conversations */}
                            <div className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 p-5">
                                <h3 className="text-white font-semibold mb-4 flex items-center gap-2">💬 Recent Conversations</h3>
                                <div className="space-y-3 max-h-80 overflow-y-auto">
                                    {conversations.length === 0 ? (
                                        <p className="text-slate-500 text-sm text-center py-8">No conversations yet</p>
                                    ) : conversations.slice(0, 5).map(c => (
                                        <div key={c.id} className="bg-white/5 rounded-xl p-3 border border-white/5">
                                            <div className="flex items-center justify-between mb-1">
                                                <span className="text-sm text-white font-medium">{c.patient_name || 'Anonymous'}</span>
                                                {c.intent && <span className="text-xs bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded-full">{c.intent}</span>}
                                            </div>
                                            <p className="text-xs text-slate-400 line-clamp-1">{c.message}</p>
                                            <p className="text-xs text-slate-500 mt-1">{new Date(c.timestamp).toLocaleString()}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Conversations Tab */}
                {activeTab === 'conversations' && (
                    <div className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 p-5">
                        <h3 className="text-white font-semibold mb-4">All Conversations</h3>
                        <div className="space-y-3">
                            {conversations.length === 0 ? (
                                <p className="text-slate-500 text-center py-12">No conversations recorded yet. Start chatting to see history here.</p>
                            ) : conversations.map(c => (
                                <div key={c.id} className="bg-white/5 rounded-xl p-4 border border-white/5 hover:border-white/10 transition">
                                    <div className="flex items-center justify-between mb-2">
                                        <div className="flex items-center gap-3">
                                            <span className="text-white font-medium">{c.patient_name || 'Anonymous'}</span>
                                            {c.intent && <span className="text-xs bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded-full">{c.intent}</span>}
                                            {c.urgency && c.urgency !== 'non_urgent' && (
                                                <span className={`text-xs px-2 py-0.5 rounded-full ${c.urgency === 'critical' ? 'bg-red-500/10 text-red-400' : 'bg-amber-500/10 text-amber-400'}`}>
                                                    {c.urgency}
                                                </span>
                                            )}
                                        </div>
                                        <span className="text-xs text-slate-500">{new Date(c.timestamp).toLocaleString()}</span>
                                    </div>
                                    <div className="mt-2 space-y-1">
                                        <p className="text-sm text-slate-300"><span className="text-blue-400">Patient:</span> {c.message}</p>
                                        <p className="text-sm text-slate-400"><span className="text-green-400">AI:</span> {c.ai_response.substring(0, 150)}...</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Emergencies Tab */}
                {activeTab === 'emergencies' && (
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <h3 className="text-white font-semibold text-lg">Emergency Cases</h3>
                            <button onClick={fetchData} className="text-sm text-blue-400 hover:text-blue-300 transition">↻ Refresh</button>
                        </div>
                        {emergencies.length === 0 ? (
                            <div className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 p-12 text-center">
                                <span className="text-4xl mb-4 block">✅</span>
                                <p className="text-slate-400">No active emergencies. All clear.</p>
                            </div>
                        ) : emergencies.map(em => (
                            <div key={em.id} className={`bg-white/5 backdrop-blur-xl rounded-2xl border p-5 ${severityColor(em.severity)}`}>
                                <div className="flex items-center justify-between mb-3">
                                    <div className="flex items-center gap-3">
                                        <span className={`text-sm font-bold px-3 py-1 rounded-full border ${severityColor(em.severity)}`}>{em.severity}</span>
                                        <span className={`text-sm ${statusColor(em.dispatch_status)}`}>● {em.dispatch_status}</span>
                                    </div>
                                    <span className="text-xs text-slate-500">{new Date(em.created_at).toLocaleString()}</span>
                                </div>
                                <p className="text-white mb-2">{em.symptoms}</p>
                                <p className="text-sm text-slate-400 mb-3">📞 {em.contact_number}</p>
                                {em.notes && <p className="text-xs text-slate-500 mb-3">Notes: {em.notes}</p>}
                                <div className="flex gap-2 flex-wrap">
                                    {em.dispatch_status === 'PENDING' && (
                                        <button onClick={() => handleUpdateEmergency(em.id, 'DISPATCHED')}
                                            className="text-xs bg-blue-600/20 text-blue-400 border border-blue-500/30 px-3 py-1.5 rounded-lg hover:bg-blue-600/30 transition">
                                            🚑 Dispatch Ambulance
                                        </button>
                                    )}
                                    {em.dispatch_status === 'DISPATCHED' && (
                                        <button onClick={() => handleUpdateEmergency(em.id, 'ARRIVED')}
                                            className="text-xs bg-green-600/20 text-green-400 border border-green-500/30 px-3 py-1.5 rounded-lg hover:bg-green-600/30 transition">
                                            ✅ Mark Arrived
                                        </button>
                                    )}
                                    {['PENDING', 'DISPATCHED', 'ARRIVED'].includes(em.dispatch_status) && (
                                        <button onClick={() => handleUpdateEmergency(em.id, 'COMPLETED')}
                                            className="text-xs bg-slate-600/20 text-slate-400 border border-slate-500/30 px-3 py-1.5 rounded-lg hover:bg-slate-600/30 transition">
                                            Mark Resolved
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* Knowledge Base Tab */}
                {activeTab === 'knowledge' && (
                    <div className="space-y-6">
                        {/* Semantic Search */}
                        <div className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 p-5">
                            <h3 className="text-white font-semibold mb-4">🔍 Semantic Search (RAG)</h3>
                            <div className="flex gap-2">
                                <input value={knowledgeSearch} onChange={e => setKnowledgeSearch(e.target.value)} placeholder="Search hospital knowledge..."
                                    onKeyDown={e => e.key === 'Enter' && handleSearchKnowledge()}
                                    className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 outline-none focus:border-blue-500/50 transition text-sm" />
                                <button onClick={handleSearchKnowledge}
                                    className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium hover:from-blue-500 hover:to-indigo-500 transition">
                                    Search
                                </button>
                            </div>
                            {searchResults.length > 0 && (
                                <div className="mt-4 space-y-2">
                                    {searchResults.map((r, i) => (
                                        <div key={i} className="bg-white/5 rounded-xl p-3 border border-white/5">
                                            <div className="flex items-center justify-between mb-1">
                                                <span className="text-white font-medium text-sm">{r.title}</span>
                                                <span className="text-xs text-blue-400">{(r.score * 100).toFixed(0)}% match</span>
                                            </div>
                                            <p className="text-xs text-slate-400 line-clamp-3">{r.content}</p>
                                            <span className="text-xs text-slate-500 mt-1 inline-block">{r.category}</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Add Knowledge */}
                        <div className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 p-5">
                            <h3 className="text-white font-semibold mb-4">➕ Add Knowledge Entry</h3>
                            <form onSubmit={handleAddKnowledge} className="space-y-3">
                                <input value={newKb.title} onChange={e => setNewKb(p => ({ ...p, title: e.target.value }))} placeholder="Title"
                                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 outline-none focus:border-blue-500/50 transition text-sm" />
                                <textarea value={newKb.content} onChange={e => setNewKb(p => ({ ...p, content: e.target.value }))} placeholder="Content..." rows={3}
                                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 outline-none focus:border-blue-500/50 transition text-sm resize-none" />
                                <div className="flex gap-3">
                                    <select value={newKb.category} onChange={e => setNewKb(p => ({ ...p, category: e.target.value }))}
                                        className="bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white outline-none focus:border-blue-500/50 transition text-sm">
                                        <option value="hospital_info">Hospital Info</option>
                                        <option value="departments">Departments</option>
                                        <option value="billing">Billing</option>
                                        <option value="test_prep">Test Prep</option>
                                        <option value="emergency">Emergency</option>
                                        <option value="policies">Policies</option>
                                    </select>
                                    <button type="submit" className="bg-gradient-to-r from-green-600 to-emerald-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium hover:from-green-500 hover:to-emerald-500 transition">
                                        Add Entry
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}

                {/* Triage Test Tab */}
                {activeTab === 'triage' && (
                    <div className="space-y-6">
                        <div className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 p-5">
                            <h3 className="text-white font-semibold mb-4">🩺 Triage Assessment Tool</h3>
                            <p className="text-slate-400 text-sm mb-4">Test the AI triage engine by describing symptoms below.</p>
                            <div className="flex gap-2">
                                <input value={triageInput} onChange={e => setTriageInput(e.target.value)} placeholder="Describe symptoms... e.g. 'chest pain and difficulty breathing'"
                                    onKeyDown={e => e.key === 'Enter' && handleTriage()}
                                    className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 outline-none focus:border-blue-500/50 transition text-sm" />
                                <button onClick={handleTriage}
                                    className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium hover:from-blue-500 hover:to-indigo-500 transition">
                                    Assess
                                </button>
                            </div>
                        </div>

                        {triageResult && (
                            <div className={`bg-white/5 backdrop-blur-xl rounded-2xl border p-5 ${severityColor(triageResult.severity_level)}`}>
                                <h3 className="text-white font-semibold mb-4">Assessment Result</h3>
                                <div className="grid md:grid-cols-2 gap-4 mb-4">
                                    <div>
                                        <p className="text-xs text-slate-400 mb-1">Severity</p>
                                        <p className={`text-lg font-bold ${triageResult.severity_level === 'CRITICAL' ? 'text-red-400' : triageResult.severity_level === 'URGENT' ? 'text-amber-400' : 'text-green-400'}`}>
                                            {triageResult.severity_level} ({(triageResult.severity_score * 100).toFixed(0)}%)
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-xs text-slate-400 mb-1">Department</p>
                                        <p className="text-lg font-bold text-white">{triageResult.recommended_department}</p>
                                    </div>
                                    <div>
                                        <p className="text-xs text-slate-400 mb-1">Ambulance Required</p>
                                        <p className={`font-bold ${triageResult.needs_ambulance ? 'text-red-400' : 'text-green-400'}`}>
                                            {triageResult.needs_ambulance ? '🚑 YES' : 'No'}
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-xs text-slate-400 mb-1">Immediate Attention</p>
                                        <p className={`font-bold ${triageResult.needs_immediate_attention ? 'text-red-400' : 'text-green-400'}`}>
                                            {triageResult.needs_immediate_attention ? '⚠️ YES' : 'No'}
                                        </p>
                                    </div>
                                </div>

                                {triageResult.detected_symptoms?.length > 0 && (
                                    <div className="mb-4">
                                        <p className="text-xs text-slate-400 mb-2">Detected Symptoms</p>
                                        <div className="flex flex-wrap gap-2">
                                            {triageResult.detected_symptoms.map((s: string, i: number) => (
                                                <span key={i} className="text-xs bg-white/10 text-white px-2 py-1 rounded-lg">{s}</span>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {triageResult.first_aid_tips?.length > 0 && (
                                    <div>
                                        <p className="text-xs text-slate-400 mb-2">First Aid Guidance</p>
                                        <ul className="space-y-1">
                                            {triageResult.first_aid_tips.map((tip: string, i: number) => (
                                                <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                                                    <span className="text-blue-400 mt-0.5">•</span> {tip}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    )
}
