matplotlib-backend-pgf
======================

A backend for matplotlib that creates pgf pictures which can be processed with XeLaTex/LuaLaTeX. This enables full unicode support and a consistent typesetting of the text elements within LaTeX documents.

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

XeLaTeX, and thus this backend as well, can use any font that is known by the operating system. However, LaTeX documents use the Computer Modern font family. For creating figures with the same font family it is recommended to use the [unicode variant of Computer Modern](http://sourceforge.net/projects/cm-unicode/) since it provides extended glyph coverage. You can also use the standard fonts of your installed LaTeX system by setting empty lists for "font.serif", "font.sans-serif" and "font.monospace". See the examples how font selection is handled by the backend.

    rc_cmufonts.append({
        "font.family": "serif"
        "font.serif": ["CMU Serif"],
        "font.sans-serif": ["CMU Sans Serif"],
        "font.monospace": ["CMU Concrete"],
        })
    mpl.rcParams.update(rc_cmufonts)

With the backend activated you can save figures as PDF file, produced by XeLaTeX, or save the drawing commands to a textfile for inclusion in LaTeX documents.

    import pylab as p
    ...
    p.savefig("figure.pgf")
    p.savefig("figure.pdf")