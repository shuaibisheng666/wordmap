import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 20000,
})

export async function getWordRelations(word) {
  const { data } = await api.get(`/word/${encodeURIComponent(word)}`)
  return data
}

export async function getRandomWord() {
  const { data } = await api.get('/word/random')
  return data
}

export async function getLlmConfig() {
  const { data } = await api.get('/llm-config')
  return data
}

export async function saveLlmConfig(config) {
  const { data } = await api.put('/llm-config', config)
  return data
}
