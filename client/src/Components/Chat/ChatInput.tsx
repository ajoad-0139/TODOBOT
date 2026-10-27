interface ChatInputProps {
  value: string
  onChange: (value: string) => void
}

const ChatInput = ({ value, onChange }: ChatInputProps) => {
  return (
    <div className="shrink-0 flex flex-col gap-1 px-4 py-3 bg-white border-2 border-[#6b94e8] rounded-2xl">
      <label className="text-xs font-bold tracking-wide text-[#4f73c4]">YOUR INSTRUCTION</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Type a task instruction..."
        className="w-full text-base text-[#18284b] outline-none placeholder:text-[#9aa6bd]"
      />
      <div className="flex justify-between items-end gap-3 mt-1">
        <p className="text-xs text-[#a3adc2]">e.g. Complete the weekly report</p>
        <button
          type="button"
          className="px-6 py-2 text-sm font-bold text-white bg-[#2f5bcc] rounded-lg hover:bg-[#2a51b8]"
        >
          Send
        </button>
      </div>
    </div>
  )
}

export default ChatInput