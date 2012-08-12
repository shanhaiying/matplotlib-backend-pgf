# -*- coding: utf-8 -*-
import matplotlib as mpl
import sys

# lookup and use the backend_pgf module in the parent folder
sys.path.append("..")
mpl.use('module://backend_pgf')

###############################################################################

import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 1, 10)

# define two sets of rc parameters
rc_sets = []
rc_sets.append({"pgf.debug": True,
                "pgf.texsystem": "xelatex",
                "pgf.rcfonts": True,
                "font.family": "serif",
                "font.size": 20,
                "lines.markersize": 10,
                })

rc_sets.append({"pgf.debug": True,
                "pgf.texsystem": "pdflatex",
                "pgf.preamble": [r"\usepackage[utf8x]{inputenc}",
                                 r"\usepackage[T1]{fontenc}",
                                 r"\usepackage{cmbright}"],
                "font.family": "sans-serif",
                "font.size": 12,
                "lines.markersize": 3,
                })

# create figure for each set
for i, rc_set in enumerate(rc_sets):
    print "using rc set %d" % (i+1)
    mpl.rcParams.update(rc_set)
    plt.figure(figsize=[5, 2.7])
    plt.plot(x, 1-x**2, "g>", label="$f(x) = 1-x^2$")
    plt.plot(x, x**2, "bo", label="$f(x) = x^2$")
    plt.xlabel(u"some unicode µ, ü, ö, °")
    plt.legend()
    plt.tight_layout(pad=.5)
    plt.savefig("test_rcparams_%d.pdf" % (i+1))
