import numpy as np
import time
from sklearn.metrics import (
    precision_recall_curve, auc, precision_score, recall_score,
    f1_score, confusion_matrix, roc_auc_score, average_precision_score
)
import json

class ModelEvaluator:
    """Evaluate and compare models on the test set."""
    
    def evaluate_model(self, model, X_test, y_test, model_name: str) -> dict:
        """Compute all metrics for a single model.
        
        Returns dict with: pr_auc, roc_auc, precision, recall, f1, fpr,
        confusion_matrix, optimal_threshold, inference_latency_ms
        """
        # Inference latency
        start_time = time.time()
        if hasattr(model, "predict_proba"):
            y_prob = model.predict_proba(X_test)[:, 1]
        else:
            y_prob = model.predict(X_test)
        latency_ms = (time.time() - start_time) * 1000 / len(X_test)
        
        # Determine optimal threshold on the fly for metrics computation
        precision_arr, recall_arr, thresholds = precision_recall_curve(y_test, y_prob)
        f1_scores = 2 * (precision_arr[:-1] * recall_arr[:-1]) / (precision_arr[:-1] + recall_arr[:-1] + 1e-10)
        optimal_idx = np.argmax(f1_scores)
        optimal_threshold = thresholds[optimal_idx] if len(thresholds) > 0 else 0.5
        
        y_pred = (y_prob >= optimal_threshold).astype(int)
        
        pr_auc = average_precision_score(y_test, y_prob)
        roc_auc = roc_auc_score(y_test, y_prob)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        cm = confusion_matrix(y_test, y_pred)
        
        tn, fp, fn, tp = cm.ravel()
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        
        return {
            'model_name': model_name,
            'pr_auc': float(pr_auc),
            'roc_auc': float(roc_auc),
            'precision': float(precision),
            'recall': float(recall),
            'f1': float(f1),
            'fpr': float(fpr),
            'confusion_matrix': cm.tolist(),
            'optimal_threshold': float(optimal_threshold),
            'inference_latency_ms': float(latency_ms)
        }
    
    def compare_models(self, results: list) -> str:
        """Generate a formatted comparison table.
        
        Columns: Model | PR-AUC | Precision | Recall | F1 | FPR | ROC-AUC | Latency(ms)
        Rows: Model 0, Model 1, Model 2
        Highlight the best value in each column.
        """
        header = f"{'Model':<10} | {'PR-AUC':<8} | {'Precision':<9} | {'Recall':<8} | {'F1':<8} | {'FPR':<8} | {'ROC-AUC':<8} | {'Latency(ms)':<11}"
        separator = "-" * len(header)
        lines = [header, separator]
        
        for r in results:
            line = f"{r['model_name']:<10} | {r['pr_auc']:.4f}   | {r['precision']:.4f}    | {r['recall']:.4f}   | {r['f1']:.4f}   | {r['fpr']:.4f}   | {r['roc_auc']:.4f}   | {r['inference_latency_ms']:.4f}"
            lines.append(line)
            
        return "\n".join(lines)
    
    def find_optimal_threshold(self, model, X_val, y_val) -> float:
        """Find the threshold that maximizes F1 on the validation set."""
        if hasattr(model, "predict_proba"):
            y_prob = model.predict_proba(X_val)[:, 1]
        else:
            y_prob = model.predict(X_val)
            
        precision, recall, thresholds = precision_recall_curve(y_val, y_prob)
        f1_scores = 2 * (precision[:-1] * recall[:-1]) / (precision[:-1] + recall[:-1] + 1e-10)
        return float(thresholds[np.argmax(f1_scores)])
    
    def save_evaluation_report(self, results: list, output_path: str):
        """Save results as JSON and print the comparison table."""
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=4)
        
        print("Model Evaluation Report:")
        print(self.compare_models(results))
