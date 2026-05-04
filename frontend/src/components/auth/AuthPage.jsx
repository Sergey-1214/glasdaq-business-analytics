import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff, Loader2 } from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import './AuthPage.css'

export default function AuthPage() {
  const [tab, setTab] = useState('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [localError, setLocalError] = useState('')

  const { login, register, loading, error, clearError } = useAuthStore()
  const navigate = useNavigate()

  function switchTab(t) {
    setTab(t)
    setLocalError('')
    clearError()
    setName('')
    setEmail('')
    setPassword('')
    setConfirm('')
    setShowPassword(false)
    setShowConfirm(false)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setLocalError('')
    clearError()

    if (!email.includes('@')) {
      setLocalError('Введите корректный email')
      return
    }

    if (tab === 'register') {
      if (name.trim().length < 2) {
        setLocalError('Введите имя (минимум 2 символа)')
        return
      }
      if (password.length < 6) {
        setLocalError('Пароль должен быть не менее 6 символов')
        return
      }
      if (password !== confirm) {
        setLocalError('Пароли не совпадают')
        return
      }
    }

    try {
      if (tab === 'login') {
        await login(email, password)
      } else {
        await register(name, email, password)
      }
      navigate('/', { replace: true })
    } catch {
    }
  }

  const displayError = localError || error
  const inputClass = (base) => `${base} ${displayError ? base + '--error' : ''}`

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-card__logo">
          <img src="/glasdaq3.png" alt="Glasdaq" />
        </div>

        <div className="auth-tabs">
          <button
            className={`auth-tabs__btn ${tab === 'login' ? 'auth-tabs__btn--active' : ''}`}
            onClick={() => switchTab('login')}
          >
            Войти
          </button>
          <button
            className={`auth-tabs__btn ${tab === 'register' ? 'auth-tabs__btn--active' : ''}`}
            onClick={() => switchTab('register')}
          >
            Регистрация
          </button>
        </div>

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          {tab === 'register' && (
            <div className="auth-form__field">
              <label className="auth-form__label">Имя</label>
              <input
                className="auth-form__input"
                type="text"
                placeholder="Иван Иванов"
                value={name}
                onChange={(e) => { setName(e.target.value); setLocalError('') }}
                required
                autoComplete="name"
              />
            </div>
          )}

          <div className="auth-form__field">
            <label className="auth-form__label">Email</label>
            <input
              className={inputClass('auth-form__input')}
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => { setEmail(e.target.value); setLocalError(''); clearError() }}
              required
              autoComplete="email"
            />
          </div>

          <div className="auth-form__field">
            <label className="auth-form__label">Пароль</label>
            <div className="auth-form__input-wrap">
              <input
                className={inputClass('auth-form__input')}
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                value={password}
                onChange={(e) => { setPassword(e.target.value); setLocalError(''); clearError() }}
                required
                autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
              />
              <button
                type="button"
                className="auth-form__eye"
                onClick={() => setShowPassword((v) => !v)}
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          {tab === 'register' && (
            <div className="auth-form__field">
              <label className="auth-form__label">Повторите пароль</label>
              <div className="auth-form__input-wrap">
                <input
                  className={inputClass('auth-form__input')}
                  type={showConfirm ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={confirm}
                  onChange={(e) => { setConfirm(e.target.value); setLocalError('') }}
                  required
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  className="auth-form__eye"
                  onClick={() => setShowConfirm((v) => !v)}
                  tabIndex={-1}
                >
                  {showConfirm ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>
          )}

          {displayError && (
            <div className="auth-form__error">{displayError}</div>
          )}

          <button className="auth-form__submit" type="submit" disabled={loading}>
            {loading ? (
              <Loader2 size={16} className="auth-form__spinner" />
            ) : tab === 'login' ? 'Войти' : 'Создать аккаунт'}
          </button>
        </form>
      </div>
    </div>
  )
}
