import { createElement, useEffect, useMemo, useState } from 'react'
import { Mail, User, Calendar, ShieldCheck, BarChart2, FileText, Clock, Loader2 } from 'lucide-react'
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

export default function AccountBlock() {
  const { user, isAuthenticated } = useAuthStore()
  const { focusedBlockId } = useDashboardStore()
  const isFocused = focusedBlockId === 'account'
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
          throw new Error(typeof ideasJson?.detail === 'string' ? ideasJson.detail : 'Не удалось загрузить идеи')
        }

        if (!reportsResponse.ok) {
          throw new Error(typeof reportsJson?.detail === 'string' ? reportsJson.detail : 'Не удалось загрузить отчеты')
        }

        const ideas = ideasJson?.data || []
        const reports = reportsJson?.data || []

        if (active) {
          setStats({
            total_analyses: ideas.length,
            total_reports: reports.length,
            registration_date: user.created_at,
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
    </div>
  )
}
