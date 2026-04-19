import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import './AuthPage.css'

export default function AuthPage() {
  const [tab, setTab] = useState('login') // 'login' | 'register'
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
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
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setLocalError('')
    clearError()

    if (tab === 'register') {
      if (password !== confirm) {
        setLocalError('Пароли не совпадают')
        return
      }
      if (password.length < 6) {
        setLocalError('Пароль должен быть не менее 6 символов')
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
      // ошибка уже в store.error
    }
  }

  const displayError = localError || error

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
                onChange={(e) => setName(e.target.value)}
                required
                autoComplete="name"
              />
            </div>
          )}

          <div className="auth-form__field">
            <label className="auth-form__label">Email</label>
            <input
              className="auth-form__input"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>

          <div className="auth-form__field">
            <label className="auth-form__label">Пароль</label>
            <input
              className="auth-form__input"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
            />
          </div>

          {tab === 'register' && (
            <div className="auth-form__field">
              <label className="auth-form__label">Повторите пароль</label>
              <input
                className="auth-form__input"
                type="password"
                placeholder="••••••••"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                autoComplete="new-password"
              />
            </div>
          )}

          {displayError && (
            <div className="auth-form__error">{displayError}</div>
          )}

          <button className="auth-form__submit" type="submit" disabled={loading}>
            {loading
              ? 'Загрузка...'
              : tab === 'login'
              ? 'Войти'
              : 'Создать аккаунт'}
          </button>
        </form>
      </div>
    </div>
  )
}
