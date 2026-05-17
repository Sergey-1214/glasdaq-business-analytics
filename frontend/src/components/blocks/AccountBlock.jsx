import { createElement, useState } from 'react'
import { Mail, User, Calendar, ShieldCheck, BarChart2, FileText, Clock, Pencil, X, Check, Loader2 } from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import { useDashboardStore } from '../../store/dashboardStore'
import { apiFetch } from '../../api/client'
import './AccountBlock.css'

function getInitials(name) {
  if (!name) return '?'
  return name.split(/[\s_]/).map((w) => w[0]).slice(0, 2).join('').toUpperCase()
}

function formatDate(str) {
  if (!str) return '—'
  return new Date(str).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
}

const MOCK_STATS = [
  { icon: BarChart2, label: 'Анализов', value: '24' },
  { icon: FileText, label: 'Отчётов', value: '8' },
  { icon: Clock, label: 'Дней активен', value: '47' },
]

function EditForm({ user, onSave, onCancel }) {
  const [username, setUsername] = useState(user.username)
  const [email, setEmail] = useState(user.email)
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function handleSave() {
    setError('')
    if (username.trim().length < 3) { setError('Имя пользователя — минимум 3 символа'); return }
    if (!email.includes('@')) { setError('Некорректный email'); return }
    if (password && password.length < 8) { setError('Пароль — минимум 8 символов'); return }

    const payload = {}
    if (username !== user.username) payload.username = username.trim()
    if (email !== user.email) payload.email = email.trim()
    if (password) payload.password = password

    if (!Object.keys(payload).length) { onCancel(); return }

    setSaving(true)
    try {
      const res = await apiFetch('/api/identity/users/me', {
        method: 'PATCH',
        body: JSON.stringify(payload),
      })
      const json = await res.json()
      if (!res.ok) {
        const detail = json.detail
        throw new Error(typeof detail === 'string' ? detail : 'Ошибка сохранения')
      }
      onSave(json.data)
    } catch (e) {
      setError(e.message)
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
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
        />
      </div>
      <div className="account__edit-field">
        <label className="account__edit-label">Email</label>
        <input
          className="account__edit-input"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
        />
      </div>
      <div className="account__edit-field">
        <label className="account__edit-label">Новый пароль</label>
        <input
          className="account__edit-input"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="оставьте пустым чтобы не менять"
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
  const { user } = useAuthStore()
  const { focusedBlockId } = useDashboardStore()
  const isFocused = focusedBlockId === 'account'
  const [editing, setEditing] = useState(false)

  if (!user) return null

  function handleSave(updatedUser) {
    useAuthStore.setState((s) => ({ user: { ...s.user, ...updatedUser } }))
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
        <div className="account__stats">
          {MOCK_STATS.map(({ icon, label, value }) => (
            <div key={label} className="account__stat">
              {createElement(icon, { size: 16, className: 'account__stat-icon' })}
              <div className="account__stat-value">{value}</div>
              <div className="account__stat-label">{label}</div>
            </div>
          ))}
        </div>
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
                <span className="account__field-value">{formatDate(user.created_at)}</span>
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
