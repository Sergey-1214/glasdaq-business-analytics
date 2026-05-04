import { Component } from 'react'
import { AlertTriangle, RotateCcw } from 'lucide-react'
import './ErrorBoundary.css'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  reset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <AlertTriangle size={20} className="error-boundary__icon" />
          <span className="error-boundary__text">Что-то пошло не так</span>
          <button className="error-boundary__retry" onClick={this.reset}>
            <RotateCcw size={12} />
            Повторить
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
