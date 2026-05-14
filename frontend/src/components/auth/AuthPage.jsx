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

  function switchTab(nextTab) {
    setTab(nextTab)
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
      if (name.trim().length < 3) {
        setLocalError('Введите имя (минимум 3 символа)')
        return
      }
      if (password.length < 8) {
        setLocalError('Пароль должен быть не менее 8 символов')
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
      // Store error is rendered below the form.
    }
  }

  const displayError = localError || error
  const inputClass = (base) => `${base} ${displayError ? `${base}--error` : ''}`
  const errorId = displayError ? 'auth-form-error' : undefined

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
            type="button"
          >
            Войти
          </button>
          <button
            className={`auth-tabs__btn ${tab === 'register' ? 'auth-tabs__btn--active' : ''}`}
            onClick={() => switchTab('register')}
            type="button"
          >
            Регистрация
          </button>
        </div>

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          {tab === 'register' && (
            <div className="auth-form__field">
              <label className="auth-form__label" htmlFor="auth-name">Имя пользователя</label>
              <input
                id="auth-name"
                className={inputClass('auth-form__input')}
                type="text"
                placeholder="ivan_ivanov"
                value={name}
                onChange={(e) => {
                  setName(e.target.value)
                  setLocalError('')
                }}
                required
                autoComplete="name"
                aria-invalid={Boolean(displayError)}
                aria-describedby={errorId}
              />
            </div>
          )}

          <div className="auth-form__field">
            <label className="auth-form__label" htmlFor="auth-email">Email</label>
            <input
              id="auth-email"
              className={inputClass('auth-form__input')}
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value)
                setLocalError('')
                clearError()
              }}
              required
              autoComplete="email"
              aria-invalid={Boolean(displayError)}
              aria-describedby={errorId}
            />
          </div>

          <div className="auth-form__field">
            <label className="auth-form__label" htmlFor="auth-password">Пароль</label>
            <div className="auth-form__input-wrap">
              <input
                id="auth-password"
                className={inputClass('auth-form__input')}
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value)
                  setLocalError('')
                  clearError()
                }}
                required
                autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
                aria-invalid={Boolean(displayError)}
                aria-describedby={errorId}
              />
              <button
                type="button"
                className="auth-form__eye"
                onClick={() => setShowPassword((value) => !value)}
                aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
                aria-pressed={showPassword}
              >
                {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          {tab === 'register' && (
            <div className="auth-form__field">
              <label className="auth-form__label" htmlFor="auth-confirm">Повторите пароль</label>
              <div className="auth-form__input-wrap">
                <input
                  id="auth-confirm"
                  className={inputClass('auth-form__input')}
                  type={showConfirm ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={confirm}
                  onChange={(e) => {
                    setConfirm(e.target.value)
                    setLocalError('')
                  }}
                  required
                  autoComplete="new-password"
                  aria-invalid={Boolean(displayError)}
                  aria-describedby={errorId}
                />
                <button
                  type="button"
                  className="auth-form__eye"
                  onClick={() => setShowConfirm((value) => !value)}
                  aria-label={showConfirm ? 'Скрыть подтверждение пароля' : 'Показать подтверждение пароля'}
                  aria-pressed={showConfirm}
                >
                  {showConfirm ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>
          )}

          {displayError && (
            <div id="auth-form-error" className="auth-form__error" role="alert">
              {displayError}
            </div>
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
