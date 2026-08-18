## This script is intended to simplify imports in any project notebook.
## Simply run following snippet in a notebook cell: from core.nb_imports import *

import warnings
warnings.filterwarnings("ignore")

from core.util import *
from core.theme import *

import pandas as pd
pd.options.display.float_format = '{:.2f}'.format
import numpy as np
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from itertools import combinations

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
from matplotlib import font_manager
from adjustText import adjust_text
import seaborn as sns
import plotly
from matplotlib_inline.backend_inline import set_matplotlib_formats
set_matplotlib_formats('retina')
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
import sklearn.metrics as metrics
from statsmodels.tsa.seasonal import STL
import statsmodels.api as sm
import statsmodels.formula.api as smf
import scipy.stats as stats

apply_style()