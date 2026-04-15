/**
 * Paper Trading Dashboard
 * Simulates real trading with mock execution, no real broker needed
 */
import React, { useEffect, useState } from 'react';
import { FlaskConical, Play, Pause, RefreshCw, TrendingUp, TrendingDown, Wallet, Activity, Plus, Minus, X } from 'lucide-react';

interface Order {
  order_id: string;
  symbol: string;
  side: string;
  quantity: number;
  price: number;
  status: string;
  created_at: string;
}

interface Position {
  symbol: string;
  quantity: number;
  avg_cost: number;
  market_value: number;
}

interface AccountState {
  cash: number;
  equity: number;
  buying_power: number;
  positions: Position[];
}

interface TradeFormData {
  symbol: string;
  side: 'buy' | 'sell';
  quantity: number;
  orderType: 'market' | 'limit';
  limitPrice: number;
}

export function PaperTrading() {
  const [active, setActive] = useState(false);
  const [account, setAccount] = useState<AccountState | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState<TradeFormData>({
    symbol: '',
    side: 'buy',
    quantity: 1,
    orderType: 'market',
    limitPrice: 0
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchAccount();
    const interval = setInterval(fetchAccount, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchAccount = async () => {
    try {
      const response = await fetch('/api/paper/account');
      if (response.ok) {
        const data = await response.json();
        setAccount(data);
        
        // Fetch orders
        const ordersRes = await fetch('/api/paper/orders');
        if (ordersRes.ok) {
          const ordersData = await ordersRes.json();
          setOrders(ordersData.orders || []);
        }
      }
    } catch (err) {
      console.error('Paper trading not available');
    }
    setLoading(false);
  };

  const handleSubmitOrder = async () => {
    setSubmitting(true);
    try {
      const response = await fetch('/api/paper/order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: formData.symbol.toUpperCase(),
          side: formData.side,
          quantity: formData.quantity,
          order_type: formData.orderType,
          price: formData.orderType === 'limit' ? formData.limitPrice : null
        })
      });
      
      if (response.ok) {
        setShowForm(false);
        setFormData({ symbol: '', side: 'buy', quantity: 1, orderType: 'market', limitPrice: 0 });
        fetchAccount();
      }
    } catch (err) {
      console.error('Order failed:', err);
    }
    setSubmitting(false);
  };

  const handleCancelOrder = async (orderId: string) => {
    try {
      await fetch(`/api/paper/order/${orderId}/cancel`, { method: 'POST' });
      fetchAccount();
    } catch (err) {
      console.error('Cancel failed:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-6 h-6 animate-spin text-emerald-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${active ? 'bg-emerald-500/20' : 'bg-gray-700'}`}>
            <FlaskConical className={`w-5 h-5 ${active ? 'text-emerald-400' : 'text-gray-400'}`} />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Paper Trading</h2>
            <p className="text-sm text-gray-400">Mock execution, no real money</p>
          </div>
        </div>
        
        <button
          onClick={() => setActive(!active)}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
            active 
              ? 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30' 
              : 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30'
          }`}
        >
          {active ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          {active ? 'Pause Session' : 'Start Session'}
        </button>
      </div>

      {/* Account Summary */}
      {account && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
            <div className="flex items-center gap-2 text-gray-400 mb-2">
              <Wallet className="w-4 h-4" />
              <span className="text-sm">Cash</span>
            </div>
            <p className="text-2xl font-bold text-white">${account.cash.toLocaleString()}</p>
          </div>
          
          <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
            <div className="flex items-center gap-2 text-gray-400 mb-2">
              <Activity className="w-4 h-4" />
              <span className="text-sm">Equity</span>
            </div>
            <p className="text-2xl font-bold text-white">${account.equity.toLocaleString()}</p>
          </div>
          
          <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
            <div className="flex items-center gap-2 text-gray-400 mb-2">
              <TrendingUp className="w-4 h-4" />
              <span className="text-sm">Buying Power</span>
            </div>
            <p className="text-2xl font-bold text-white">${account.buying_power.toLocaleString()}</p>
          </div>
          
          <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
            <div className="flex items-center gap-2 text-gray-400 mb-2">
              <TrendingDown className="w-4 h-4" />
              <span className="text-sm">Positions</span>
            </div>
            <p className="text-2xl font-bold text-white">{account.positions.length}</p>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="flex gap-3">
        <button
          onClick={() => setShowForm(true)}
          className="bg-emerald-500 hover:bg-emerald-600 text-white font-medium py-2 px-4 rounded-lg transition-colors flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          New Order
        </button>
      </div>

      {/* Order Form Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-bold text-white mb-4">Place Paper Order</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Symbol</label>
                <input
                  type="text"
                  value={formData.symbol}
                  onChange={(e) => setFormData({ ...formData, symbol: e.target.value.toUpperCase() })}
                  placeholder="AAPL, NVDA, BTC"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                />
              </div>
              
              <div className="flex gap-4">
                <button
                  onClick={() => setFormData({ ...formData, side: 'buy' })}
                  className={`flex-1 py-2 rounded-lg font-medium transition-colors ${
                    formData.side === 'buy' 
                      ? 'bg-emerald-500 text-white' 
                      : 'bg-gray-800 text-gray-400'
                  }`}
                >
                  <Plus className="w-4 h-4 inline mr-1" />
                  Buy
                </button>
                <button
                  onClick={() => setFormData({ ...formData, side: 'sell' })}
                  className={`flex-1 py-2 rounded-lg font-medium transition-colors ${
                    formData.side === 'sell' 
                      ? 'bg-red-500 text-white' 
                      : 'bg-gray-800 text-gray-400'
                  }`}
                >
                  <Minus className="w-4 h-4 inline mr-1" />
                  Sell
                </button>
              </div>
              
              <div>
                <label className="block text-sm text-gray-400 mb-1">Quantity</label>
                <input
                  type="number"
                  value={formData.quantity}
                  onChange={(e) => setFormData({ ...formData, quantity: parseFloat(e.target.value) || 0 })}
                  min="0.01"
                  step="0.01"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                />
              </div>
              
              <div>
                <label className="block text-sm text-gray-400 mb-1">Order Type</label>
                <select
                  value={formData.orderType}
                  onChange={(e) => setFormData({ ...formData, orderType: e.target.value as 'market' | 'limit' })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                >
                  <option value="market">Market</option>
                  <option value="limit">Limit</option>
                </select>
              </div>
              
              {formData.orderType === 'limit' && (
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Limit Price</label>
                  <input
                    type="number"
                    value={formData.limitPrice}
                    onChange={(e) => setFormData({ ...formData, limitPrice: parseFloat(e.target.value) || 0 })}
                    step="0.01"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
              )}
            </div>
            
            <div className="flex gap-3 mt-6">
              <button
                onClick={handleSubmitOrder}
                disabled={submitting || !formData.symbol}
                className="flex-1 bg-emerald-500 hover:bg-emerald-600 disabled:bg-gray-600 text-white font-medium py-2.5 rounded-lg transition-colors"
              >
                {submitting ? <RefreshCw className="w-4 h-4 animate-spin inline" /> : 'Submit Order'}
              </button>
              <button
                onClick={() => setShowForm(false)}
                className="flex-1 bg-gray-700 hover:bg-gray-600 text-white font-medium py-2.5 rounded-lg transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Positions */}
      <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
        <h3 className="text-lg font-semibold text-white mb-4">Open Positions</h3>
        {account && account.positions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-gray-400 text-sm border-b border-gray-700">
                  <th className="pb-3 font-medium">Symbol</th>
                  <th className="pb-3 font-medium">Quantity</th>
                  <th className="pb-3 font-medium">Avg Cost</th>
                  <th className="pb-3 font-medium">Market Value</th>
                </tr>
              </thead>
              <tbody>
                {account.positions.map((pos) => (
                  <tr key={pos.symbol} className="border-b border-gray-700/50">
                    <td className="py-3 text-white font-medium">{pos.symbol}</td>
                    <td className="py-3 text-gray-300">{pos.quantity.toFixed(2)}</td>
                    <td className="py-3 text-gray-300">${pos.avg_cost.toFixed(2)}</td>
                    <td className="py-3 text-gray-300">${pos.market_value.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8">No open positions</p>
        )}
      </div>

      {/* Pending Orders */}
      <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
        <h3 className="text-lg font-semibold text-white mb-4">Pending Orders</h3>
        {orders.filter(o => o.status === 'pending').length > 0 ? (
          <div className="space-y-2">
            {orders.filter(o => o.status === 'pending').map((order) => (
              <div key={order.order_id} className="flex items-center justify-between bg-gray-800 rounded-lg p-3">
                <div className="flex items-center gap-3">
                  <span className={`font-medium ${order.side === 'buy' ? 'text-emerald-400' : 'text-red-400'}`}>
                    {order.side.toUpperCase()}
                  </span>
                  <span className="text-white">{order.quantity} {order.symbol}</span>
                  {order.price && <span className="text-gray-400">@ ${order.price.toFixed(2)}</span>}
                </div>
                <button
                  onClick={() => handleCancelOrder(order.order_id)}
                  className="p-1 hover:bg-gray-700 rounded"
                >
                  <X className="w-4 h-4 text-gray-400" />
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8">No pending orders</p>
        )}
      </div>
    </div>
  );
}