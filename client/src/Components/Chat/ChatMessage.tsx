import type { ChatMessageType } from '../../Types/chat'

interface ChatMessageProps {
  message: ChatMessageType
}

const ChatMessage = ({ message }: ChatMessageProps) => {
  const isUser = message.role === 'user'

  return (
    <div className={`w-full flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[85%] px-4 py-3 rounded-xl text-sm text-[#18284b] ${isUser ? 'bg-[#e4ebfa]' : 'bg-white border border-[#e1e6f0]'}`}>
        <p>{message.text}</p>
        {message.linkText && (
          <p className="mt-2 font-bold text-[#2f66d6]">{message.linkText}</p>
        )}
      </div>
    </div>
  )
}

export default ChatMessage