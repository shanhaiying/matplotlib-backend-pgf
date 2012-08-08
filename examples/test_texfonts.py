# -*- coding: utf-8 -*-

import matplotlib as mpl
import sys

# lookup and use the backend_pgf module in the parent folder
sys.path.append("..")
mpl.use('module://backend_pgf')

# use latex default fonts only
font_spec = {"pgf.rcfonts": False,
             "font.family": "serif",
             # fonts specified in matplotlib are ignored
             "font.serif": ["dont care"],
             "font.sans-serif": ["me neither"],
            }
mpl.rcParams.update(font_spec)

##############################################################################

import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(-1., 1., num=50)
Y, X = np.ogrid[-1.:1.:61j, -1.:1.:61j]

plt.figure(figsize=[5, 2.7])
plt.subplot(1,2,1)
plt.imshow(X**2 + Y**2, origin="lower", aspect="auto")
plt.xlabel("only using \LaTeX \ldots", family="sans-serif")

plt.subplot(1,2,2)
plt.plot(x, np.sin(np.pi*x), label="$f(x)=\sin(\pi x)$")
plt.xlabel("\ldots default fonts")
plt.legend()

plt.tight_layout(pad=.5, h_pad=3.)
plt.savefig("test_texfonts.pdf")
