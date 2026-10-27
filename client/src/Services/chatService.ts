import { API_BASE_URL } from './taskService'
import type { ChatMessageType } from '../Types/chat'

const CONVERSATION_KEY = 'taskflow_conversation_id'
const MESSAGES_KEY = 'taskflow_chat_messages'
const MAX_STORED_MESSAGES = 100

export const makeId = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 12)

// The backend accepts 8-64 letters, digits, "-" and "_".
export const getConversationId = (): string => {
  try {
    const saved = localStorage.getItem(CONVERSATION_KEY)
    if (saved) return saved
    const created = `conv_${makeId()}`
    localStorage.setItem(CONVERSATION_KEY, created)
    return created
  } catch (err) {
    return `conv_${makeId()}`
  }
}

export const getChatSocketUrl = (conversationId: string): string => {
  const base = (import.meta.env.VITE_WS_BASE_URL || API_BASE_URL).replace(/\/$/, '')
  return `${base.replace(/^http/, 'ws')}/ws/chat/${conversationId}`
}

export const loadMessages = (): ChatMessageType[] => {
  try {
    const saved = localStorage.getItem(MESSAGES_KEY)
    return saved ? JSON.parse(saved) : []
  } catch (err) {
    return []
  }
}

export const saveMessages = (messages: ChatMessageType[]) => {
  try {
    localStorage.setItem(MESSAGES_KEY, JSON.stringify(messages.slice(-MAX_STORED_MESSAGES)))
  } catch (err) {
    // storage unavailable: the chat still works, it just will not survive a reload
  }
}