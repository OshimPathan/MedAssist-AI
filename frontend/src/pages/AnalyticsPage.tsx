/**
 * MedAssist AI — Analytics Dashboard
 * Beautiful data visualizations with Chart.js
 */

import { useState, useEffect } from 'react'
import { api } from '../services/api'
import './analytics.css'
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    LineElement,
    PointElement,
    ArcElement,
    Title,
    Tooltip,
    Legend,
    Filler,
} from 'chart.js'
import { Bar, Line, Doughnut } from 'react-chartjs-2'

ChartJS.register(
    CategoryScale, LinearScale, BarElement, LineElement,
    PointElement, ArcElement, Title, Tooltip, Legend, Filler
)

interface AnalyticsData {
    summary: {
        total_patients: number
        total_conversations: number
        total_appointments: number
        total_emergencies: number
        active_emergencies: number
        appointments_today: number
    }
    daily_trends: Array<{
        date: string
        day: string
        conversations: number
        appointments: number
        emergencies: number
    }>
    severity_distribution: Record<string, number>
    appointment_status: Record<string, number>
    intent_distribution: Record<string, number>
    department_load: Record<string, number>
    hourly_activity: {
        labels: string[]
        data: number[]
    }
}

export default function AnalyticsPage() {
    const [data, setData] = useState<AnalyticsData | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')

    useEffect(() => {
        fetchAnalytics()
    }, [])

    const fetchAnalytics = async () => {
        try {
            setLoading(true)
            const result = await api.getAnalytics()
            setData(result)
        } catch (err: any) {
            setError(err.message || 'Failed to load analytics')
        } finally {
            setLoading(false)
        }
    }

    if (loading) {
        return (
            <div className="analytics-loading">
                <div className="analytics-spinner" />
                <p>Loading analytics...</p>
            </div>
        )
    }

    if (error || !data) {
        return (
            <div className="analytics-error">
                <h2>⚠️ {error || 'No data'}</h2>
                <p>Login as admin to access analytics dashboards.</p>
                <a href="/admin" className="analytics-btn">Go to Admin →</a>
            </div>
        )
    }

    // ── Chart Configs ──

    const trendChart = {
        labels: data.daily_trends.map(d => `${d.day}\n${d.date}`),
        datasets: [
            {
                label: 'Conversations',
                data: data.daily_trends.map(d => d.conversations),
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.15)',
                fill: true,
                tension: 0.4,
                pointRadius: 5,
                pointBackgroundColor: '#6366f1',
            },
            {
                label: 'Appointments',
                data: data.daily_trends.map(d => d.appointments),
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.15)',
                fill: true,
                tension: 0.4,
                pointRadius: 5,
                pointBackgroundColor: '#10b981',
            },
            {
                label: 'Emergencies',
                data: data.daily_trends.map(d => d.emergencies),
                borderColor: '#ef4444',
                backgroundColor: 'rgba(239, 68, 68, 0.15)',
                fill: true,
                tension: 0.4,
                pointRadius: 5,
                pointBackgroundColor: '#ef4444',
            },
        ],
    }

    const severityChart = {
        labels: ['Critical', 'Urgent', 'Non-Urgent'],
        datasets: [{
            data: [
                data.severity_distribution.CRITICAL || 0,
                data.severity_distribution.URGENT || 0,
                data.severity_distribution.NON_URGENT || 0,
            ],
            backgroundColor: ['#ef4444', '#f59e0b', '#10b981'],
            borderColor: ['#dc2626', '#d97706', '#059669'],
            borderWidth: 2,
            hoverOffset: 8,
        }],
    }

    const apptStatusChart = {
        labels: Object.keys(data.appointment_status),
        datasets: [{
            data: Object.values(data.appointment_status),
            backgroundColor: [
                '#6366f1', '#10b981', '#22c55e',
                '#ef4444', '#f59e0b', '#94a3b8',
            ],
            borderWidth: 0,
            hoverOffset: 8,
        }],
    }

    const intentLabels = Object.keys(data.intent_distribution).map(
        k => k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    )
    const intentChart = {
        labels: intentLabels,
        datasets: [{
            label: 'Messages',
            data: Object.values(data.intent_distribution),
            backgroundColor: [
                '#6366f1', '#ec4899', '#10b981', '#f59e0b',
                '#ef4444', '#06b6d4', '#8b5cf6', '#f97316', '#14b8a6',
            ],
            borderRadius: 6,
            borderSkipped: false,
        }],
    }

    const deptChart = {
        labels: Object.keys(data.department_load),
        datasets: [{
            label: 'Appointments',
            data: Object.values(data.department_load),
            backgroundColor: 'rgba(99, 102, 241, 0.7)',
            borderColor: '#6366f1',
            borderWidth: 2,
            borderRadius: 6,
            borderSkipped: false,
        }],
    }

    const hourlyChart = {
        labels: data.hourly_activity.labels,
        datasets: [{
            label: 'Messages',
            data: data.hourly_activity.data,
            borderColor: '#6366f1',
            backgroundColor: 'rgba(99, 102, 241, 0.2)',
            fill: true,
            tension: 0.3,
            pointRadius: 2,
        }],
    }

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { labels: { color: '#94a3b8', font: { size: 12 } } },
        },
        scales: {
            x: { ticks: { color: '#64748b' }, grid: { color: 'rgba(148,163,184,0.1)' } },
            y: { ticks: { color: '#64748b' }, grid: { color: 'rgba(148,163,184,0.1)' }, beginAtZero: true },
        },
    }

    const doughnutOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom' as const,
                labels: { color: '#94a3b8', padding: 16, font: { size: 12 } },
            },
        },
        cutout: '65%',
    }

    return (
        <div className="analytics-page">
            {/* Header */}
            <header className="analytics-header">
                <div className="analytics-header-content">
                    <div>
                        <h1>📊 Analytics Dashboard</h1>
                        <p className="analytics-subtitle">MedAssist AI — Real-time hospital intelligence</p>
                    </div>
                    <div className="analytics-header-actions">
                        <button onClick={fetchAnalytics} className="analytics-btn-refresh">
                            🔄 Refresh
                        </button>
                        <a href="/admin" className="analytics-btn-back">← Admin</a>
                        <a href="/" className="analytics-btn-back">💬 Chat</a>
                    </div>
                </div>
            </header>

            {/* Summary Cards */}
            <section className="analytics-cards">
                <div className="analytics-card card-indigo">
                    <div className="card-icon">👥</div>
                    <div className="card-content">
                        <span className="card-number">{data.summary.total_patients}</span>
                        <span className="card-label">Total Patients</span>
                    </div>
                </div>
                <div className="analytics-card card-emerald">
                    <div className="card-icon">💬</div>
                    <div className="card-content">
                        <span className="card-number">{data.summary.total_conversations}</span>
                        <span className="card-label">Conversations</span>
                    </div>
                </div>
                <div className="analytics-card card-blue">
                    <div className="card-icon">📅</div>
                    <div className="card-content">
                        <span className="card-number">{data.summary.appointments_today}</span>
                        <span className="card-label">Today's Appointments</span>
                    </div>
                </div>
                <div className="analytics-card card-red">
                    <div className="card-icon">🚨</div>
                    <div className="card-content">
                        <span className="card-number">{data.summary.active_emergencies}</span>
                        <span className="card-label">Active Emergencies</span>
                    </div>
                </div>
            </section>

            {/* Charts Grid */}
            <section className="analytics-grid">
                {/* 7-Day Trend — Full Width */}
                <div className="analytics-chart-card chart-wide">
                    <h3>📈 7-Day Activity Trend</h3>
                    <div className="chart-container chart-tall">
                        <Line data={trendChart} options={chartOptions} />
                    </div>
                </div>

                {/* Severity Distribution */}
                <div className="analytics-chart-card">
                    <h3>🚨 Emergency Severity</h3>
                    <div className="chart-container">
                        <Doughnut data={severityChart} options={doughnutOptions} />
                    </div>
                </div>

                {/* Appointment Status */}
                <div className="analytics-chart-card">
                    <h3>📋 Appointment Status</h3>
                    <div className="chart-container">
                        <Doughnut data={apptStatusChart} options={doughnutOptions} />
                    </div>
                </div>

                {/* Intent Distribution */}
                <div className="analytics-chart-card chart-wide">
                    <h3>🧠 AI Intent Classification</h3>
                    <div className="chart-container chart-tall">
                        <Bar data={intentChart} options={{
                            ...chartOptions,
                            indexAxis: 'y' as const,
                        }} />
                    </div>
                </div>

                {/* Department Load */}
                <div className="analytics-chart-card">
                    <h3>🏥 Department Load (30d)</h3>
                    <div className="chart-container">
                        <Bar data={deptChart} options={chartOptions} />
                    </div>
                </div>

                {/* Hourly Activity */}
                <div className="analytics-chart-card">
                    <h3>⏰ Today's Hourly Activity</h3>
                    <div className="chart-container">
                        <Line data={hourlyChart} options={chartOptions} />
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="analytics-footer">
                <p>Data refreshed at {new Date().toLocaleTimeString()} • MedAssist AI v2.0</p>
            </footer>
        </div>
    )
}
