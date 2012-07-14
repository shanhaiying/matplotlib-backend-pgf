matplotlib-backend-pgf
======================

A backend for matplotlib that creates pgf pictures which can be processed with XeLaTex/LuaLaTeX. This enables full unicode support and a consistent typesetting of the text elements within LaTeX documents.

Please let me know if you have difficulties in using this backend or if the output of your figures doesn't look as expected.

### Examples

* See the [demo document](https://github.com/pwuertz/matplotlib-backend-pgf/raw/master/demo/demo.pdf) for a comparison with the PDF+usetex backend.
* The scipts in the [examples folder](https://github.com/pwuertz/matplotlib-backend-pgf/tree/master/examples) show how to use the backend and how font selection is handled.
* XeLaTeX compiled matplotlib examples - [Gallery](https://github.com/pwuertz/matplotlib-backend-pgf/wiki/Examples Gallery), [List](https://github.com/pwuertz/matplotlib-backend-pgf/wiki/Examples List)

![Example Image](https://github.com/pwuertz/matplotlib-backend-pgf/raw/master/demo/figure-pgf.png)

### Requirements

The only requirement is an installed TeX distribution that includes `xelatex` and the `pgf` package (both found in [TeX Live](http://www.tug.org/texlive/) for example). The `xelatex` command must be in the system's path.

### How to use it

Simply place the file `backend_pgf.py` in a directory that is in python's search path or right next to your plotting script.

Then, right at the beginning of your plotting script, activate the backend.

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

With the backend activated you can save figures as PDF file, produced by XeLaTeX, or save the drawing commands to a textfile for inclusion in LaTeX documents:

    import pylab as p
    ...
    p.savefig("figure.pgf")
    p.savefig("figure.pdf")

The LaTeX document for creating the figures can be fully customized by adding your own commands to the preamble. Use the `pgf.preamble` rc parameter if you want to configure the math fonts or for loading additional packages. Also, if you want to do the font configuration yourself instead of using the fonts specified in the rc parameters, make sure to disable `pgf.rcfonts`:

    rc_custom_preamble = {
        "pgf.rcfonts": False,   # do not setup fonts from the mpl rc params
        "pgf.preamble": r"""
    \usepackage{siunitx}
    \usepackage{unicode-math}
    \setmathfont{XITS Math}
    \setmainfont{Gentium}
    """}
    mpl.rcParams.update(rc_custom_preamble)
