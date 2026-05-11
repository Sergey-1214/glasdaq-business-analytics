import { Mail, User, Calendar, ShieldCheck, BarChart2, FileText, Clock } from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import { useDashboardStore } from '../../store/dashboardStore'
import './AccountBlock.css'

function getInitials(name) {
  if (!name) return '?'
  return name.split(' ').map((w) => w[0]).slice(0, 2).join('').toUpperCase()
}

function formatDate(str) {
  if (!str) return '—'
  const d = new Date(str)
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
}

const PLAN_COLORS = {
  Basic: '#6b6f80',
  Pro: '#7c6af5',
  Enterprise: '#e0a05c',
}

const MOCK_STATS = [
  { icon: BarChart2, label: 'Анализов', value: '24' },
  { icon: FileText, label: 'Отчётов', value: '8' },
  { icon: Clock, label: 'Дней активен', value: '47' },
]

export default function AccountBlock() {
  const { user } = useAuthStore()
  const { focusedBlockId } = useDashboardStore()
  const isFocused = focusedBlockId === 'account'

  if (!user) return null

  const planColor = PLAN_COLORS[user.plan] ?? PLAN_COLORS.Basic

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
        <div className="account__stats">
          {MOCK_STATS.map(({ icon: Icon, label, value }) => (
            <div key={label} className="account__stat">
              <Icon size={16} className="account__stat-icon" />
              <div className="account__stat-value">{value}</div>
              <div className="account__stat-label">{label}</div>
            </div>
          ))}
        </div>
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
              <span className="account__field-value">{formatDate(user.created_at)}</span>
            </div>
            <div className="account__field">
              <ShieldCheck size={13} className="account__field-icon" />
              <span className="account__field-label">Тариф</span>
              <span className="account__field-value">
                <span className="account__plan-badge" style={{ color: planColor, borderColor: planColor }}>
                  {user.plan ?? 'Basic'}
                </span>
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
