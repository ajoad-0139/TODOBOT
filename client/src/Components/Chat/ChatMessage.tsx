import type { ChatMessageType, ClarificationCandidate } from '../../Types/chat'

interface ChatMessageProps {
  message: ChatMessageType
  isLast: boolean
  disabled: boolean
  onConfirm: (operationId: string) => void
  onCancel: (operationId: string) => void
  onPick: (candidate: ClarificationCandidate) => void
}

const stateLabels = {
  open: '',
  confirmed: 'Confirmed',
  cancelled: 'Cancelled',
  expired: 'No longer pending',
}

const ChatMessage = ({ message, isLast, disabled, onConfirm, onCancel, onPick }: ChatMessageProps) => {
  const isUser = message.role === 'user'
  const isError = message.kind === 'error'

  let bubbleStyle = 'bg-white border border-[#e1e6f0]'
  if (isUser) bubbleStyle = 'bg-[#e4ebfa]'
  if (isError) bubbleStyle = 'bg-[#ffe9e6] border border-[#f3c4bd] text-[#b84436]'

  const isOpenConfirmation = message.kind === 'confirmation' && message.confirmationState === 'open'
  const showCandidates = message.kind === 'clarification' && isLast && message.candidates

  return (
    <div className={`w-full flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[85%] px-4 py-3 rounded-xl text-sm text-[#18284b] ${bubbleStyle}`}>
        <p className="whitespace-pre-line">{message.text}</p>

        {isOpenConfirmation && message.operationId && (
          <div className="flex gap-2 mt-3">
            <button
              type="button"
              disabled={disabled}
              onClick={() => onConfirm(message.operationId as string)}
              className="px-4 py-1.5 text-sm font-bold text-white bg-[#2f5bcc] rounded-lg hover:bg-[#2a51b8] disabled:bg-[#9db3e6] disabled:cursor-not-allowed"
            >
              Confirm
            </button>
            <button
              type="button"
              disabled={disabled}
              onClick={() => onCancel(message.operationId as string)}
              className="px-4 py-1.5 text-sm font-bold text-[#2f5bcc] bg-white border border-[#6b94e8] rounded-lg hover:bg-[#f0f4fd] disabled:text-[#9db3e6] disabled:cursor-not-allowed"
            >
              Cancel
            </button>
          </div>
        )}

        {message.kind === 'confirmation' && !isOpenConfirmation && message.confirmationState && (
          <p className="mt-2 text-xs font-bold text-[#7b88a6]">{stateLabels[message.confirmationState]}</p>
        )}

        {showCandidates && (
          <div className="flex flex-col gap-2 mt-3">
            {message.candidates?.map((candidate) => (
              <button
                key={candidate.id}
                type="button"
                disabled={disabled}
                onClick={() => onPick(candidate)}
                className="px-3 py-1.5 text-left text-sm font-bold text-[#2f5bcc] bg-[#f0f4fd] border border-[#c9d7f5] rounded-lg hover:bg-[#e4ebfa] disabled:text-[#9db3e6] disabled:cursor-not-allowed"
              >
                {candidate.title}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default ChatMessage