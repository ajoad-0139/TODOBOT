import type{ Task } from '../Types/task'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const getTasks = async (): Promise<Task[]> => {
  const response = await fetch(`${API_BASE_URL}/api/v1/tasks/`)
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`)
  }
  return response.json()
}