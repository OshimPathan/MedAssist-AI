/**
 * MedAssist AI - REST API Client
 * Handles all HTTP API calls to the backend
 */

const API_BASE = 'http://localhost:8000/api';

class ApiService {
    private token: string | null = null;

    constructor() {
        this.token = localStorage.getItem('medassist_token');
    }

    private async request(endpoint: string, options: RequestInit = {}): Promise<any> {
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
            ...((options.headers || {}) as Record<string, string>),
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers,
        });

        if (response.status === 401) {
            this.logout();
            throw new Error('Unauthorized');
        }

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || 'Request failed');
        }

        return response.json();
    }

    // Auth
    async login(email: string, password: string) {
        const data = await this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        });
        this.token = data.access_token;
        localStorage.setItem('medassist_token', data.access_token);
        return data;
    }

    async register(email: string, password: string, name: string, role: string = 'RECEPTIONIST') {
        return this.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, password, name, role }),
        });
    }

    async getMe() {
        return this.request('/auth/me');
    }

    logout() {
        this.token = null;
        localStorage.removeItem('medassist_token');
    }

    isAuthenticated(): boolean {
        return !!this.token;
    }

    // Dashboard
    async getDashboardStats() {
        return this.request('/admin/stats');
    }

    async getConversations(page: number = 1, perPage: number = 20) {
        return this.request(`/admin/conversations?page=${page}&per_page=${perPage}`);
    }

    async getActiveSessions() {
        return this.request('/admin/sessions/active');
    }

    // Doctors
    async getDoctors(departmentId?: string) {
        const query = departmentId ? `?department_id=${departmentId}` : '';
        return this.request(`/doctors/${query}`);
    }

    async getDepartments() {
        return this.request('/doctors/departments');
    }

    // Appointments
    async getAppointments(filters?: Record<string, string>) {
        const params = new URLSearchParams(filters || {});
        return this.request(`/appointments/?${params}`);
    }

    async bookAppointment(data: any) {
        return this.request('/appointments/', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async rescheduleAppointment(id: string, data: any) {
        return this.request(`/appointments/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async cancelAppointment(id: string) {
        return this.request(`/appointments/${id}`, { method: 'DELETE' });
    }

    async getAvailableSlots(doctorId: string, date: string, duration: number = 30) {
        return this.request(`/appointments/available-slots?doctor_id=${doctorId}&date=${date}&duration=${duration}`);
    }

    async lockSlot(doctorId: string, dateTime: string) {
        return this.request(`/appointments/lock-slot?doctor_id=${doctorId}&date_time=${dateTime}`, {
            method: 'POST',
        });
    }

    async releaseSlot(doctorId: string, dateTime: string) {
        return this.request(`/appointments/release-slot?doctor_id=${doctorId}&date_time=${dateTime}`, {
            method: 'POST',
        });
    }

    // GDPR & Compliance
    async exportPatientData(patientId: string) {
        return this.request(`/compliance/data-export/${patientId}`);
    }

    async updateConsent(patientId: string, consent: boolean) {
        return this.request(`/compliance/consent?patient_id=${patientId}&consent=${consent}`, {
            method: 'POST',
        });
    }

    // Emergency
    async getEmergencies(activeOnly: boolean = true) {
        return this.request(`/emergency/?active_only=${activeOnly}`);
    }

    async updateEmergency(id: string, data: any) {
        return this.request(`/emergency/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async getEmergencyStats() {
        return this.request('/emergency/stats/summary');
    }

    // Triage
    async assessSymptoms(message: string) {
        return this.request('/triage/assess', {
            method: 'POST',
            body: JSON.stringify(message),
        });
    }

    async getFirstAid(condition: string) {
        return this.request(`/triage/first-aid/${encodeURIComponent(condition)}`);
    }

    async getTriageDepartments() {
        return this.request('/triage/departments');
    }

    // Knowledge Base
    async searchKnowledge(query: string, topK: number = 5) {
        return this.request(`/knowledge/search?q=${encodeURIComponent(query)}&top_k=${topK}`);
    }

    async getKnowledge(category?: string) {
        const query = category ? `?category=${encodeURIComponent(category)}` : '';
        return this.request(`/knowledge/${query}`);
    }

    async addKnowledge(data: { title: string; content: string; category: string }) {
        return this.request('/knowledge/', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async getKnowledgeStats() {
        return this.request('/knowledge/stats');
    }

    async reindexKnowledge() {
        return this.request('/knowledge/reindex', { method: 'POST' });
    }

    // Analytics
    async getAnalytics() {
        return this.request('/analytics/overview');
    }
}

export const api = new ApiService();
export default ApiService;
