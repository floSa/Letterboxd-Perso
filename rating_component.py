import os
import streamlit.components.v1 as components

_COMPONENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "components", "half_rating")
_half_rating_func = components.declare_component("half_rating", path=_COMPONENT_DIR)

def half_rating(value: float = 0.0, mode: str = "star", key: str = None) -> float:
    """
    Affiche 5 vraies étoiles (ou cœurs) vectorielles interactives.
    Se remplit par moitié (0.5) au survol et au clic, de 0.0 à 5.0.
    Retourne la note sélectionnée (float: 0.0, 0.5, 1.0, ... 5.0).
    """
    val = float(value or 0.0)
    result = _half_rating_func(value=val, mode=mode, default=val, key=key)
    return float(result) if result is not None else val
