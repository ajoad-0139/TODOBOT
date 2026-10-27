export interface ChatMessageType {
  id: number
  role: 'user' | 'assistant'
  text: string
  linkText?: string
}