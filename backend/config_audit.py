"""Config validation and audit for Sentinel Edge.

Provides:
- YAML config schema validation
- Exchange permissions check
- Minimum risk settings enforcement
- Config hash generation for trade attribution
- Semantic versioning for strategy params

Usage:
    from config_audit import ConfigValidator, ConfigHasher
    
    # Validate config
    validator = ConfigValidator(config_path=Path("/app/config.yaml"))
    await validator.validate()
    
    # Generate config hash for trade
    hasher = ConfigHasher()
    config_hash = hasher.hash_config(config_dict)
    
    # CLI:
    # python -m config_audit validate --config=/app/config.yaml
"""
import hashlib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# Config Schema
# ═══════════════════════════════════════════════════════════

REQUIRED_FIELDS = [
    "strategy.name",
    "strategy.version",
    "risk.max_position_size",
    "risk.max_drawdown",
]

RISK_DEFAULTS = {
    "max_position_size": 0.05,  # 5% max
    "max_drawdown": 0.15,       # 15% max
    "stop_loss_pct": 0.01,      # 1% stop
    "take_profit_pct": 0.02,    # 2% take
}

EXCHANGE_REQUIREMENTS = {
    "binance": {
        "required_permissions": ["spot", "margin"],
        "min_balance": 100,  # USD
    },
    "coinbase": {
        "required_permissions": ["trade", "wallet"],
        "min_balance": 100,
    },
    "kraken": {
        "required_permissions": ["trade"],
        "min_balance": 100,
    },
}


# ═══════════════════════════════════════════════════════════
# Validation Result
# ═══════════════════════════════════════════════════════════

@dataclass
class ValidationResult:
    """Config validation result."""
    valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


# ═══════════════════════════════════════════════════════════

class ConfigValidator:
    """Validates YAML config for Sentinel Edge.
    
    Checks:
    - Required fields present
    - Schema validation
    - Exchange permissions
    - Risk settings within limits
    - Strategy version semantic
    """
    
    def __init__(self, config_path: Path = None, config_dict: Dict = None) -> None:
        self.config_path = config_path
        self.config = config_dict or {}
        
    async def validate(self) -> ValidationResult:
        """Run full validation."""
        errors = []
        warnings = []
        
        # Load file if path provided
        if self.config_path:
            config = await self._load_config()
            self.config = config
        else:
            config = self.config
            
        # 1. Required fields
        errors.extend(self._check_required_fields(config))
        
        # 2. Strategy version semantic
        errors.extend(self._check_strategy_version(config))
        
        # 3. Risk settings
        errors.extend(self._check_risk_settings(config))
        warnings.extend(self._warn_risk_settings(config))
        
        # 4. Exchange permissions
        errors.extend(self._check_exchange(config))
        
        # 5. Symbol validity
        warnings.extend(self._check_symbols(config))
        
        # 6. General schema
        warnings.extend(self._check_schema(config))
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
    
    async def _load_config(self) -> Dict:
        """Load YAML config."""
        import yaml
        with open(self.config_path) as f:
            return yaml.safe_load(f)
    
    def _check_required_fields(self, config: Dict) -> List[str]:
        """Check required fields exist."""
        errors = []
        for field in REQUIRED_FIELDS:
            parts = field.split(".")
            current = config
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    errors.append(f"Missing required field: {field}")
                    break
        return errors
    
    def _check_strategy_version(self, config: Dict) -> List[str]:
        """Check strategy version is semantic."""
        errors = []
        strategy = config.get("strategy", {})
        version = strategy.get("version", "0.0.0")
        
        # Semantic version pattern: major.minor.patch
        if not re.match(r'^\d+\.\d+\.\d+$', version):
            errors.append(f"Invalid strategy version: {version}. Use semantic (e.g., 1.0.0)")
        
        return errors
    
    def _check_risk_settings(self, config: Dict) -> List[str]:
        """Check risk settings within safe limits."""
        errors = []
        risk = config.get("risk", {})
        
        # Max position size
        max_pos = risk.get("max_position_size", RISK_DEFAULTS["max_position_size"])
        if max_pos > 0.20:
            errors.append(f"max_position_size {max_pos} exceeds 20% - too risky")
        if max_pos <= 0:
            errors.append(f"max_position_size must be > 0")
        
        # Max drawdown
        max_dd = risk.get("max_drawdown", RISK_DEFAULTS["max_drawdown"])
        if max_dd > 0.30:
            errors.append(f"max_drawdown {max_dd} exceeds 30% - too risky")
        
        # Stop loss required
        if not risk.get("stop_loss_pct"):
            errors.append("stop_loss_pct is required")
        
        return errors
    
    def _warn_risk_settings(self, config: Dict) -> List[str]:
        """Warn on suboptimal but not invalid settings."""
        warnings = []
        risk = config.get("risk", {})
        
        max_pos = risk.get("max_position_size", RISK_DEFAULTS["max_position_size"])
        if max_pos > 0.10:
            warnings.append(f"max_position_size {max_pos} > 10% - consider reducing")
        
        max_dd = risk.get("max_drawdown", RISK_DEFAULTS["max_drawdown"])
        if max_dd > 0.20:
            warnings.append(f"max_drawdown {max_dd} > 20% - consider reducing")
        
        return warnings
    
    def _check_exchange(self, config: Dict) -> List[str]:
        """Check exchange settings and permissions."""
        errors = []
        exchange = config.get("exchange", {})
        exchange_name = exchange.get("name", "").lower()
        
        if not exchange_name:
            errors.append("exchange.name is required")
            return errors
        
        # Check exchange requirements
        if exchange_name in EXCHANGE_REQUIREMENTS:
            reqs = EXCHANGE_REQUIREMENTS[exchange_name]
            
            # API key validation
            if not exchange.get("api_key"):
                errors.append(f"{exchange_name}: api_key required")
            if not exchange.get("api_secret"):
                errors.append(f"{exchange_name}: api_secret required")
            
            # Testnet check
            if exchange_name == "binance" and not exchange.get("testnet"):
                warnings.append("Using production mode - ensure testnet validated first")
        
        return errors
    
    def _check_symbols(self, config: Dict) -> List[str]:
        """Check symbol validity."""
        warnings = []
        symbols = config.get("symbols", [])
        
        if not symbols:
            warnings.append("No symbols configured")
            return warnings
        
        # Check format (e.g., BTCUSDT, ETHUSDT)
        for symbol in symbols:
            if not re.match(r'^[A-Z]{2,10}USDT$', symbol):
                warnings.append(f"Symbol format may be invalid: {symbol}")
        
        return warnings
    
    def _check_schema(self, config: Dict) -> List[str]:
        """General schema warnings."""
        warnings = []
        
        if not config.get("symbols"):
            warnings.append("Empty symbols list")
        
        if not config.get("timeframes"):
            warnings.append("No timeframes configured")
        
        return warnings


