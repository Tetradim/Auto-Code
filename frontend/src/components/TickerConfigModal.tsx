import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { api } from '@/lib/api';

// Default providers - alpaca first for real-time, yfinance as fallback
const DEFAULT_PROVIDERS = ['alpaca', 'yfinance'];
const ALL_PROVIDERS = ['alpaca', 'polygon', 'finnhub', 'yfinance'];

interface TickerConfigModalProps {
  symbol: string;
  isOpen: boolean;
  onClose: () => void;
  onRefresh?: () => void;
}

export const TickerConfigModal: React.FC<TickerConfigModalProps> = ({
  symbol,
  isOpen,
  onClose,
  onRefresh,
}) => {
  const [localConfig, setLocalConfig] = useState({
    price_providers: DEFAULT_PROVIDERS,
  });
  const [saving, setSaving] = useState(false);
  const [initialLoad, setInitialLoad] = useState(true);

  // Load existing config when modal opens
  useEffect(() => {
    if (isOpen && symbol) {
      setInitialLoad(true);
      api.getTickerConfig(symbol).then((config) => {
        setLocalConfig({
          price_providers: config?.price_providers || DEFAULT_PROVIDERS,
        });
        setInitialLoad(false);
      }).catch(() => {
        setLocalConfig({
          price_providers: DEFAULT_PROVIDERS,
        });
        setInitialLoad(false);
      });
    }
  }, [isOpen, symbol]);

  const handleSave = async () => {
    setSaving(true);
    try {
      // Save price providers config
      await api.updateTickerConfig(symbol, {
        price_providers: localConfig.price_providers,
      });

      onClose();
      onRefresh?.();
    } catch (error) {
      console.error('Failed to save config:', error);
    } finally {
      setSaving(false);
    }
  };

  const toggleProvider = (provider: string) => {
    let updated = [...(localConfig.price_providers || DEFAULT_PROVIDERS)];

    if (updated.includes(provider)) {
      updated = updated.filter((p) => p !== provider);
    } else {
      updated.push(provider);
    }

    // Always keep at least one provider
    if (updated.length === 0) {
      updated = ['yfinance'];
    }

    setLocalConfig({ ...localConfig, price_providers: updated });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-lg bg-zinc-900 rounded-2xl border border-zinc-700 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-700">
          <h2 className="text-lg font-semibold text-white">
            Configure {symbol}
          </h2>
          <button
            onClick={onClose}
            className="p-2 text-zinc-400 hover:text-white transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-4">
          {initialLoad ? (
            <div className="text-sm text-zinc-400">Loading...</div>
          ) : (
            <>
              {/* Price Providers Section */}
              <div className="space-y-4 border-t border-zinc-700 pt-6">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-white">
                    Price Data Providers
                  </label>
                  <span className="text-xs text-zinc-500">
                    Higher priority tried first
                  </span>
                </div>

                <div className="flex flex-wrap gap-3">
                  {ALL_PROVIDERS.map((provider) => (
                    <label
                      key={provider}
                      className={`flex items-center gap-2 px-4 py-2.5 rounded-2xl cursor-pointer transition-all border ${
                        localConfig.price_providers?.includes(provider)
                          ? 'bg-green-900/30 border-green-600'
                          : 'bg-zinc-800 border-transparent hover:border-zinc-600'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={
                          localConfig.price_providers?.includes(provider) ??
                          (provider === 'alpaca' || provider === 'yfinance')
                        }
                        onChange={() => toggleProvider(provider)}
                        className="accent-green-500"
                      />
                      <span className="capitalize text-sm text-white">
                        {provider}
                      </span>
                    </label>
                  ))}
                </div>

                <p className="text-xs text-zinc-500 mt-1">
                  Current order:{' '}
                  <span className="font-mono text-green-400">
                    {localConfig.price_providers?.join(' → ') ||
                      'alpaca → yfinance'}
                  </span>
                </p>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-zinc-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-zinc-400 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || initialLoad}
            className="px-4 py-2 text-sm bg-green-600 hover:bg-green-500 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
};