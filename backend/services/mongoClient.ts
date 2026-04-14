/**
 * MongoDB Command Client - TypeScript version for Pulse side.
 * 
 * This provides the same functionality as the Python mongo_client.py
 * but can be used in any TypeScript/JavaScript context (Node.js, browser).
 * 
 * Usage:
 *     import { MongoCommandClient } from './mongoClient';
 *     
 *     const client = new MongoCommandClient(db);
 *     await client.notifyOrderFilled({
 *         symbol: 'NVDA',
 *         orderId: 'ord_123',
 *         fillPrice: 142.35,
 *         quantity: 50,
 *         side: 'BUY'
 *     });
 */

// ==================== Types ====================

export interface OrderFilledParams {
  symbol: string;
  order_id: string;
  fill_price: number;
  quantity: number;
  side: 'BUY' | 'SELL';
  pnl_realized?: number;
  fees?: number;
  order_type?: 'MARKET' | 'LIMIT' | 'STOP';
  trading_mode?: 'paper' | 'live';
  metadata?: Record<string, unknown>;
}

export interface PositionUpdateParams {
  symbol: string;
  position_size: number;
  entry_price?: number;
  current_pnl_pct?: number;
  current_pnl_dollar?: number;
  market_value?: number;
  metadata?: Record<string, unknown>;
}

export interface AccountUpdateParams {
  symbol: string;
  buying_power: number;
  total_equity: number;
  day_pnl_pct?: number;
  day_pnl_dollar?: number;
  metadata?: Record<string, unknown>;
}

export interface BrokerStatusParams {
  broker_id: string;
  connected: boolean;
  error?: string;
  metadata?: Record<string, unknown>;
}

export interface AutoStopParams {
  symbol: string;
  reason: 'daily_loss_exceeded' | 'consecutive_losses_exceeded';
  limit_value: number;
  current_value: number;
  metadata?: Record<string, unknown>;
}

export interface PulseStatusParams {
  trading_mode?: 'paper' | 'live';
  simulate_24_7?: boolean;
  market_hours_only?: boolean;
  paused?: boolean;
  running?: boolean;
  market_open?: boolean;
  metadata?: Record<string, unknown>;
}

export interface MongoCommandClientConfig {
  collectionName?: string;
}

// ==================== Client Class ====================

export class MongoCommandClient {
  private collection: any; // MongoDB collection
  
  constructor(collection: any, config?: MongoCommandClientConfig) {
    this.collection = collection;
  }
  
  // ==================== Core Method ====================
  
  private async sendCommand(command: Record<string, unknown>): Promise<boolean> {
    try {
      // Add timestamp if not present
      if (!command.timestamp) {
        command.timestamp = new Date().toISOString();
      }
      
      // Ensure symbol is uppercase
      if (command.symbol && typeof command.symbol === 'string') {
        command.symbol = command.symbol.toUpperCase();
      }
      
      await this.collection.insertOne(command);
      console.log(`📤 Sent command: ${command.command_type} | ${command.symbol}`);
      return true;
    } catch (error) {
      console.error(`Failed to send command: ${error}`);
      return false;
    }
  }
  
  // ==================== Pulse → Edge Commands ====================
  
  async notifyOrderFilled(params: OrderFilledParams): Promise<boolean> {
    const command = {
      command_type: 'ORDER_FILLED',
      symbol: params.symbol.toUpperCase(),
      order_id: params.order_id,
      fill_price: params.fill_price,
      quantity: params.quantity,
      side: params.side,
      pnl_realized: params.pnl_realized ?? 0,
      fees: params.fees ?? 0,
      order_type: params.order_type ?? 'MARKET',
      trading_mode: params.trading_mode ?? 'paper',
      metadata: params.metadata ?? {},
    };
    return this.sendCommand(command);
  }
  
  async updatePosition(params: PositionUpdateParams): Promise<boolean> {
    const command = {
      command_type: 'POSITION_UPDATE',
      symbol: params.symbol.toUpperCase(),
      position_size: params.position_size,
      entry_price: params.entry_price ?? null,
      current_pnl_pct: params.current_pnl_pct ?? 0,
      current_pnl_dollar: params.current_pnl_dollar ?? 0,
      market_value: params.market_value ?? null,
      metadata: params.metadata ?? {},
    };
    return this.sendCommand(command);
  }
  
  async updateAccount(params: AccountUpdateParams): Promise<boolean> {
    const command = {
      command_type: 'ACCOUNT_UPDATE',
      symbol: params.symbol.toUpperCase(),
      buying_power: params.buying_power,
      total_equity: params.total_equity,
      day_pnl_pct: params.day_pnl_pct ?? 0,
      day_pnl_dollar: params.day_pnl_dollar ?? 0,
      metadata: params.metadata ?? {},
    };
    return this.sendCommand(command);
  }
  
