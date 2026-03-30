"""
Grey Relational Analysis (GRA) for feature importance ranking.

Based on Section 2.2 of:
Wang et al. (2024) "Integration of the grey relational analysis with machine
learning for sucrose anaerobic hydrogen production prediction."
International Journal of Hydrogen Energy 68 (2024) 388-397.

Steps (per Section 2.2):
  1. Normalise all sequences to [0, 1] via MinMax scaling.
  2. Compute deviation sequences: Δ₀ᵢ(k) = |x₀*(k) − xᵢ*(k)|
  3. Grey Correlation Coefficient (Equation 2):
       γ(x₀, xᵢ)(k) = (Δmin + ξ·Δmax) / (Δ₀ᵢ(k) + ξ·Δmax)
     where ξ = 0.5 (discrimination coefficient).
  4. Grey Relational Grade = mean of coefficients per feature.
  5. Rank features by grade descending.
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
    @staticmethod
    def _minmax_normalize(arr: np.ndarray) -> np.ndarray:
        """Normalize each column to [0, 1] using min-max scaling."""
        if arr.ndim == 1:
            arr_min, arr_max = arr.min(), arr.max()
            denom = arr_max - arr_min
            return (arr - arr_min) / denom if denom != 0 else np.zeros_like(arr)
        # 2-D: per-column
        arr_min = arr.min(axis=0)
        arr_max = arr.max(axis=0)
        denom = arr_max - arr_min
        with np.errstate(divide='ignore', invalid='ignore'):
            result = np.where(denom != 0, (arr - arr_min) / denom, 0.0)
        return np.nan_to_num(result, nan=0.0)

    # ------------------------------------------------------------------
    def fit(self, X: np.ndarray, y: np.ndarray, feature_names: Optional[List[str]] = None):
        """
        Perform GRA.

        Args:
            X: Feature matrix (n_samples × n_features).  Raw or pre-scaled —
               MinMax normalisation is always applied internally so callers
               do not need to pre-process.
            y: Target vector (n_samples,).
            feature_names: Optional list of feature name strings.
        """
        if feature_names is None:
            feature_names = [f'Feature_{i}' for i in range(X.shape[1])]

        self.feature_names_ = feature_names

        # --- Step 1: MinMax normalisation to [0, 1] (paper Section 2.2) ---
        y_norm = self._minmax_normalize(y)
        X_norm = self._minmax_normalize(X)

        # --- Step 2 & 3: Compute grey relation degree for each feature ---
        grey_relations = {}
        for i, fname in enumerate(feature_names):
            xi_seq = X_norm[:, i]
            # Deviation sequence
            delta = np.abs(y_norm - xi_seq)
            delta_min = delta.min()
            delta_max = delta.max()

            # Grey Relational Coefficient — Equation (2)
            if delta_max == 0:
                coefficients = np.ones_like(delta)
            else:
                coefficients = (delta_min + self.xi * delta_max) / (
                    delta + self.xi * delta_max
                )

            # Grey Relational Grade — mean of coefficients
            grey_relations[fname] = float(coefficients.mean())

        self.grey_relations = grey_relations

        # --- Step 4: Rank features by grey relation degree (descending) ---
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
