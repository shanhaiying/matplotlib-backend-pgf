# -*- coding: utf-8 -*-

import matplotlib

use_pgf = False
if use_pgf:
    matplotlib.use('module://backend_pgf')
    matplotlib.rcParams.update({"pgf.font": "CMU Serif"})
    #matplotlib.rcParams.update({"pgf.preamble": r"\usepackage{mathpazo}"})
else:
    matplotlib.rcParams["text.latex.preamble"] = r"""
    \usepackage{lmodern}
    \usepackage[T1]{fontenc}
    """
    matplotlib.rcParams["text.usetex"] = True
    matplotlib.rcParams['text.latex.unicode'] = True
    matplotlib.rcParams["font.family"] = "serif"

params_text = {
               'axes.labelsize': 11,
               'text.fontsize': 11,
               'legend.fontsize': 11,
               'xtick.labelsize': 11,
               'ytick.labelsize': 11,
               }
matplotlib.rcParams.update(params_text)

import pylab as p
import numpy as np

x = np.linspace(0, 1, num=20)

p.figure(figsize=(2.6,2.0))
p.plot(x, x**2, "r--", label=ur"Unicode, ияäüέψλ", lw=2)
if matplotlib.rcParams["text.usetex"]:
    p.plot(x, 1-x**2, "b-.", label=ur"Math, $\displaystyle\int_\Omega \mu \cdot x^2\,\mathrm{d}x$")
else:
    p.plot(x, 1-x**2, "b-.", label=ur"Math, $\int_\Omega \mu \cdot x^2\,\mathrm{d}x$")    
p.plot(x, 0.2*x, "g>")
p.xlabel(ur"$x$-axis in units of $10^3\,$µm")
p.ylabel(ur"angle $\alpha$ in °")
p.tight_layout(0.0)
p.legend()

if use_pgf:
    print "saving pgf figures in demo/"
    p.savefig("demo/figure-pgf.pdf")
    p.savefig("demo/figure.pgf")
elif matplotlib.rcParams["text.usetex"]:
    print "saving pdf-usetex figure in demo/"
    p.savefig("demo/figure-pdf-usetex.pdf")
else:
    print "saving pdf figure in demo/"
    p.savefig("demo/figure-pdf.pdf")
