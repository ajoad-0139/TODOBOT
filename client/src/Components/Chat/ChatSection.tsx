import { useEffect, useRef, useState } from 'react'
import ChatMessage from './ChatMessage'
import ChatInput from './ChatInput'
import type {
  ChatMessageType,
  ClarificationCandidate,
  ClientMessage,
  ConfirmationState,
  ServerEvent,
} from '../../Types/chat'
import { getChatSocketUrl, getConversationId, loadMessages, makeId, saveMessages } from '../../Services/chatService'

interface ChatSectionProps {
  onTasksChanged: () => void
}

const RECONNECT_DELAY_MS = 2000

const ChatSection = ({ onTasksChanged }: ChatSectionProps) => {
  const [messages, setMessages] = useState<ChatMessageType[]>(() => loadMessages())
  const [input, setInput] = useState('')
  const [connected, setConnected] = useState(false)
  const [thinking, setThinking] = useState(false)

  const socketRef = useRef<WebSocket | null>(null)
  const lastSentRef = useRef<ClientMessage | null>(null)
  const nextId = useRef(Date.now())
  const bottomRef = useRef<HTMLDivElement>(null)

  const addMessage = (message: Omit<ChatMessageType, 'id'>) => {
    nextId.current += 1
    const id = nextId.current
    setMessages((prev) => [...prev, { ...message, id }])
  }

  const stopThinking = () => {
    lastSentRef.current = null
    setThinking(false)
  }

  const markConfirmation = (operationId: string | undefined, state: ConfirmationState) => {
    if (!operationId) return
    setMessages((prev) =>
      prev.map((m) => (m.kind === 'confirmation' && m.operationId === operationId ? { ...m, confirmationState: state } : m))
    )
  }

  const handleEvent = (event: ServerEvent) => {
    switch (event.type) {
      case 'connection_ready': {
        // A request that was never answered is re-sent with the same request_id.
        // The server replays its stored result instead of repeating the operation.
        const unanswered = lastSentRef.current
        if (unanswered) socketRef.current?.send(JSON.stringify(unanswered))
        break
      }
      case 'tool_status':
        if (event.data?.tool === 'create_task' && event.data?.ok) onTasksChanged()
        break
      case 'assistant_message':
        addMessage({ role: 'assistant', kind: 'text', text: event.message })
        stopThinking()
        break
      case 'clarification_request':
        addMessage({ role: 'assistant', kind: 'clarification', text: event.message, candidates: event.data?.candidates })
        stopThinking()
        break
      case 'confirmation_required': {
        nextId.current += 1
        const id = nextId.current
        setMessages((prev) => {
          // The server re-sends a pending confirmation on reconnect: do not show it twice.
          if (prev.some((m) => m.kind === 'confirmation' && m.operationId === event.operation_id)) return prev
          // A new confirmation replaces any older one on the server.
          const older = prev.map((m) =>
            m.kind === 'confirmation' && m.confirmationState === 'open'
              ? { ...m, confirmationState: 'expired' as ConfirmationState }
              : m
          )
          return [
            ...older,
            {
              id,
              role: 'assistant',
              kind: 'confirmation',
              text: event.message,
              operationId: event.operation_id,
              confirmationState: 'open',
            },
          ]
        })
        stopThinking()
        break
      }
      case 'operation_success':
        markConfirmation(event.operation_id, 'confirmed')
        onTasksChanged()
        break
      case 'operation_error':
        if (event.data?.code === 'no_pending_operation') {
          markConfirmation(event.operation_id, 'expired')
          addMessage({ role: 'assistant', kind: 'error', text: event.message })
          stopThinking()
        } else {
          // A step failed after confirmation. Its text is in the summary message that follows.
          markConfirmation(event.operation_id, 'confirmed')
          onTasksChanged()
        }
        break
      case 'operation_cancelled':
        markConfirmation(event.operation_id, 'cancelled')
        addMessage({ role: 'assistant', kind: 'text', text: event.message })
        // A cancel button press ends the turn here. For a normal message, more events follow.
        if (lastSentRef.current && lastSentRef.current.type === 'cancel') stopThinking()
        break
      case 'error':
        addMessage({ role: 'assistant', kind: 'error', text: event.message })
        stopThinking()
        break
    }
  }

  useEffect(() => {
    const conversationId = getConversationId()
    let socket: WebSocket | null = null
    let retryTimer: number | undefined
    let closedByUs = false

    const connect = () => {
      socket = new WebSocket(getChatSocketUrl(conversationId))
      socketRef.current = socket
      socket.onopen = () => setConnected(true)
      socket.onmessage = (e) => {
        try {
          handleEvent(JSON.parse(e.data))
        } catch (err) {
          console.error('Could not read server event', err)
        }
      }
      socket.onclose = () => {
        setConnected(false)
        if (!closedByUs) retryTimer = window.setTimeout(connect, RECONNECT_DELAY_MS)
      }
    }

    connect()
    return () => {
      closedByUs = true
      window.clearTimeout(retryTimer)
      socket?.close()
    }
  }, [])

  useEffect(() => {
    saveMessages(messages)
    bottomRef.current?.scrollIntoView({ block: 'end' })
  }, [messages, thinking])

  const sendPayload = (payload: ClientMessage): boolean => {
    const socket = socketRef.current
    if (!socket || socket.readyState !== WebSocket.OPEN) return false
    lastSentRef.current = payload
    setThinking(true)
    socket.send(JSON.stringify(payload))
    return true
  }

  const sendChat = (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || thinking || !connected) return
    const sent = sendPayload({ type: 'chat_message', request_id: makeId(), message: trimmed })
    if (sent) {
      addMessage({ role: 'user', kind: 'text', text: trimmed })
      setInput('')
    }
  }

  const handleSend = () => sendChat(input)

  const handlePick = (candidate: ClarificationCandidate) => {
    sendChat(`${candidate.title} (#${candidate.id})`)
  }

  const handleConfirm = (operationId: string) => {
    sendPayload({ type: 'confirm', request_id: makeId(), operation_id: operationId })
  }

  const handleCancel = (operationId: string) => {
    sendPayload({ type: 'cancel', request_id: makeId(), operation_id: operationId })
  }

  return (
    <div className="flex flex-col flex-1 min-h-0 gap-4 p-6 bg-[#fafbff] border border-[#dde4f5] rounded-3xl">
      <div className="shrink-0 flex items-center gap-3 px-5 py-4 bg-[#e8eefb] rounded-xl">
        <span className="text-xl text-[#1b3a73]">✦</span>
        <h2 className="flex-1 text-xl font-bold text-[#1b3a73]">AI Assistant</h2>
        <span className={`text-xs font-bold ${connected ? 'text-[#2a7a56]' : 'text-[#9a6a1c]'}`}>
          {connected ? 'Connected' : 'Reconnecting...'}
        </span>
      </div>
      <p className="shrink-0 px-2 text-sm text-[#6b7a99]">Manage everything with a message</p>
      <div className="flex-1 min-h-0 flex flex-col gap-5 overflow-y-auto">
        {messages.length === 0 && (
          <p className="px-2 text-sm text-[#7b88a6]">
            Try: “Create a high-priority task to finish the demo tomorrow” or “Find tasks related to documentation.”
          </p>
        )}
        {messages.map((message, index) => (
          <ChatMessage
            key={message.id}
            message={message}
            isLast={index === messages.length - 1}
            disabled={thinking || !connected}
            onConfirm={handleConfirm}
            onCancel={handleCancel}
            onPick={handlePick}
          />
        ))}
        {thinking && (
          <div className="w-full flex justify-start">
            <div className="px-4 py-3 rounded-xl text-sm text-[#7b88a6] bg-white border border-[#e1e6f0]">Thinking...</div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <ChatInput value={input} onChange={setInput} onSend={handleSend} disabled={!connected || thinking} />
    </div>
  )
}

export default ChatSection