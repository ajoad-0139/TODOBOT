import { useState } from 'react'
import ChatMessage from './ChatMessage'
import ChatInput from './ChatInput'
import type { ChatMessageType } from '../../Types/chat'

const dummyMessages: ChatMessageType[] = [
  { id: 1, role: 'user', text: 'Move my presentation task to In progress.' },
  {
    id: 2,
    role: 'assistant',
    text: 'Done. I moved “Finish AI presentation” to In progress.',
    linkText: 'View updated task board',
  },
  { id: 3, role: 'user', text: 'Find tasks related to documentation.' },
  { id: 4, role: 'assistant', text: 'Found: Update API documentation' },
]

const ChatSection = () => {
  const [input, setInput] = useState('')

  return (
    <div className="flex flex-col flex-1 min-h-0 gap-4 p-6 bg-[#fafbff] border border-[#dde4f5] rounded-3xl">
      <div className="shrink-0 flex items-center gap-3 px-5 py-4 bg-[#e8eefb] rounded-xl">
        <span className="text-xl text-[#1b3a73]">✦</span>
        <h2 className="text-xl font-bold text-[#1b3a73]">AI Assistant</h2>
      </div>
      <p className="shrink-0 px-2 text-sm text-[#6b7a99]">Manage everything with a message</p>
      <div className="flex-1 min-h-0 flex flex-col gap-5 overflow-y-auto">
        {dummyMessages.map((message) => <ChatMessage key={message.id} message={message} />)}
      </div>
      <ChatInput value={input} onChange={setInput} />
    </div>
  )
}

export default ChatSection