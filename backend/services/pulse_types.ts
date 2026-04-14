/**
 * Sentinel Pulse ↔ Edge Command Types
 * 
 * These types mirror the Python Pydantic models in shared/commands.py
 * and define the contract for all communication between Edge and Pulse.
 */

// ==================== Command Types ====================

export enum CommandType {
  // Pulse → Edge (Feedback Loop)
  ORDER_FILLED = "ORDER_FILLED",
  POSITION_UPDATE = "POSITION_UPDATE",
  ACCOUNT_UPDATE = "ACCOUNT_UPDATE",
  ORDER_REJECTED = "ORDER_REJECTED",
  ORDER_CANCELLED = "ORDER_CANCELLED",
  
  // Edge → Pulse (Signals)
  SIGNAL_UPDATE = "SIGNAL_UPDATE",
  CORRELATION_ALERT = "CORRELATION_ALERT",
  EMERGENCY_EXIT = "EMERGENCY_EXIT",
}

// ==================== Base Command ====================

export interface BaseCommand {
  command_type: CommandType;
  symbol: string;
  timestamp?: string;  // ISO 8601 datetime
  metadata?: Record<string, unknown>;
}

// ==================== Pulse → Edge Commands ====================

export interface OrderFilledCommand extends BaseCommand {
  command_type: CommandType.ORDER_FILLED;
  order_id: string;
  fill_price: number;
  quantity: number;
  side: "BUY" | "SELL";
  pnl_realized?: number;
  fees?: number;
}

export interface PositionUpdateCommand extends BaseCommand {
  command_type: CommandType.POSITION_UPDATE;
  position_size: number;  // positive = long, negative = short, 0 = flat
  entry_price?: number;
  current_pnl_pct: number;
  current_pnl_dollar: number;
  market_value?: number;
}

export interface AccountUpdateCommand extends BaseCommand {
  command_type: CommandType.ACCOUNT_UPDATE;
  buying_power: number;
  total_equity: number;
  day_pnl_pct: number;
  day_pnl_dollar: number;
}

export interface OrderRejectedCommand extends BaseCommand {
  command_type: CommandType.ORDER_REJECTED;
  order_id: string;
  reason: string;
  exchange_error_code?: string;
}

export interface OrderCancelledCommand extends BaseCommand {
  command_type: CommandType.ORDER_CANCELLED;
  order_id: string;
  reason?: string;
}

// ==================== Edge → Pulse Commands ====================

export type SignalAction = "BUY" | "SELL" | "HOLD" | "EMERGENCY_SELL";

export interface SignalUpdateCommand extends BaseCommand {
  command_type: CommandType.SIGNAL_UPDATE;
  signal_score: number;
  action: SignalAction;
  confidence: number;
  reason: string;
}

export interface CorrelationAlertCommand extends BaseCommand {
  command_type: CommandType.CORRELATION_ALERT;
  correlated_symbols: string[];
  cluster_strength: number;
  recommended_action: "REDUCE_SIZE" | "CLOSE_ALL" | "HOLD";
}

// ==================== Union Types ====================

export type PulseToEdgeCommand = 
  | OrderFilledCommand 
  | PositionUpdateCommand 
  | AccountUpdateCommand 
  | OrderRejectedCommand 
  | OrderCancelledCommand;

export type EdgeToPulseCommand = 
  | SignalUpdateCommand 
  | CorrelationAlertCommand;

export type AnyCommand = PulseToEdgeCommand | EdgeToPulseCommand;

// ==================== API Response Types ====================

export interface PulseHealthStatus {
  available: boolean;
  circuit_state: "CLOSED" | "HALF_OPEN" | "OPEN";
  failure_count: number;
  success_count: number;
  retry_queue_size: number;
}

export interface PositionState {
  size: number;
  entry_price: number;
  entry_time?: string;
  current_pnl_pct: number;
  current_pnl_dollar: number;
  last_updated?: string;
}

export interface AccountState {
  buying_power: number;
  total_equity: number;
  day_pnl_pct: number;
  day_pnl_dollar: number;
}

// ==================== Test Helpers ====================

export const createTestOrderFilled = (symbol: string): OrderFilledCommand => ({
  command_type: CommandType.ORDER_FILLED,
  symbol,
  order_id: `test_${Date.now()}`,
  fill_price: 0,
  quantity: 0,
  side: "BUY",
  pnl_realized: 0,
  fees: 0,
});

export const createTestPositionUpdate = (symbol: string): PositionUpdateCommand => ({
  command_type: CommandType.POSITION_UPDATE,
  symbol,
  position_size: 0,
  current_pnl_pct: 0,
  current_pnl_dollar: 0,
});