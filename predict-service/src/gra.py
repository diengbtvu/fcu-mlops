"""
Grey Relational Analysis (GRA) for feature importance ranking.

Based on Section 2.2 of:
Wang et al. (2024) "Integration of the grey relational analysis with machine
learning for sucrose anaerobic hydrogen production prediction."
International Journal of Hydrogen Energy 68 (2024) 388-397.

Grey Correlation Coefficient (Equation 2):
    γ(x₀, xᵢ)(k) = (Δmin + ξ·Δmax) / (Δ₀ᵢ(k) + ξ·Δmax)
where ξ = 0.5 (discrimination coefficient, optimal when ξ ≤ 0.5463).
"""

import logging
from typing import List, Optional, Tuple

import numpy as np


class GreyRelationalAnalysis:
    """
    Compute Grey Relation Degree for each feature vs. the target sequence.
    Higher degree → stronger correlation with the target.
    """

    def __init__(self, xi: float = 0.5):
        """
        Args:
            xi: Discrimination coefficient (default 0.5).
        """
        self.xi = xi
        self.grey_relations: Optional[dict] = None
        self.ranking: Optional[List[Tuple[str, float]]] = None
        self.feature_names_: Optional[List[str]] = None

    # ------------------------------------------------------------------
    def fit(self, X: np.ndarray, y: np.ndarray, feature_names: Optional[List[str]] = None):
        """
        Perform GRA.

        Args:
            X: Feature matrix (n_samples × n_features), already normalised to [0,1].
            y: Target vector (n_samples,), already normalised to [0,1].
            feature_names: Optional list of feature name strings.
        """
        if feature_names is None:
            feature_names = [f'Feature_{i}' for i in range(X.shape[1])]

        self.feature_names_ = feature_names

        # --- Step 1: Averaging process (normalise by dividing by mean) ---
        y_mean = y.mean()
        y_norm = y / y_mean if y_mean != 0 else y.copy()

        X_means = X.mean(axis=0)
        # Avoid division by zero
        with np.errstate(divide='ignore', invalid='ignore'):
            X_norm = np.where(X_means != 0, X / X_means, 1.0)
        X_norm = np.nan_to_num(X_norm, nan=1.0)

        # --- Step 2: Compute grey relation degree for each feature ---
        grey_relations = {}
        for i, fname in enumerate(feature_names):
            xi_seq = X_norm[:, i]
            delta = np.abs(y_norm - xi_seq)
            delta_min = delta.min()
            delta_max = delta.max()

            # Equation (2)
            if delta_max == 0:
                coefficients = np.ones_like(delta)
            else:
                coefficients = (delta_min + self.xi * delta_max) / (
                    delta + self.xi * delta_max
                )

            grey_relations[fname] = float(coefficients.mean())

        self.grey_relations = grey_relations

        # --- Step 3: Rank features by grey relation degree (descending) ---
        self.ranking = sorted(grey_relations.items(), key=lambda kv: kv[1], reverse=True)

        logging.info("GRA completed. Feature ranking:")
        for rank, (fname, score) in enumerate(self.ranking, 1):
            logging.info(f"  {rank}. {fname}: {score:.4f}")

        return self

    # ------------------------------------------------------------------
    def get_ranking(self) -> List[Tuple[str, float]]:
        """Return list of (feature_name, grey_relation_degree) sorted desc."""
        if self.ranking is None:
            raise RuntimeError("Call fit() before get_ranking().")
        return self.ranking

    def get_ranking_dict(self) -> dict:
        """Return {feature_name: grey_relation_degree} dict."""
        return dict(self.ranking) if self.ranking else {}

    def get_ordered_feature_names(self) -> List[str]:
        """Return feature names in GRA importance order (most important first)."""
        return [fname for fname, _ in self.get_ranking()]


# -----------------------------------------------------------------------
# Convenience function (used by Flask train route)
# -----------------------------------------------------------------------
def run_gra(X: np.ndarray, y: np.ndarray, feature_names: List[str], xi: float = 0.5) -> dict:
    """
    Run GRA and return a serialisable ranking dict.

    Returns:
        {"ranking": [{"feature": str, "score": float, "rank": int}, ...]}
    """
    gra = GreyRelationalAnalysis(xi=xi)
    gra.fit(X, y, feature_names)
    ranking = [
        {"feature": fname, "score": round(score, 6), "rank": i + 1}
        for i, (fname, score) in enumerate(gra.get_ranking())
    ]
    return {"ranking": ranking}
