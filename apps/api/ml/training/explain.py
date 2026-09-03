import shap
import numpy as np
import xgboost as xgb

class SHAPExplainer:
    """SHAP TreeExplainer wrapper for XGBoost models."""
    
    def __init__(self, model: xgb.XGBClassifier):
        self.model = model
        self.explainer = shap.TreeExplainer(
            model,
            feature_perturbation='tree_path_dependent',
            model_output='raw'
        )
    
    def explain(self, features: np.ndarray, feature_names: list[str]) -> dict:
        """Explain a single prediction.
        
        Returns:
        {
            'base_value': float,
            'features': [
                {'name': str, 'value': float, 'contribution': float},
                ...
            ]
        }
        Sorted by absolute contribution descending.
        """
        # Ensure input is 2D for shap explainer
        if features.ndim == 1:
            features = features.reshape(1, -1)
            
        # Compute shap values with check_additivity=False to avoid float precision issues
        shap_values = self.explainer.shap_values(features, check_additivity=False)
        
        # Get values for the single instance
        instance_shap = shap_values[0]
        instance_features = features[0]
        base_value = float(self.explainer.expected_value)
        
        feature_contributions = []
        for i, name in enumerate(feature_names):
            feature_contributions.append({
                'name': name,
                'value': float(instance_features[i]),
                'contribution': float(instance_shap[i])
            })
            
        feature_contributions.sort(key=lambda x: abs(x['contribution']), reverse=True)
        
        return {
            'base_value': base_value,
            'features': feature_contributions
        }
    
    def explain_top_n(self, features: np.ndarray, feature_names: list[str], n: int = 5) -> list[dict]:
        """Return top N contributing features for a prediction."""
        explanation = self.explain(features, feature_names)
        return explanation['features'][:n]
