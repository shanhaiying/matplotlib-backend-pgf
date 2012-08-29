

The PGF backend is now part of matplotlib and will be included in the 1.2 release
======================

This repository was the previous home of backend_pgf and won't be used for development or bugtracking anymore.

### Examples

* See the [demo document](https://github.com/pwuertz/matplotlib-backend-pgf/raw/master/demo/demo.pdf) for a comparison with the PDF+usetex backend.
* The scipts in the [examples folder](https://github.com/pwuertz/matplotlib-backend-pgf/tree/master/examples) show how to use the backend and how font selection is handled.

![Example Image](https://github.com/pwuertz/matplotlib-backend-pgf/raw/master/demo/figure-pgf.png)

### Requirements

The only requirement is an installed TeX distribution that includes `xelatex` and the `pgf` package (both found in [TeX Live](http://www.tug.org/texlive/) for example). The `xelatex` command must be in the system's path.

### Downloading the module (pre matplotlib 1.2)

If you are using a version of matplotlib older than 1.2 you first have to download `backend_pgf.py` from the matplotlib repository. The `download_backend.py` script will do this for you. Simply place the file `backend_pgf.py` in a directory that is in python's search path or right next to your plotting script.

### How to use it

Right at the beginning of your plotting script, activate the backend.

    import matplotlib as mpl
    mpl.use("module://backend_pgf")

XeLaTeX, and thus this backend as well, can use any font that is known by the operating system. However, LaTeX documents use the Computer Modern font family. For creating figures with the same font family it is recommended to use the [unicode variant of Computer Modern](http://sourceforge.net/projects/cm-unicode/) since it provides extended glyph coverage. You can also use the standard fonts of your installed LaTeX system by setting empty lists for "font.serif", "font.sans-serif" and "font.monospace". The examples show how font selection is handled by the backend:

    rc_cmufonts = {
        "font.family": "serif"
        "font.serif": ["CMU Serif"],
        "font.sans-serif": ["CMU Sans Serif"],
        "font.monospace": [], # fallback to the default LaTeX monospace font
        }
    mpl.rcParams.update(rc_cmufonts)

With the backend activated you can save figures as PDF file, produced by XeLaTeX, or save the drawing commands to a textfile for inclusion in LaTeX documents. If pdftocairo or ghostscript is installed, the figure can be converted to png as well.

    import pylab as p
    ...
    p.savefig("figure.pgf")
    p.savefig("figure.pdf")
    p.savefig("figure.png")

The LaTeX document for creating the figures can be fully customized by adding your own commands to the preamble. Use the `pgf.preamble` rc parameter if you want to configure the math fonts or for loading additional packages. Also, if you want to do the font configuration yourself instead of using the fonts specified in the rc parameters, make sure to disable `pgf.rcfonts`:

    rc_custom_preamble = {
        "pgf.rcfonts": False,   # do not setup fonts from the mpl rc params
        "pgf.preamble": [
           r"\usepackage{siunitx}",      # use additional packages
           r"\usepackage{unicode-math}", # configure math fonts
           r"\setmathfont{XITS Math}",
           r"\setmainfont{Gentium}",     # manually setting the main font
           ]
    }
    mpl.rcParams.update(rc_custom_preamble)
