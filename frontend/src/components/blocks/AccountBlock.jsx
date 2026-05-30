import { createElement, useEffect, useMemo, useState } from 'react'
import {
  Mail,
  User,
  Calendar,
  ShieldCheck,
  BarChart2,
  FileText,
  Clock,
  Pencil,
  X,
  Check,
  Loader2,
} from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import { useDashboardStore } from '../../store/dashboardStore'
import { apiFetch } from '../../api/client'
import './AccountBlock.css'

function getInitials(name) {
  if (!name) return '?'
  return name
    .split(/[\s_]/)
    .map((word) => word[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

function formatDate(value) {
  if (!value) return '—'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return '—'
  }

  return date.toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

function getDaysSince(value) {
  if (!value) return 0

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return 0
  }

  const diffMs = Date.now() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  return Math.max(diffDays, 1)
}

function EditForm({ user, onSave, onCancel }) {
  const [username, setUsername] = useState(user.username)
  const [email, setEmail] = useState(user.email)
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function handleSave() {
    setError('')

    if (username.trim().length < 3) {
      setError('Имя пользователя — минимум 3 символа')
      return
    }

    if (!email.includes('@')) {
      setError('Некорректный email')
      return
    }

    if (password && password.length < 8) {
      setError('Пароль — минимум 8 символов')
      return
    }

    const payload = {}
    if (username !== user.username) payload.username = username.trim()
    if (email !== user.email) payload.email = email.trim()
    if (password) payload.password = password

    if (!Object.keys(payload).length) {
      onCancel()
      return
    }

    setSaving(true)
    try {
      const response = await apiFetch('/api/identity/users/me', {
        method: 'PATCH',
        body: JSON.stringify(payload),
      })
      const json = await response.json()

      if (!response.ok) {
        const detail = json?.detail
        throw new Error(typeof detail === 'string' ? detail : 'Ошибка сохранения')
      }

      onSave(json.data)
    } catch (error) {
      setError(error.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="account__edit-form">
      {error && <div className="account__edit-error">{error}</div>}

      <div className="account__edit-field">
        <label className="account__edit-label">Имя пользователя</label>
        <input
          className="account__edit-input"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          autoComplete="username"
        />
      </div>

      <div className="account__edit-field">
        <label className="account__edit-label">Email</label>
        <input
          className="account__edit-input"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          autoComplete="email"
        />
      </div>

      <div className="account__edit-field">
        <label className="account__edit-label">Новый пароль</label>
        <input
          className="account__edit-input"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="оставьте пустым, чтобы не менять"
          autoComplete="new-password"
        />
      </div>

      <div className="account__edit-actions">
        <button className="account__edit-btn account__edit-btn--cancel" onClick={onCancel} disabled={saving}>
          <X size={13} /> Отмена
        </button>
        <button className="account__edit-btn account__edit-btn--save" onClick={handleSave} disabled={saving}>
          {saving ? <Loader2 size={13} className="account__spinner" /> : <Check size={13} />}
          Сохранить
        </button>
      </div>
    </div>
  )
}

export default function AccountBlock() {
  const { user, isAuthenticated } = useAuthStore()
  const { focusedBlockId } = useDashboardStore()
  const isFocused = focusedBlockId === 'account'
  const [editing, setEditing] = useState(false)
  const [stats, setStats] = useState(null)
  const [statsLoading, setStatsLoading] = useState(false)
  const [statsError, setStatsError] = useState('')

  useEffect(() => {
    if (!isAuthenticated || !isFocused || !user) {
      return undefined
    }

    let active = true

    async function loadStats() {
      setStatsLoading(true)
      setStatsError('')

      try {
        const [ideasResponse, reportsResponse] = await Promise.all([
          apiFetch('/api/market/ideas/me'),
          apiFetch('/api/market/reports/me'),
        ])

        const [ideasJson, reportsJson] = await Promise.all([
          ideasResponse.json(),
          reportsResponse.json(),
        ])

        if (!ideasResponse.ok) {
          const detail = ideasJson?.detail
          throw new Error(typeof detail === 'string' ? detail : 'Не удалось загрузить идеи')
        }

        if (!reportsResponse.ok) {
          const detail = reportsJson?.detail
          throw new Error(typeof detail === 'string' ? detail : 'Не удалось загрузить отчеты')
        }

        const ideas = ideasJson?.data || []
        const reports = reportsJson?.data || []
        const sortedIdeas = [...ideas].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))

        if (active) {
          setStats({
            total_analyses: ideas.length,
            total_reports: reports.length,
            registration_date: user.created_at,
            last_active: user.last_login_at || user.updated_at || user.created_at,
            first_analysis: sortedIdeas[sortedIdeas.length - 1]?.created_at ?? null,
            last_analysis: sortedIdeas[0]?.created_at ?? null,
          })
        }
      } catch (error) {
        if (active) {
          setStatsError(error.message || 'Не удалось загрузить статистику')
        }
      } finally {
        if (active) {
          setStatsLoading(false)
        }
      }
    }

    loadStats()

    return () => {
      active = false
    }
  }, [isAuthenticated, isFocused, user])

  const statCards = useMemo(() => {
    const registrationDate = stats?.registration_date || user?.created_at
    const activeDays = getDaysSince(registrationDate)

    return [
      { icon: BarChart2, label: 'Анализов', value: String(stats?.total_analyses ?? 0) },
      { icon: FileText, label: 'Отчетов', value: String(stats?.total_reports ?? 0) },
      { icon: Clock, label: 'Дней с нами', value: String(activeDays) },
    ]
  }, [stats, user?.created_at])

  if (!user) return null

  function handleSave(updatedUser) {
    useAuthStore.setState((state) => ({ user: { ...state.user, ...updatedUser } }))
    setEditing(false)
  }

  return (
    <div className={`account ${isFocused ? 'account--focused' : ''}`}>
      <div className="account__top">
        <div className={`account__avatar ${isFocused ? 'account__avatar--lg' : ''}`}>
          {getInitials(user.username)}
        </div>
        <div className="account__info">
          <div className="account__name">{user.username}</div>
          <div className="account__role">Аналитик</div>
        </div>
        {isFocused && !editing && (
          <button className="account__edit-trigger" onClick={() => setEditing(true)} title="Редактировать">
            <Pencil size={13} />
          </button>
        )}
      </div>

      {isFocused && (
        <>
          <div className="account__stats">
            {statCards.map(({ icon, label, value }) => (
              <div key={label} className="account__stat">
                {createElement(icon, { size: 16, className: 'account__stat-icon' })}
                <div className="account__stat-value">{value}</div>
                <div className="account__stat-label">{label}</div>
              </div>
            ))}
          </div>
          {statsLoading && (
            <div className="account__stats-state">
              <Loader2 size={14} className="account__spinner" />
              Обновляем статистику
            </div>
          )}
          {statsError && !statsLoading && <div className="account__stats-state">{statsError}</div>}
        </>
      )}

      <div className="account__divider" />

      {editing ? (
        <EditForm user={user} onSave={handleSave} onCancel={() => setEditing(false)} />
      ) : (
        <div className="account__fields">
          <div className="account__field">
            <User size={13} className="account__field-icon" />
            <span className="account__field-label">Имя</span>
            <span className="account__field-value">{user.username}</span>
          </div>
          <div className="account__field">
            <Mail size={13} className="account__field-icon" />
            <span className="account__field-label">Email</span>
            <span className="account__field-value">{user.email}</span>
          </div>
          {isFocused && (
            <>
              <div className="account__field">
                <Calendar size={13} className="account__field-icon" />
                <span className="account__field-label">С нами</span>
                <span className="account__field-value">{formatDate(stats?.registration_date || user.created_at)}</span>
              </div>
              <div className="account__field">
                <ShieldCheck size={13} className="account__field-icon" />
                <span className="account__field-label">Тариф</span>
                <span className="account__field-value">
                  <span className="account__plan-badge" style={{ color: '#6b6f80', borderColor: '#6b6f80' }}>
                    Basic
                  </span>
                </span>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