# ═══════════════════════════════════════════════════════════
# Config Hashing for Trade Attribution
# ═══════════════════════════════════════════════════════════

class ConfigHasher:
    """Generate config hash for trade attribution.
    
    Hash is stored with every trade record.
    Same config → same hash → can compare PnL across configs.
    """
    
    def __init__(self) -> None:
        # Fields that affect trading behavior
        self._relevant_fields = [
            "strategy.name",
            "strategy.version",
            "strategy.parameters",  # All strategy params
            "risk.max_position_size",
            "risk.max_drawdown",
            "risk.stop_loss_pct",
            "risk.take_profit_pct",
            "symbols",
            "timeframes",
            "exchange.name",
        ]
    
    def hash_config(self, config: Dict) -> str:
        """Generate deterministic hash of trading-relevant config."""
        relevant = self._extract_relevant(config)
        # Serialize and hash
        serialized = json.dumps(relevant, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]
    
    def _extract_relevant(self, config: Dict) -> Dict:
        """Extract only trading-relevant fields."""
        result = {}
        
        for field in self._relevant_fields:
            parts = field.split(".")
            current = config
            
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    current = None
                    break
            
            if current is not None:
                # Build nested path
                self._set_nested(result, parts, current)
        
        return result
    
    def _set_nested(self, target: Dict, path: List[str], value: Any) -> None:
        """Set nested dict value."""
        current = target
        for part in path[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[path[-1]] = value
    
    def get_version_info(self, config: Dict) -> Dict[str, str]:
        """Extract semantic version info."""
        strategy = config.get("strategy", {})
        
        return {
            "name": strategy.get("name", "unknown"),
            "version": strategy.get("version", "0.0.0"),
            "hash": self.hash_config(config),
        }


# ═══════════════════════════════════════════════════════════
# Config Migration Helpers
# ═══════════════════════════════════════════════════════════

def bump_version(current: str, part: str = "patch") -> str:
    """Bump semantic version.
    
    Usage:
        bump_version("1.2.3", "patch")  # → "1.2.4"
        bump_version("1.2.3", "minor")  # → "1.3.0"
        bump_version("1.2.3", "major")  # → "2.0.0"
    """
    parts = current.split(".")
    if len(parts) != 3:
        return "0.0.1"
    
    major, minor, patch = map(int, parts)
    
    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    else:  # patch
        patch += 1
    
    return f"{major}.{minor}.{patch}"


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

async def validate_cli():
    """CLI for config validation."""
    import argparse
    import yaml
    
    parser = argparse.ArgumentParser(description="Validate Sentinel config")
    parser.add_argument("--config", type=str, help="Config file path")
    args = parser.parse_args()
    
    if not args.config:
        print("Error: --config required")
        return 1
    
    config_path = Path(args.config)
    validator = ConfigValidator(config_path=config_path)
    result = await validator.validate()
    
    if result.valid:
        print(f"✅ Config valid: {config_path}")
        if result.warnings:
            print("Warnings:")
            for w in result.warnings:
                print(f"  ⚠️  {w}")
    else:
        print(f"❌ Config invalid: {config_path}")
        print("Errors:")
        for e in result.errors:
            print(f"  🔴 {e}")
        return 1
    
    # Show config hash
    hasher = ConfigHasher()
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    print(f"\nConfig hash: {hasher.hash_config(config)}")
    info = hasher.get_version_info(config)
    print(f"Strategy: {info['name']} v{info['version']}")
    
    return 0


if __name__ == "__main__":
    import asyncio
    asyncio.run(validate_cli())