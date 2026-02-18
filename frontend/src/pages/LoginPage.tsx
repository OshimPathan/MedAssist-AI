import { useState } from 'react'
import { api } from '../services/api'

export default function LoginPage() {
    const [isLogin, setIsLogin] = useState(true)
    const [error, setError] = useState('')
    const [success, setSuccess] = useState('')

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault()
        setError('')
        setSuccess('')
        const form = new FormData(e.currentTarget)

        try {
            if (isLogin) {
                await api.login(form.get('email') as string, form.get('password') as string)
                window.location.href = '/admin'
            } else {
                await api.register(
                    form.get('email') as string,
                    form.get('password') as string,
                    form.get('name') as string,
                    'ADMIN',
                )
                setSuccess('Account created! You can now login.')
                setIsLogin(true)
            }
        } catch (err: any) {
            setError(err.message)
        }
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-indigo-950 flex items-center justify-center p-4">
            <div className="w-full max-w-md">
                <div className="text-center mb-8">
                    <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-400 to-indigo-600 flex items-center justify-center mx-auto mb-4 shadow-2xl shadow-blue-500/30">
                        <span className="text-4xl">🏥</span>
                    </div>
                    <h1 className="text-2xl font-bold text-white">MedAssist AI</h1>
                    <p className="text-blue-300/60 text-sm mt-1">Hospital Staff Portal</p>
                </div>

                <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-8 shadow-2xl">
                    {/* Toggle */}
                    <div className="flex bg-white/5 rounded-xl p-1 mb-6">
                        <button
                            onClick={() => setIsLogin(true)}
                            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${isLogin ? 'bg-blue-500/20 text-blue-300' : 'text-white/40'}`}
                        >Login</button>
                        <button
                            onClick={() => setIsLogin(false)}
                            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${!isLogin ? 'bg-blue-500/20 text-blue-300' : 'text-white/40'}`}
                        >Register</button>
                    </div>

                    {error && <div className="text-red-400 text-sm mb-4 bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-center">{error}</div>}
                    {success && <div className="text-emerald-400 text-sm mb-4 bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3 text-center">{success}</div>}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        {!isLogin && (
                            <div>
                                <label className="text-white/50 text-xs block mb-1.5 ml-1">Full Name</label>
                                <input name="name" type="text" placeholder="Dr. John Smith" required
                                    className="w-full bg-white/10 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-white/20 focus:outline-none focus:border-blue-500/50 focus:ring-2 focus:ring-blue-500/20 text-sm" />
                            </div>
                        )}
                        <div>
                            <label className="text-white/50 text-xs block mb-1.5 ml-1">Email</label>
                            <input name="email" type="email" placeholder="admin@hospital.com" required
                                className="w-full bg-white/10 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-white/20 focus:outline-none focus:border-blue-500/50 focus:ring-2 focus:ring-blue-500/20 text-sm" />
                        </div>
                        <div>
                            <label className="text-white/50 text-xs block mb-1.5 ml-1">Password</label>
                            <input name="password" type="password" placeholder="••••••••" required minLength={8}
                                className="w-full bg-white/10 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-white/20 focus:outline-none focus:border-blue-500/50 focus:ring-2 focus:ring-blue-500/20 text-sm" />
                        </div>
                        <button type="submit"
                            className="w-full py-3 rounded-xl bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-semibold hover:from-blue-600 hover:to-indigo-700 transition-all shadow-lg shadow-blue-500/25 active:scale-[0.98]">
                            {isLogin ? 'Login' : 'Create Account'}
                        </button>
                    </form>
                </div>

                <a href="/" className="block text-center text-blue-400/60 text-xs mt-6 hover:text-blue-300 transition-colors">
                    ← Back to Patient Chat
                </a>
            </div>
        </div>
    )
}
