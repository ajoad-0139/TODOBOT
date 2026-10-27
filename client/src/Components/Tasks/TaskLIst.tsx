import  { useEffect, useState } from 'react'
import TaskCard from './TaskCard'
import { getTasks } from '../../Services/taskService'
import type { Task } from '../../Types/task'

interface TaskListProps {
  refreshKey: number
}

const TaskList = ({ refreshKey }: TaskListProps) => {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let ignore = false

    const fetchTasks = async () => {
      try {
        const data = await getTasks()
        if (!ignore) {
          setTasks(data)
          setError(null)
        }
      } catch (err) {
        if (!ignore) setError('Could not load tasks. Please try again later.')
      } finally {
        if (!ignore) setLoading(false)
      }
    }

    fetchTasks()
    return () => {
      ignore = true
    }
  }, [refreshKey])

  return (
    <div className="flex flex-col gap-5 lg:flex-1 lg:min-h-0">
      <div className="shrink-0 px-2">
        <h1 className="text-4xl font-extrabold text-[#18284b]">My tasks</h1>
        <p className="mt-1 text-base text-[#6b7a99]">Organize tasks by asking your AI assistant</p>
      </div>
      <div className="flex flex-col h-[520px] lg:h-auto lg:flex-1 lg:min-h-0 p-7 bg-white border border-[#e1e6f0] rounded-3xl">
        <div className="shrink-0 flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-[#18284b]">Task board</h2>
          <span className="px-6 py-3 bg-[#eef3fb] rounded-xl text-sm font-bold text-[#2d4f8f]">
            All tasks &nbsp;{tasks.length}
          </span>
        </div>
        <div className="flex-1 min-h-0 flex flex-col gap-3 overflow-y-auto">
          {loading && <p className="text-sm text-[#6b7a99] text-center mt-6">Loading tasks...</p>}
          {error && <p className="text-sm text-red-600 text-center mt-6">{error}</p>}
          {!loading && !error && tasks.length === 0 && (
            <p className="text-sm text-[#6b7a99] text-center mt-6">No tasks yet.</p>
          )}
          {tasks.map((task) => <TaskCard key={task.id} task={task} />)}
        </div>
      </div>
    </div>
  )
}

export default TaskList