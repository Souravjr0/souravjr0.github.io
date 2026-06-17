"""
rl_trader.py
Reinforcement Learning Environment and lightweight Deep Q-Network (DQN) Agent.
Learns mathematically optimal trading policies in a event-driven simulator.
"""

import os
import json
import numpy as np
import pandas as pd
from typing import Tuple, List, Optional

class TradingEnvironment:
    def __init__(self, df: pd.DataFrame, initial_balance: float = 10000.0, transaction_fee: float = 0.001):
        self.df = df.copy().reset_index(drop=True)
        self.initial_balance = initial_balance
        self.fee_rate = transaction_fee
        
        # Extracted observation features list
        self.features = ["rsi14", "macd_hist", "volatility", "feat_garman_klass_vol", "feat_dist_ema20"]
        # Standard default fallbacks if missing
        for f in self.features:
            if f not in self.df.columns:
                self.df[f] = 0.0
                
        self.reset()

    def reset(self) -> np.ndarray:
        """Reset environment to initial state."""
        self.current_step = 30  # Start with enough historical context
        self.balance = self.initial_balance
        self.position = 0.0  # 0.0 -> no holding, >0 -> units held
        self.entry_price = 0.0
        self.net_worths = [self.initial_balance]
        
        return self._get_observation()

    def _get_observation(self) -> np.ndarray:
        """Construct the state representation vector (length 6)."""
        row = self.df.iloc[self.current_step]
        obs = np.array([
            float(row.get("rsi14", 50.0)),
            float(row.get("macd_hist", 0.0)),
            float(row.get("volatility", 0.0)),
            float(row.get("feat_garman_klass_vol", 0.0)),
            float(row.get("feat_dist_ema20", 0.0)),
            float(self.position > 0)  # Position hold state (0 or 1)
        ])
        
        # Standardize state vector elements to keep neural updates stable
        obs[0] = (obs[0] - 50.0) / 25.0
        obs[1] = obs[1] * 10.0
        obs[2] = obs[2] / 5.0
        obs[3] = obs[3] * 50.0
        return obs

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, dict]:
        """
        Execute one simulated action step.
        action: 0 -> HOLD, 1 -> BUY (LONG), 2 -> SELL (SHORT)
        """
        row = self.df.iloc[self.current_step]
        price = float(row["close"])
        
        prev_net_worth = self.balance + (self.position * price)
        
        # Apply action logic
        if action == 1:  # BUY / LONG
            if self.position == 0.0:  # If flat, allocate cash
                buy_amount = self.balance * 0.95  # Standard safety buffer
                self.position = buy_amount / price
                self.balance -= buy_amount * (1.0 + self.fee_rate)
                self.entry_price = price
        elif action == 2:  # SELL / EXIT
            if self.position > 0.0:  # Liquidate holdings
                sell_amount = self.position * price
                self.balance += sell_amount * (1.0 - self.fee_rate)
                self.position = 0.0
                self.entry_price = 0.0
                
        # Advance state
        self.current_step += 1
        done = (self.current_step >= len(self.df) - 1)
        
        # Calculate new net worth
        next_price = float(self.df.iloc[self.current_step]["close"])
        net_worth = self.balance + (self.position * next_price)
        self.net_worths.append(net_worth)
        
        # Reward Engine: risk-adjusted returns + drawdowns penalty
        pnl_pct = (net_worth - prev_net_worth) / prev_net_worth
        
        # Drawdown tracking
        max_worth = max(self.net_worths)
        drawdown = (max_worth - net_worth) / max_worth
        
        # Action penalties
        fee_penalty = self.fee_rate if action in {1, 2} else 0.0
        
        # Compound reward and scale to prevent explosive updates
        reward = (pnl_pct * 100.0 - (0.5 * drawdown) - (0.1 * fee_penalty)) / 10.0
        
        obs = self._get_observation()
        info = {"net_worth": net_worth, "position": self.position}
        
        return obs, reward, done, info


