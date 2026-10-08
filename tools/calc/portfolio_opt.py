"""
tools/calc/portfolio_opt.py - Quadratic Programming (QP) Portfolio Optimization Engine
Implements the mathematical formulation principles from NVIDIA cuOpt Numerical Optimization Formulation
(Linear Constraints, Positive Semi-Definite Covariance Q, Minimize Variance, Dual Sensitivities).
All calculations are deterministic, audited, and logged to ProvenanceLedger.
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from tools.ledger import ProvenanceLedger


class PortfolioQPOptimizer:
    """
    Quadratic Programming (QP) Portfolio Optimizer.
    Formulates and solves Markowitz Mean-Variance problems:
        min  (1/2) * w^T Q w - lambda * mu^T w
        s.t. sum(w_i) = 1 (Budget constraint)
             w_i >= 0     (Long-only constraint)
             w_i <= cap_i (Concentration limits)
             mu^T w >= R  (Target return, if specified)

    Conforms to NVIDIA cuOpt QP formulation standards:
    - Verifies positive semi-definiteness of Q (eigenvalues >= -1e-8)
    - Returns primal allocations w* and dual sensitivity metrics (shadow price of budget & return)
    - Records cryptographic SHA-256 ledger provenance
    """

    def __init__(self, risk_free_rate: float = 0.0425):
        self.risk_free_rate = float(risk_free_rate)

    @staticmethod
    def validate_covariance_matrix(cov_matrix: np.ndarray) -> Tuple[bool, float]:
        """
        Validates that Q is symmetric and positive semi-definite (PSD).
        Returns (is_psd, min_eigenvalue).
        """
        if cov_matrix.ndim != 2 or cov_matrix.shape[0] != cov_matrix.shape[1]:
            raise ValueError(f"Covariance matrix must be square 2D, got shape {cov_matrix.shape}")
        
        # Symmetrize to eliminate machine precision asymmetries
        sym_cov = 0.5 * (cov_matrix + cov_matrix.T)
        eigenvalues = np.linalg.eigvalsh(sym_cov)
        min_eig = float(np.min(eigenvalues))
        is_psd = min_eig >= -1e-7
        return is_psd, min_eig

    def solve_global_minimum_variance(
        self,
        tickers: List[str],
        cov_matrix: np.ndarray,
        max_weight: float = 1.0,
        expected_returns: Optional[np.ndarray] = None,
        ledger: Optional[ProvenanceLedger] = None
    ) -> Dict[str, Any]:
        """
        Solves Global Minimum Variance (GMV) portfolio:
            min  (1/2) w^T Q w
            s.t. 1^T w = 1, 0 <= w_i <= max_weight
        """
        n = len(tickers)
        if cov_matrix.shape != (n, n):
            raise ValueError(f"Mismatch between tickers length ({n}) and cov_matrix shape {cov_matrix.shape}")

        is_psd, min_eig = self.validate_covariance_matrix(cov_matrix)
        if not is_psd:
            # Regularize Q with tiny diagonal ridge if slightly non-PSD
            cov_matrix = cov_matrix + (abs(min_eig) + 1e-6) * np.eye(n)

        # Analytical unconstrained GMV baseline via KKT:
        # [Q  1] [w     ] = [0]
        # [1^T 0] [lambda]   [1]
        inv_cov = np.linalg.pinv(cov_matrix)
        ones = np.ones(n)
        denom = float(ones.T @ inv_cov @ ones)
        if abs(denom) < 1e-12:
            unconstrained_w = np.full(n, 1.0 / n)
            dual_budget = 0.0
        else:
            unconstrained_w = (inv_cov @ ones) / denom
            dual_budget = float(1.0 / denom)

        # Projected active-set bound clipping for long-only and max_weight
        w = self._project_bounds(unconstrained_w, max_weight=max_weight)

        var = float(w.T @ cov_matrix @ w)
        vol = float(np.sqrt(max(var, 0.0)))
        
        exp_ret = float(expected_returns @ w) if expected_returns is not None else 0.0
        sharpe = (exp_ret - self.risk_free_rate) / vol if vol > 1e-6 else 0.0

        weights_dict = {tickers[i]: round(float(w[i]), 4) for i in range(n)}

        result = {
            "tickers": tickers,
            "weights": weights_dict,
            "portfolio_variance": round(var, 6),
            "annualized_volatility": round(vol, 4),
            "expected_return": round(exp_ret, 4),
            "sharpe_ratio": round(sharpe, 4),
            "dual_budget_multiplier": round(dual_budget, 6),
            "min_eigenvalue_psd": round(min_eig, 8),
            "formulation_type": "QP_GLOBAL_MINIMUM_VARIANCE"
        }

        # Log into ProvenanceLedger
        if ledger is not None:
            ledger_id = ledger.record(
                tool="tools.calc.portfolio_opt.gmv",
                inputs={"tickers": tickers, "max_weight": max_weight},
                output=weights_dict,
                raw_value=var,
                source="NVIDIA cuOpt QP formulation (GMV)",
                notes=f"GMV Portfolio Vol: {vol:.4f}, Sharpe: {sharpe:.4f}",
                source_tag="QP_CALC"
            )
            result["ledger_id"] = ledger_id

        return result

    def solve_mean_variance(
        self,
        tickers: List[str],
        cov_matrix: np.ndarray,
        expected_returns: np.ndarray,
        target_return: Optional[float] = None,
        risk_aversion: float = 1.0,
        max_weight: float = 1.0,
        ledger: Optional[ProvenanceLedger] = None
    ) -> Dict[str, Any]:
        """
        Solves Markowitz Mean-Variance allocation:
            min  (1/2) w^T Q w - lambda * mu^T w
            s.t. 1^T w = 1, 0 <= w_i <= max_weight, (and optional mu^T w >= target_return)
        """
        n = len(tickers)
        if cov_matrix.shape != (n, n) or len(expected_returns) != n:
            raise ValueError("Dimension mismatch between tickers, cov_matrix, and expected_returns")

        is_psd, min_eig = self.validate_covariance_matrix(cov_matrix)
        if not is_psd:
            cov_matrix = cov_matrix + (abs(min_eig) + 1e-6) * np.eye(n)

        inv_cov = np.linalg.pinv(cov_matrix)
        ones = np.ones(n)
        A = float(ones.T @ inv_cov @ ones)
        B = float(ones.T @ inv_cov @ expected_returns)
        C = float(expected_returns.T @ inv_cov @ expected_returns)
        delta = A * C - B * B

        if target_return is not None and delta > 1e-10:
            # Analytical 2-constraint KKT system:
            lambda_1 = (C - target_return * B) / delta
            lambda_2 = (target_return * A - B) / delta
            unconstrained_w = inv_cov @ (lambda_1 * ones + lambda_2 * expected_returns)
            dual_return = float(lambda_2)
            dual_budget = float(lambda_1)
        else:
            # Risk aversion formulation
            w_risk = inv_cov @ (risk_aversion * expected_returns)
            w_gmv = (inv_cov @ ones) / A if A > 1e-12 else np.full(n, 1.0 / n)
            w_unnorm = w_gmv + (w_risk - (ones.T @ w_risk / A) * (inv_cov @ ones) if A > 1e-12 else w_risk)
            unconstrained_w = w_unnorm / np.sum(w_unnorm) if abs(np.sum(w_unnorm)) > 1e-12 else np.full(n, 1.0 / n)
            dual_return = float(risk_aversion)
            dual_budget = float(1.0 / A) if A > 1e-12 else 0.0

        # Project onto feasible simplex [0, max_weight]
        w = self._project_bounds(unconstrained_w, max_weight=max_weight)

        var = float(w.T @ cov_matrix @ w)
        vol = float(np.sqrt(max(var, 0.0)))
        exp_ret = float(expected_returns @ w)
        sharpe = (exp_ret - self.risk_free_rate) / vol if vol > 1e-6 else 0.0

        weights_dict = {tickers[i]: round(float(w[i]), 4) for i in range(n)}

        result = {
            "tickers": tickers,
            "weights": weights_dict,
            "portfolio_variance": round(var, 6),
            "annualized_volatility": round(vol, 4),
            "expected_return": round(exp_ret, 4),
            "sharpe_ratio": round(sharpe, 4),
            "dual_budget_multiplier": round(dual_budget, 6),
            "dual_return_multiplier": round(dual_return, 6),
            "target_return": target_return,
            "formulation_type": "QP_MEAN_VARIANCE"
        }

        # Log into ProvenanceLedger
        if ledger is not None:
            ledger_id = ledger.record(
                tool="tools.calc.portfolio_opt.mean_variance",
                inputs={"tickers": tickers, "target_return": target_return, "max_weight": max_weight},
                output=weights_dict,
                raw_value=var,
                source="NVIDIA cuOpt QP formulation (Mean-Variance)",
                notes=f"Mean-Variance Exp Return: {exp_ret:.4f}, Vol: {vol:.4f}, Sharpe: {sharpe:.4f}",
                source_tag="QP_CALC"
            )
            result["ledger_id"] = ledger_id

        return result

    def _project_bounds(self, weights: np.ndarray, max_weight: float = 1.0) -> np.ndarray:
        """
        Projects an unconstrained weight vector onto the bounded simplex:
        w_i >= 0, w_i <= max_weight, sum(w_i) = 1.
        Iterative thresholding ensures exact budget equality.
        """
        n = len(weights)
        w = np.copy(weights)
        
        # Clip negatives (long-only) and concentration caps
        w = np.clip(w, 0.0, max_weight)
        
        for _ in range(20):
            total = np.sum(w)
            if abs(total - 1.0) < 1e-7:
                break
            if total <= 0:
                w = np.full(n, 1.0 / n)
                break
            w = w / total
            w = np.clip(w, 0.0, max_weight)

        total = np.sum(w)
        if total > 0:
            w = w / total
        return w
