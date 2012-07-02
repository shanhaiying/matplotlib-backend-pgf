matplotlib-backend-pgf
======================

A backend for matplotlib drawing pgf pictures that can processed with XeLaTex/LuaLaTeX. This enables full unicode support and a consistent typesetting of the text elements within LaTeX documents.

* See the [demo document](https://github.com/pwuertz/matplotlib-backend-pgf/raw/master/demo/demo.pdf) for a comparison with the PDF+usetex backend.
* The scipts in the [examples folder](https://github.com/pwuertz/matplotlib-backend-pgf/tree/master/test) show how to use the backend and how font selection is handled.
* XeLaTeX compiled matplotlib examples - [Gallery](https://github.com/pwuertz/matplotlib-backend-pgf/wiki/Examples Gallery), [List](https://github.com/pwuertz/matplotlib-backend-pgf/wiki/Examples List)

![Example Image](https://github.com/pwuertz/matplotlib-backend-pgf/raw/master/demo/figure-pgf.png)

Some notes:

* It is recommended to install the [unicode variant of Computer Modern](http://sourceforge.net/projects/cm-unicode/) and to choose `CMU Serif`, `CMU Sans Serif`, etc. in the rc parameters (`demo/create_demo_figures.py` for example). This provides the most consistent appearance for LaTeX documents.