  async notifyOrderRejected(
    symbol: string,
    orderId: string,
    reason: string,
    exchangeErrorCode?: string
  ): Promise<boolean> {
    const command = {
      command_type: 'ORDER_REJECTED',
      symbol: symbol.toUpperCase(),
      order_id: orderId,
      reason,
      exchange_error_code: exchangeErrorCode ?? null,
      metadata: {},
    };
    return this.sendCommand(command);
  }
  
  async notifyOrderCancelled(
    symbol: string,
    orderId: string,
    reason?: string
  ): Promise<boolean> {
    const command = {
      command_type: 'ORDER_CANCELLED',
      symbol: symbol.toUpperCase(),
      order_id: orderId,
      reason: reason ?? null,
      metadata: {},
    };
    return this.sendCommand(command);
  }
  
  // ==================== Status Commands ====================
  
  async sendPulseStatus(params: PulseStatusParams): Promise<boolean> {
    const command = {
      command_type: 'PULSE_STATUS',
      symbol: 'SYSTEM',
      trading_mode: params.trading_mode ?? 'paper',
      simulate_24_7: params.simulate_24_7 ?? false,
      market_hours_only: params.market_hours_only ?? true,
      paused: params.paused ?? false,
      running: params.running ?? false,
      market_open: params.market_open ?? false,
      metadata: params.metadata ?? {},
    };
    return this.sendCommand(command);
  }
  
  async notifyBrokerStatus(params: BrokerStatusParams): Promise<boolean> {
    const command = {
      command_type: 'BROKER_STATUS',
      symbol: 'SYSTEM',
      broker_id: params.broker_id,
      connected: params.connected,
      error: params.error ?? null,
      metadata: params.metadata ?? {},
    };
    return this.sendCommand(command);
  }
  
  async notifyAutoStop(params: AutoStopParams): Promise<boolean> {
    const command = {
      command_type: 'AUTO_STOP_TRIGGERED',
      symbol: params.symbol.toUpperCase(),
      reason: params.reason,
      limit_value: params.limit_value,
      current_value: params.current_value,
      metadata: params.metadata ?? {},
    };
    return this.sendCommand(command);
  }
  
  // ==================== Query Methods ====================
  
  async getRecentCommands(
    commandType?: string,
    symbol?: string,
    limit: number = 100
  ): Promise<any[]> {
    const query: Record<string, unknown> = {};
    if (commandType) query.command_type = commandType;
    if (symbol) query.symbol = symbol.toUpperCase();
    
    return this.collection
      .find(query)
      .sort({ timestamp: -1 })
      .limit(limit)
      .toArray();
  }
  
  async clearCommands(olderThanHours?: number): Promise<number> {
    const query: Record<string, unknown> = {};
    
    if (olderThanHours) {
      const cutoff = new Date();
      cutoff.setHours(cutoff.getHours() - olderThanHours);
      query.timestamp = { $lt: cutoff.toISOString() };
    }
    
    const result = await this.collection.deleteMany(query);
    console.log(`Cleared ${result.deletedCount} commands`);
    return result.deletedCount;
  }
}

// ==================== Factory Function ====================

export function createMongoCommandClient(mongoDb: any, config?: MongoCommandClientConfig): MongoCommandClient {
  const collectionName = config?.collectionName ?? 'commands';
  const collection = mongoDb.collection(collectionName);
  return new MongoCommandClient(collection, config);
}

// ==================== React Hook ====================

import { useState, useEffect, useCallback } from 'react';

interface UseMongoCommandsOptions {
  mongoDb?: any;
  collectionName?: string;
}

export function useMongoCommands(options: UseMongoCommandsOptions = {}) {
  const [client, setClient] = useState<MongoCommandClient | null>(null);
  const [connected, setConnected] = useState(false);
  
  useEffect(() => {
    if (options.mongoDb) {
      const newClient = createMongoCommandClient(options.mongoDb, {
        collectionName: options.collectionName,
      });
      setClient(newClient);
      setConnected(true);
    }
  }, [options.mongoDb, options.collectionName]);
  
  const notifyOrderFilled = useCallback(
    (params: OrderFilledParams) => client?.notifyOrderFilled(params),
    [client]
  );
  
  const updatePosition = useCallback(
    (params: PositionUpdateParams) => client?.updatePosition(params),
    [client]
  );
  
  const sendPulseStatus = useCallback(
    (params: PulseStatusParams) => client?.sendPulseStatus(params),
    [client]
  );
  
  return {
    connected,
    notifyOrderFilled,
    updatePosition,
    sendPulseStatus,
    client,
  };
}