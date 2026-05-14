import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, dendrogram
from scipy.spatial.distance import pdist, squareform
from typing import List, Dict

class HRPAllocator:
    """
    Implements Hierarchical Risk Parity (HRP) for multi-asset allocation.
    Diversifies based on the correlation structure of the portfolio.
    """
    def __init__(self, returns_history: pd.DataFrame) -> None:
        self.returns = returns_history # DataFrame of returns for all pairs

    def get_weights(self) -> pd.Series:
        """Calculates optimal HRP weights."""
        corr = self.returns.corr()
        cov = self.returns.cov()
        
        # 1. Quasi-Diagonalization
        dist = np.sqrt(0.5 * (1 - corr))
        link = linkage(squareform(dist), method='single')
        sort_ix = self._get_quasi_diag(link)
        sort_ix = corr.index[sort_ix].tolist() # Sorted ticker names
        
        # 2. Recursive Bisection with full HRP
        weights = self._recursive_bisection(sort_ix, cov)
        return weights

    def _get_quasi_diag(self, link: np.ndarray) -> List[int]:
        """Sorts the items into clusters."""
        link = link.astype(int)
        sort_ix = pd.Series([link[-1, 0], link[-1, 1]])
        num_items = link[-1, 3]
        while sort_ix.max() >= num_items:
            sort_ix.index = range(0, sort_ix.shape[0] * 2, 2)
            df0 = sort_ix[sort_ix >= num_items]
            i = df0.index
            j = df0.values - num_items
            sort_ix[i] = link[j, 0]
            df0 = pd.Series(link[j, 1], index=i + 1)
            sort_ix = pd.concat([sort_ix, df0])
            sort_ix = sort_ix.sort_index()
        return sort_ix.tolist()

    def _recursive_bisection(self, assets: List[str], cov: pd.DataFrame) -> pd.Series:
        """Implements full Hierarchical Risk Parity recursive bisection."""
        weights = {}
        
        def bisect_cluster(items):
            if len(items) <= 1:
                return {items[0]: 1.0}
            
            # Split cluster in half
            mid = len(items) // 2
            left = items[:mid]
            right = items[mid:]
            
            # Calculate variance (risk) of each cluster
            var_left = cov.loc[left, left].values.sum()
            var_right = cov.loc[right, right].values.sum()
            
            # Recursive bisection for sub-clusters
            left_weights = bisect_cluster(left)
            right_weights = bisect_cluster(right)
            
            # Allocate inversely proportional to cluster variance
            total_var = var_left + var_right
            w_left = var_right / total_var
            w_right = var_left / total_var
            
            # Scale sub-weights by cluster weight
            result = {}
            for asset, w in left_weights.items():
                result[asset] = w * w_left
            for asset, w in right_weights.items():
                result[asset] = w * w_right
            
            return result
        
        weight_dict = bisect_cluster(assets)
        weights_series = pd.Series(weight_dict)
        
        # Normalize to sum to 1.0
        weights_series = weights_series / weights_series.sum()
        return weights_series

    def _get_bisection_indices(self, items: List[List[str]]) -> List[tuple]:
        """Helper for recursive bisection."""
        res = []
        for i in range(len(items)):
            if len(items[i]) > 1:
                res.extend([(i, i + 1)])
        return res