class DeepQNetworkAgent:
    def __init__(self, symbol: str, timeframe: str, model_dir: str = "models"):
        self.symbol = symbol
        self.timeframe = timeframe
        self.model_dir = model_dir
        
        self.state_dim = 6
        self.action_dim = 3
        
        # Hyperparameters
        self.gamma = 0.95
        self.epsilon = 1.0
        self.epsilon_min = 0.1
        self.epsilon_decay = 0.99
        self.lr = 0.0002
        
        # Lightweight vectorized 2-layer Neural Network
        self.hidden_dim = 12
        self.w1 = np.random.randn(self.hidden_dim, self.state_dim) * np.sqrt(2.0 / self.state_dim)
        self.b1 = np.zeros((self.hidden_dim, 1))
        self.w2 = np.random.randn(self.action_dim, self.hidden_dim) * np.sqrt(2.0 / self.hidden_dim)
        self.b2 = np.zeros((self.action_dim, 1))
        
        self.model_path = os.path.join(self.model_dir, f"{self.symbol}_{self.timeframe}_rl.json")
        self.load_model()

    def _forward(self, s: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Compute feedforward activation values."""
        s = s.reshape(-1, 1)
        z1 = np.dot(self.w1, s) + self.b1
        a1 = np.maximum(0, z1)  # ReLU activation function
        z2 = np.dot(self.w2, a1) + self.b2
        return z2.flatten(), a1

    def act(self, state: np.ndarray, explore: bool = False) -> int:
        """Select action using epsilon-greedy exploration strategy."""
        if explore and np.random.rand() < self.epsilon:
            return int(np.random.randint(self.action_dim))
        q_values, _ = self._forward(state)
        return int(np.argmax(q_values))

    def update_policy(self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray, done: bool):
        """Train the policy network incrementally using SGD backpropagation."""
        q_values, h1 = self._forward(state)
        next_q_values, _ = self._forward(next_state)
        
        # Q-learning target: Q(s,a) = r + gamma * max Q(s', a')
        target_q = reward
        if not done:
            target_q += self.gamma * np.max(next_q_values)
            
        # Loss derivative
        loss_deriv = q_values[action] - target_q
        
        # Backpropagate through output layer
        dz2 = np.zeros((self.action_dim, 1))
        dz2[action] = loss_deriv
        
        dw2 = np.dot(dz2, h1.T)
        db2 = dz2
        
        # Backpropagate through hidden layer (ReLU derivative)
        dh1 = np.dot(self.w2.T, dz2)
        dz1 = dh1 * (h1 > 0)
        
        dw1 = np.dot(dz1, state.reshape(1, -1))
        db1 = dz1
        
        # Optimize network weights with gradient clipping to prevent gradient explosion
        self.w1 -= self.lr * np.clip(dw1, -1.0, 1.0)
        self.b1 -= self.lr * np.clip(db1, -1.0, 1.0)
        self.w2 -= self.lr * np.clip(dw2, -1.0, 1.0)
        self.b2 -= self.lr * np.clip(db2, -1.0, 1.0)
        
        # Apply parameter clipping to ensure weight space remains bounded
        self.w1 = np.clip(self.w1, -5.0, 5.0)
        self.b1 = np.clip(self.b1, -5.0, 5.0)
        self.w2 = np.clip(self.w2, -5.0, 5.0)
        self.b2 = np.clip(self.b2, -5.0, 5.0)

    def train_rl_policy(self, df: pd.DataFrame, episodes: int = 8):
        """Run standard episode training loops to establish robust policies."""
        env = TradingEnvironment(df)
        
        for ep in range(episodes):
            state = env.reset()
            done = False
            
            while not done:
                action = self.act(state, explore=True)
                next_state, reward, done, _ = env.step(action)
                self.update_policy(state, action, reward, next_state, done)
                state = next_state
                
            self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
            
        self.save_model()

    def save_model(self):
        """Save network parameters to disk."""
        os.makedirs(self.model_dir, exist_ok=True)
        model_data = {
            "w1": self.w1.tolist(),
            "b1": self.b1.tolist(),
            "w2": self.w2.tolist(),
            "b2": self.b2.tolist(),
            "epsilon": self.epsilon
        }
        try:
            with open(self.model_path, "w") as f:
                json.dump(model_data, f)
        except Exception:
            pass

    def load_model(self) -> bool:
        """Load network parameters from disk."""
        if not os.path.exists(self.model_path):
            return False
        try:
            with open(self.model_path, "r") as f:
                data = json.load(f)
            self.w1 = np.array(data["w1"])
            self.b1 = np.array(data["b1"])
            self.w2 = np.array(data["w2"])
            self.b2 = np.array(data["b2"])
            self.epsilon = float(data["epsilon"])
            return True
        except Exception:
            return False
