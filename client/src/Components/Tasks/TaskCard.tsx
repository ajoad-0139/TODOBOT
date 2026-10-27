import type { Task } from '../../Types/task'

interface TaskCardProps {
  task: Task
}

const statusLabels = {
  pending: 'To do',
  in_progress: 'In progress',
  completed: 'Done',
}

const priorityLabels = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
}

const priorityStyles = {
  low: 'bg-[#e2f3ec] text-[#2a7a56]',
  medium: 'bg-[#fff0d6] text-[#9a6a1c]',
  high: 'bg-[#ffe9e6] text-[#b84436]',
}

const getDueLabel = (task: Task) => {
  if (task.status === 'completed') return 'Completed'
  if (!task.due_date) return 'No due date'

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const due = new Date(task.due_date)
  due.setHours(0, 0, 0, 0)
  const days = Math.round((due.getTime() - today.getTime()) / 86400000)

  if (days < 0) return 'Overdue'
  if (days === 0) return 'Today'
  if (days === 1) return 'Tomorrow'
  if (days < 7) return due.toLocaleDateString('en-US', { weekday: 'long' })
  if (days < 14) return 'Next week'
  return due.toLocaleDateString()
}

const TaskCard = ({ task }: TaskCardProps) => {
  const isCompleted = task.status === 'completed'

  return (
    <div className="w-full flex items-center gap-4 px-5 py-4 bg-[#fafbff] border border-[#e3e8f2] rounded-xl">
      <div className={`shrink-0 w-8 h-8 flex justify-center items-center rounded-full border-2 text-sm font-bold ${isCompleted ? 'bg-[#d9f3e6] border-[#8fb3a3] text-[#2e8b57]' : 'bg-[#dbe5f7] border-[#9aa9c9]'}`}>
        {isCompleted && '✓'}
      </div>
      <div className="flex-1 min-w-0">
        <h3 className={`text-lg font-bold truncate ${isCompleted ? 'text-[#8a97ae]' : 'text-[#18284b]'}`}>
          {task.title}
        </h3>
        {task.description && (
          <p className="text-sm text-[#6b7a99] truncate">{task.description}</p>
        )}
        <p className="text-sm text-[#7b88a6]">
          {getDueLabel(task)} <span className="mx-1">•</span> {statusLabels[task.status]}
        </p>
      </div>
      <span className={`shrink-0 w-24 sm:w-32 px-4 py-2.5 rounded-lg text-sm font-bold ${priorityStyles[task.priority]}`}>
        {priorityLabels[task.priority]}
      </span>
    </div>
  )
}

export default TaskCard