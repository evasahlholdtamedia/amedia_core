## This file defines Amedia standard colors and font type, to apply to any visualisation automatically. 
## It is called in nb_import.py, no need for additional imports.

import os
import matplotlib.pyplot as plt
from matplotlib import font_manager
from cycler import cycler

class DotDict(dict):
    """Enables dot notation access to dictionary keys."""
    def __getattr__(self, name):
        try:
            return self[name.upper()]
        except KeyError:
            return self[name.lower()]

plot_standards_dict = {
    "w": 14, "h": 8,
    "line_width": 1, "marker_size": 1, 
    "bar_width": 0.35, "bar_gap": 0.1, "cluster_bar_gap": 0.01,
    "legend_cols": 1}

ps = DotDict(plot_standards_dict)

colors_dict = {
    "MAGENTA": "#BE0064", "GRONN": "#004E46", "SVART": "#000000", 
    "HVIT": "#FFFFFF", "LYS_GUL": "#F8F9DF", "VARMGRA": "#EBDCD7", 
    "MORK_MAGENTA": "#500020", "MORK_GRONN": "#002C22", 
    "BLA": "#1B4F8F", "LYS_BLA": "#7FA9D4", "ROD": "#D6402E",
    "ORANSJE": "#E8873B", "LYS_GRONN": "#6FA85C", "GULL": "#C9A227",
    "PLOMME": "#6B4C7A", "MORK_GRA": "#3F3A38", "GRA": "#8A807A"}

colors = DotDict(colors_dict)

palette = [
    colors.magenta, 
    colors.gronn, 
    colors.varmgra,
    colors.oransje,
    colors.bla, 
    colors.lys_gronn,
    colors.mork_magenta, 
    colors.mork_gronn,
    colors.lys_gul,
    colors.lys_bla,
    colors.rod,
    colors.plomme,
    colors.mork_gra,
    colors.gull,
    colors.svart,
    colors.hvit]

fonts = DotDict()

def apply_style():
    """Applies Amedia visual identity to plotting backends."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    font_folder = os.path.join(base_dir, 'Instrument_Sans', 'static')
    
    if os.path.exists(font_folder):
        for font_file in os.listdir(font_folder):
            if font_file.endswith('.ttf'):
                font_path = os.path.join(font_folder, font_file)
                font_manager.fontManager.addfont(font_path)
                prop = font_manager.FontProperties(fname=font_path)
                name_clean = font_file.replace('InstrumentSans-', '').replace('.ttf', '').lower()
                fonts[name_clean] = prop
        
        plt.rcParams['font.family'] = 'Instrument Sans'
        print("Global font was set to Instrument Sans")

    plt.rcParams.update({
        'axes.prop_cycle': cycler(color=palette),
        'axes.facecolor': 'white', 'figure.facecolor': 'white',
        'text.color': colors.svart, 'axes.labelcolor': colors.svart,
        'axes.edgecolor': colors.varmgra, 'grid.color': colors.varmgra,
        'grid.linestyle': '--', 'grid.linewidth': 0.5,
        'axes.titleweight': 'bold', 'axes.labelweight': 'bold',
        'legend.loc': 'upper right', 'legend.fontsize': 8,
        'axes.grid': True, 'axes.grid.axis': 'y', 'axes.axisbelow': True,
        'axes.titlesize': 16, 'axes.labelsize': 12, 'xtick.labelsize': 8, 
        'ytick.labelsize': 8, 'figure.titlesize': 12,
    })

    print("Amedia visual style applied to matplotlib")
    