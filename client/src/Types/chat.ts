export type ChatMessageKind = 'text' | 'confirmation' | 'clarification' | 'error'
export type ConfirmationState = 'open' | 'confirmed' | 'cancelled' | 'expired'

export interface ClarificationCandidate {
  id: number
  title: string
}

export interface ChatMessageType {
  id: number
  role: 'user' | 'assistant'
  text: string
  kind: ChatMessageKind
  operationId?: string
  confirmationState?: ConfirmationState
  candidates?: ClarificationCandidate[]
}

// What the server sends
export type ServerEventType =
  | 'connection_ready'
  | 'assistant_message'
  | 'tool_status'
  | 'clarification_request'
  | 'confirmation_required'
  | 'operation_success'
  | 'operation_error'
  | 'operation_cancelled'
  | 'error'

export interface ServerEvent {
  type: ServerEventType
  message: string
  request_id?: string
  operation_id?: string
  operation?: string
  data?: Record<string, any>
}

// What the client sends
export type ClientMessage =
  | { type: 'chat_message'; request_id: string; message: string }
  | { type: 'confirm'; request_id: string; operation_id: string }
  | { type: 'cancel'; request_id: string; operation_id: string }