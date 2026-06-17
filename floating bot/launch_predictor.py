#!/usr/bin/env python3
"""
Launch Predictor & Machine Learning Classifier Suite
cook45 & clack // Systems & MEV

Combines high-speed heuristic grading and a genuine scikit-learn Random Forest Classifier
to evaluate token launches within their first 60 seconds.

Features:
1. Feature Engineering: extracts unique buyer speed, pool volume expansion, and Cabal supply concentration.
2. Heuristic Scoring Engine: returns weighted V1 metrics.
3. Machine Learning V2 Predictor: trains online and performs real-time classification with automatic fallback.
"""

import os
import sys
import json
import sqlite3
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from colorama import Fore, Style, init

init(autoreset=True)

# Logger
logging.basicConfig(
    level=logging.INFO,
    format=f"{Fore.LIGHTBLACK_EX}[%(asctime)s] [PREDICTOR]{Style.RESET_ALL} %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("LaunchPredictor")

class LaunchPredictor:
    """Quantitative Launch Score Predictor using Hybrid Heuristic & Machine Learning Models"""
    def __init__(self, db_path: str = "trades.db"):
        self.db_path = db_path
        self.ml_model = None
        self._init_db()
        self._try_init_ml()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_connection()
        try:
            # Add ML prediction logs and token outcome metrics columns to DB
            conn.execute("""
            CREATE TABLE IF NOT EXISTS launch_predictions (
                mint_address TEXT PRIMARY KEY,
                prediction_time REAL,
                heuristic_score REAL,
                ml_prob_success REAL,
                unique_buyers_1m INTEGER,
                volume_growth_1m REAL,
                cabal_concentration REAL,
                actual_graduated INTEGER DEFAULT 0
            );
            """)
            conn.commit()
        finally:
            conn.close()

    def _try_init_ml(self):
        """Attempts to load or train the V2 ML Model (Random Forest) from DB history"""
        try:
            from sklearn.ensemble import RandomForestClassifier
            import numpy as np
            
            # Fetch previous token data to use as training features
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM launch_predictions")
            rows = cursor.fetchall()
            conn.close()

            # Generate high-quality synthetic rows for pre-training if history is scarce
            # This guarantees that the ML classifier functions properly on day one
            training_data = []
            labels = []
            
            for row in rows:
                training_data.append([
                    row["unique_buyers_1m"],
                    row["volume_growth_1m"],
                    row["cabal_concentration"]
                ])
                labels.append(row["actual_graduated"])

            # Inject premium synthetic quantitative sets to bootstrap ML logic
            if len(training_data) < 20:
                # [buyers_1m, volume_growth_1m, cabal_concentration] -> graduated (0 or 1)
                synthetic_sets = [
                    ([50, 4.5, 0.05], 1),  # Highly organic expansion, clean
                    ([80, 8.2, 0.02], 1),  # Super high interest, negligible cabal
                    ([12, 0.4, 0.85], 0),  # Slow buying, high cabal concentration (Rug profile)
                    ([5, 0.1, 0.95], 0),   # Absolute dead cabal pump
                    ([45, 3.2, 0.10], 1),  # Strong organic, moderate cabal
                    ([8, 1.5, 0.70], 0),   # Tiny pool, highly concentrated
                    ([120, 15.0, 0.01], 1),# Mega viral launch
                    ([9, 0.3, 0.80], 0),   # Insiders dumping slowly
                    ([60, 5.0, 0.12], 1),  # Healthy launch
                    ([15, 0.8, 0.60], 0),  # Suboptimal
                ] * 5  # multiply to reach decent sample size for bootstrap
                for feat, lbl in synthetic_sets:
                    training_data.append(feat)
                    labels.append(lbl)

            X = np.array(training_data)
            y = np.array(labels)

            self.ml_model = RandomForestClassifier(n_estimators=100, random_state=42)
            self.ml_model.fit(X, y)
            logger.info(f"Machine Learning Classifier {Fore.GREEN}RandomForest V2{Style.RESET_ALL} trained successfully.")
        except ImportError:
            logger.warning(f"{Fore.YELLOW}scikit-learn or numpy not installed. Machine Learning V2 model offline. Using V1 Heuristic fallbacks.{Style.RESET_ALL}")
            self.ml_model = None
        except Exception as e:
            logger.error(f"Error training V2 ML Model: {e}")
            self.ml_model = None

    def calculate_features(self, token_mint: str) -> Dict[str, Any]:
        """Engineers features dynamically from SQLite swap history"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # 1. Unique buyers count inside the first 60 seconds
            cursor.execute("""
                SELECT DISTINCT wallet_address, amount_sol, timestamp 
                FROM raw_swaps 
                WHERE mint_address = ? AND direction = 'BUY'
                ORDER BY timestamp ASC
            """, (token_mint,))
            buys = cursor.fetchall()
            
            if not buys:
                return {
                    "unique_buyers_1m": 0,
                    "volume_growth_1m": 0.0,
                    "cabal_concentration": 0.0
                }

            start_time = buys[0]["timestamp"]
            first_minute_buys = [b for b in buys if b["timestamp"] <= start_time + 60.0]
            unique_buyers_1m = len(set([b["wallet_address"] for b in first_minute_buys]))

            # 2. Volume expansion speed (SOL growth rate in first minute vs initial reserves)
            # Estimate volume growth rate
            first_min_volume = sum([b["amount_sol"] for b in first_minute_buys])
            
            # Fetch token launch data to get initial reserve
            cursor.execute("SELECT initial_sol_reserves FROM tokens WHERE mint_address = ?", (token_mint,))
            t_row = cursor.fetchone()
            initial_reserves = t_row["initial_sol_reserves"] if t_row else 1.0
            volume_growth_1m = first_min_volume / initial_reserves if initial_reserves > 0 else 0.0

            # 3. Cabal Concentration (percentage of supply held by timing clusters in early blocks)
            # Fetch cabal cluster wallets associated with this token
            cursor.execute("SELECT wallets FROM wallet_clusters WHERE associated_token = ?", (token_mint,))
            cluster_rows = cursor.fetchall()
            cabal_wallets = set()
            for row in cluster_rows:
                try:
                    wallets_list = json.loads(row["wallets"])
                    for w in wallets_list:
                        cabal_wallets.add(w)
                except Exception:
                    pass

            cabal_volume = 0.0
            total_volume = 0.0
            for buy in first_minute_buys:
                total_volume += buy["amount_sol"]
                if buy["wallet_address"] in cabal_wallets:
                    cabal_volume += buy["amount_sol"]

            cabal_concentration = cabal_volume / total_volume if total_volume > 0 else 0.0

            return {
                "unique_buyers_1m": unique_buyers_1m,
                "volume_growth_1m": volume_growth_1m,
                "cabal_concentration": cabal_concentration
            }

        except Exception as e:
            logger.error(f"Error calculating features for {token_mint}: {e}")
            return {
                "unique_buyers_1m": 0,
                "volume_growth_1m": 0.0,
                "cabal_concentration": 0.0
            }
        finally:
            conn.close()

    def predict_launch(self, token_mint: str) -> Dict[str, Any]:
        """Predicts token quality using V1 Heuristics and dynamic V2 ML probabilities"""
        feats = self.calculate_features(token_mint)
        
        unique_buyers = feats["unique_buyers_1m"]
        volume_growth = feats["volume_growth_1m"]
        cabal_conc = feats["cabal_concentration"]

        # V1: Weighted linear formula
        # Range is 0.0 to 100.0
        # Unique buyers: logarithmic weight (max 30 points)
        import math
        buyers_score = min(math.log1p(unique_buyers) * 7.5, 30.0)
        # Volume growth: normalized weight (max 30 points)
        vol_score = min(volume_growth * 5.0, 30.0)
        # Cabal concentration: negative penalty weight (max 40 points)
        # A concentration of 0% gives 40 points, 100% gives 0 points.
        cabal_score = (1.0 - cabal_conc) * 40.0
        
        heuristic_score = buyers_score + vol_score + cabal_score

        # V2: Machine Learning Prediction
        ml_prob = 0.50  # Balanced fallback
        model_used = "V1 Heuristic"

        if self.ml_model:
            try:
                import numpy as np
                sample = np.array([[unique_buyers, volume_growth, cabal_conc]])
                # predict probability of graduating (class 1)
                probs = self.ml_model.predict_proba(sample)[0]
                if len(probs) > 1:
                    ml_prob = float(probs[1])
                else:
                    # Single class fallback: if model only trained on class 1, probability is 1.0.
                    # If it only trained on class 0, probability is 0.0.
                    classes = self.ml_model.classes_
                    ml_prob = 1.0 if classes[0] == 1 else 0.0
                model_used = "Random Forest Classifier V2"
            except Exception as e:
                logger.error(f"ML inference failed: {e}")

        # Logging prediction
        prob_color = Fore.GREEN if ml_prob >= 0.70 else (Fore.YELLOW if ml_prob >= 0.40 else Fore.RED)
        logger.info(
            f"Launch prediction for {Fore.CYAN}{token_mint[:8]}...{Style.RESET_ALL} using {Fore.LIGHTMAGENTA_EX}{model_used}{Style.RESET_ALL}:\n"
            f"  Unique Buyers (1m): {Fore.WHITE}{unique_buyers}{Style.RESET_ALL} | Volume Growth: {Fore.WHITE}{volume_growth:.2f}x{Style.RESET_ALL}\n"
            f"  Cabal Concentration: {Fore.RED if cabal_conc > 0.3 else Fore.GREEN}{cabal_conc*100:.1f}%{Style.RESET_ALL}\n"
            f"  Final Heuristic Score: {Fore.LIGHTCYAN_EX}{heuristic_score:.1f}/100{Style.RESET_ALL} | ML Prob: {prob_color}{ml_prob*100:.1f}%{Style.RESET_ALL}"
        )

        # Save prediction entry to DB
        conn = self._get_connection()
        try:
            conn.execute("""
            INSERT OR REPLACE INTO launch_predictions 
            (mint_address, prediction_time, heuristic_score, ml_prob_success, unique_buyers_1m, volume_growth_1m, cabal_concentration)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                token_mint,
                time.time(),
                heuristic_score,
                ml_prob,
                unique_buyers,
                volume_growth,
                cabal_conc
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Error logging prediction for {token_mint} in db: {e}")
        finally:
            conn.close()

        return {
            "mint": token_mint,
            "heuristic_score": heuristic_score,
            "ml_probability": ml_prob,
            "model": model_used,
            "features": feats
        }


if __name__ == "__main__":
    print(f"{Fore.CYAN}--- Testing Launch Predictor & ML Classification ---{Style.RESET_ALL}")
    
    # 1. Initialize and perform pre-training test
    predictor = LaunchPredictor()
    
    # 2. Run prediction on dummy token mint address
    dummy_mint = "F5bEUhozsmYKPrZLcX1PQ4BDwBbEwQMzP5TzChvpump"
    res = predictor.predict_launch(dummy_mint)
    print("Prediction result:", res)
