import { useState } from 'react'
import ChatSection from '../Components/Chat/ChatSection'
import TaskList from '../Components/Tasks/TaskLIst'

const Home = () => {
  const [refreshKey, setRefreshKey] = useState(0)

  const refreshTasks = () => setRefreshKey((prev) => prev + 1)

  return (
    <div className="flex flex-col h-full w-full bg-white border border-[#e1e6f0] rounded-[2rem] overflow-hidden">
      <div className="shrink-0 flex justify-between items-center px-6 sm:px-10 py-6 bg-[#172a4d]">
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-wide text-white">TASKFLOW</h1>
        <span className="text-xs font-bold tracking-wide text-[#b9c7e6] lg:mr-[10%]">AI TASK MANAGER</span>
      </div>
      <div className="flex-1 min-h-0 flex flex-col lg:flex-row gap-6 p-6 sm:p-8 overflow-y-auto lg:overflow-hidden">
        <div className="flex flex-col shrink-0 lg:shrink lg:flex-1 lg:min-w-0 lg:min-h-0">
          <TaskList refreshKey={refreshKey} />
        </div>
        <div className="flex flex-col h-[560px] shrink-0 lg:h-auto lg:shrink lg:w-[34%]">
          <ChatSection onTasksChanged={refreshTasks} />
        </div>
      </div>
    </div>
  )
}

export default Home