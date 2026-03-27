"""
Exploratory Data Visualiser Tool

A lightweight GUI for exploring rib analysis research data across multiple papers
with custom axis selection, plot modes (2D/3D), and binning visualization.

This tool reuses core functionality from ribs_core and provides an interactive
interface for data exploration.
"""

from .visualiser_gui import VisualisierApp

__all__ = ["VisualisierApp"]
