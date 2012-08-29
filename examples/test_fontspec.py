# -*- coding: utf-8 -*-

import matplotlib as mpl
import sys

# lookup and use the backend_pgf module in the parent folder
sys.path.append("..")
mpl.use('module://backend_pgf')

# font specification via rc parameters
font_spec = {"font.family": "sans-serif",      # use sans-serif as default font
             "font.serif": ["Linux Libertine O"],  # custom serif font
             "font.sans-serif": [""],            # no font given, latex default
            }
mpl.rcParams.update(font_spec)

# set a different math font via latex preamble
latex_preamble = {"pgf.preamble": [r"\usepackage{cmbright}"]}
mpl.rcParams.update(latex_preamble)

##############################################################################

import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(-1, 1, num=50)

plt.figure(figsize=[5, 2.7])
plt.text(0., .5, ur"Custom Font", family="Linux Libertine Capitals O", ha="center")
plt.text(0., .3, ur"Specified Serif Font", family="serif", ha="center")
plt.plot(x, x**2, "r--", label=ur"Line 1, $f(x)=x^2$")
plt.plot(x, 1-x**2, "b", label=ur"Line 2, $f(x)=1-x^2$")
plt.xlabel(ur"\LaTeX \, default sans-serif with unicode (°/µm)")
plt.ylabel(ur"Sans-serif math $\frac{1}{N} \sum_i x_i$")
plt.legend().legendPatch.set_facecolor([1., 1., 1., .8])

plt.tight_layout(pad=.5)
plt.savefig("test_fontspec.pdf")
