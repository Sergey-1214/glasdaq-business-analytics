import { describe, it, expect, beforeEach } from 'vitest'
import { useAnalysisStore } from './analysisStore'

const MOCK_PARSED = {
  language: 'ru',
  normalized_idea: 'кофейня в центре Москвы',
  business_category: 'Food & Beverage',
  subcategory: 'Coffee Shop',
  business_model: 'B2C',
  price_segment: 'mid',
  target_audience: ['millennials', 'office workers'],
  keywords: ['coffee', 'cafe', 'specialty'],
  confidence: 0.92,
}

const MOCK_ANALYSIS = {
  tam: 500000000,
  sam: 120000000,
  som: 15000000,
  competitors: [
    { name: 'Starbucks', share: 30 },
    { name: 'Coffee House', share: 20 },
    { name: 'Other', share: 50 },
  ],
  trend: 'growing',
  verdict: 'Рынок кофеен показывает устойчивый рост.',
}

function reset() {
  useAnalysisStore.setState({ entries: [], parsed: null, analysis: null })
}

describe('useAnalysisStore', () => {
  beforeEach(reset)

  it('starts with empty state', () => {
    const state = useAnalysisStore.getState()
    expect(state.parsed).toBeNull()
    expect(state.analysis).toBeNull()
  })

  it('setParsed stores parsed idea data', () => {
    useAnalysisStore.getState().setParsed(MOCK_PARSED)
    expect(useAnalysisStore.getState().parsed).toEqual(MOCK_PARSED)
  })

  it('setAnalysis stores market analysis', () => {
    useAnalysisStore.getState().setAnalysis(MOCK_ANALYSIS)
    const state = useAnalysisStore.getState()
    expect(state.analysis.tam).toBe(500000000)
    expect(state.analysis.competitors).toHaveLength(3)
  })

  it('clear resets both fields', () => {
    useAnalysisStore.getState().setParsed(MOCK_PARSED)
    useAnalysisStore.getState().setAnalysis(MOCK_ANALYSIS)
    useAnalysisStore.getState().clear()

    const state = useAnalysisStore.getState()
    expect(state.parsed).toBeNull()
    expect(state.analysis).toBeNull()
  })

  it('parsed and analysis are independent', () => {
    useAnalysisStore.getState().setParsed(MOCK_PARSED)
    expect(useAnalysisStore.getState().analysis).toBeNull()

    useAnalysisStore.getState().setAnalysis(MOCK_ANALYSIS)
    expect(useAnalysisStore.getState().parsed).toEqual(MOCK_PARSED)
  })
})
