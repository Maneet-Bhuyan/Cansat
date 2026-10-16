"""
Cognitive CanSat - Aerial Vision Safety & Out-of-Distribution (OOD) Guard
--------------------------------------------------------------------------
Guards the landing hazard classification pipeline against non-aerial
subjects (human faces, indoor rooms, desks, ceilings, artificial objects)
to eliminate false-positive SAFE_LZ / OPTIMAL LZ verdicts.
"""

from typing import Dict, Any, Tuple, Optional
import numpy as np


class AerialVisionGuard:
    """
    Validates whether an incoming optical frame matches physical aerial sounding
    and nadir drone imagery characteristics before downstream hazard inference.
    """

    def __init__(self, skin_threshold: float = 0.14, min_aerial_confidence: float = 0.55):
        self.skin_threshold = skin_threshold
        self.min_aerial_confidence = min_aerial_confidence

    def check_skin_tone_ratio(self, frame_rgb: np.ndarray) -> float:
        """
        Calculates the percentage of pixels exhibiting human skin chromaticity
        in normalized RGB / HSV color space.
        """
        if frame_rgb is None or frame_rgb.size == 0:
            return 0.0

        R = frame_rgb[:, :, 0].astype(np.float32)
        G = frame_rgb[:, :, 1].astype(np.float32)
        B = frame_rgb[:, :, 2].astype(np.float32)

        # Peer / Kovac skin color illumination rule
        # R > 95 and G > 40 and B > 20 and max-min > 15 and |R-G| > 15 and R > G and R > B
        max_c = np.maximum(np.maximum(R, G), B)
        min_c = np.minimum(np.minimum(R, G), B)

        skin_mask = (
            (R > 95) & (G > 40) & (B > 20) &
            ((max_c - min_c) > 15) &
            (np.abs(R - G) > 15) &
            (R > G) & (R > B)
        )
        return float(np.sum(skin_mask) / (frame_rgb.shape[0] * frame_rgb.shape[1]))

    def check_indoor_illumination(self, frame_rgb: np.ndarray) -> Tuple[bool, str]:
        """
        Identifies flat indoor artificial surfaces, drywall, and ceilings
        lacking natural aerial vegetative or geological spectral variance.
        """
        R = frame_rgb[:, :, 0].astype(np.float32)
        G = frame_rgb[:, :, 1].astype(np.float32)
        B = frame_rgb[:, :, 2].astype(np.float32)

        mean_r, mean_g, mean_b = float(np.mean(R)), float(np.mean(G)), float(np.mean(B))
        std_r, std_g, std_b = float(np.std(R)), float(np.std(G)), float(np.std(B))
        avg_std = (std_r + std_g + std_b) / 3.0

        # Excessively uniform flat surfaces (walls/ceilings)
        if avg_std < 14.0 and (mean_r > 100 and mean_g > 100 and mean_b > 90):
            return True, "FLAT_INDOOR_WALL_OR_CEILING"

        # Extreme desaturation with artificial warm indoor white balance
        max_m = max(mean_r, mean_g, mean_b)
        min_m = min(mean_r, mean_g, mean_b)
        sat = (max_m - min_m) / (max_m + 1e-5)
        if sat < 0.06 and avg_std < 18.0:
            return True, "LOW_VARIANCE_INDOOR_SURFACE"

        return False, ""

    def validate_frame(
        self,
        frame_rgb: np.ndarray,
        model_probs: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive Out-of-Distribution audit. Returns status, rejection flag,
        and diagnostic reason.
        """
        if frame_rgb is None or frame_rgb.size == 0:
            return {
                "is_aerial": False,
                "rejection_reason": "EMPTY_OR_CORRUPT_FRAME",
                "slai_class": "INVALID_AERIAL_SURFACE",
                "optimal_lz_valid": False,
                "confidence": 0.0
            }

        # 1. Skin tone test (face / body / hand detection)
        skin_ratio = self.check_skin_tone_ratio(frame_rgb)
        if skin_ratio >= self.skin_threshold:
            return {
                "is_aerial": False,
                "rejection_reason": "HUMAN_SUBJECT_DETECTED",
                "slai_class": "INVALID_AERIAL_SURFACE",
                "optimal_lz_valid": False,
                "skin_ratio": round(skin_ratio, 3),
                "message": f"Non-aerial subject detected (Skin chromaticity: {skin_ratio * 100:.1f}%). Landing site search suppressed."
            }

        # 2. Indoor illumination & texture test
        is_indoor, indoor_reason = self.check_indoor_illumination(frame_rgb)
        if is_indoor:
            return {
                "is_aerial": False,
                "rejection_reason": indoor_reason,
                "slai_class": "INVALID_AERIAL_SURFACE",
                "optimal_lz_valid": False,
                "message": f"Indoor / non-terrain surface detected ({indoor_reason}). Landing site search suppressed."
            }

        # 3. Model Entropy / Confidence Check (if probability distribution provided)
        if model_probs is not None and len(model_probs) > 0:
            max_prob = float(np.max(model_probs))
            # Normalized Shannon Entropy across 4 classes
            eps = 1e-7
            entropy = -float(np.sum(model_probs * np.log2(model_probs + eps))) / 2.0  # Normalized to [0, 1] for 4 classes
            if max_prob < self.min_aerial_confidence or entropy > 0.88:
                return {
                    "is_aerial": False,
                    "rejection_reason": "HIGH_ENTROPY_OOD_UNCERTAINTY",
                    "slai_class": "INVALID_AERIAL_SURFACE",
                    "optimal_lz_valid": False,
                    "max_prob": round(max_prob, 3),
                    "entropy": round(entropy, 3),
                    "message": "Visual features do not match trained aerial terrain distributions. Model uncertainty exceeds safety threshold."
                }

        # Frame passed all guards; valid aerial sounding perspective
        return {
            "is_aerial": True,
            "rejection_reason": None,
            "slai_class": "VALID_AERIAL_SURFACE",
            "optimal_lz_valid": True,
            "skin_ratio": round(skin_ratio, 3)
        }
