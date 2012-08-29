# -*- coding: utf-8 -*-

# lookup and the backend_pgf module in the parent folder
import sys
sys.path.append("..")

# create a figure for different rc parameter sets
rc_sets = []; fnames_sets = []

# pgf backend
rc_sets.append({
    "backend": "module://backend_pgf",
    "font.serif": ["CMU Serif"],
    "font.sans-serif": ["CMU Sans Serif"],
    "font.monospace": ["CMU Concrete"],
    })
fnames_sets.append(["figure-pgf.pdf", "figure.pgf", "figure-pgf.png"])

# pdf backend with text.usetex
rc_sets.append({
    "text.usetex": True,
    "text.latex.unicode": True,
    "text.latex.preamble": [r"\usepackage{lmodern}",
                            r"\usepackage[T1]{fontenc}"],
    })
fnames_sets.append(["figure-pdf-usetex.pdf"])

# plain pdf backend
rc_sets.append({
    "text.usetex": False,
    "font.serif": ["DejaVu Serif"],
    })
fnames_sets.append(["figure-pdf.pdf"])

##############################################################################

# fork child process for each set of rc parameters
import os
parent_pid = os.getpid()
child_pids = []
for rc_set, fnames in zip(rc_sets, fnames_sets):
    if os.getpid() == parent_pid:
        pid = os.fork()
        if pid == 0:
            break
        child_pids.append(pid)
# wait for all children to finish
if os.getpid() == parent_pid:
    for pid in child_pids: os.waitpid(pid, 0)
    exit()

##############################################################################

# actual plotting script starts here

import matplotlib as mpl
rc_text = {"font.family": "serif", "axes.labelsize": 11, "text.fontsize": 11,
           "legend.fontsize": 11, "xtick.labelsize": 11, "ytick.labelsize": 11}
mpl.rcParams.update(rc_text)
mpl.rcParams.update(rc_set)

import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(0, 1, num=20)

plt.figure(figsize=(2.6,2.0))
plt.plot(x, x**2, "r--", label=ur"Unicode, ияäüέψλ", lw=2)
if mpl.rcParams["text.usetex"]:
    plt.plot(x, 1-x**2, "b-.", label=ur"Math, $\displaystyle\int_\Omega \mu \cdot x^2\,\mathrm{d}x$")
else:
    plt.plot(x, 1-x**2, "b-.", label=ur"Math, $\int_\Omega \mu \cdot x^2\,\mathrm{d}x$")
plt.plot(x, 0.2*x, "g>")
plt.xlabel(ur"$x$-axis in units of $10^3\,$µm")
plt.ylabel(ur"angle $\alpha$ in °")
plt.tight_layout(0.0)
plt.legend()

# save figure
for fname in fnames:
    plt.savefig(fname)
