matplotlib-backend-pgf
======================

A backend for matplotlib drawing pgf pictures that can processed with XeLaTex/LuaLaTeX. This enables full unicode support and a consistent typesetting of the text elements within LaTeX documents.
* See [Demo document](https://github.com/pwuertz/matplotlib-backend-pgf/raw/master/demo/demo.pdf) for a comparison with the PDF+usetex backend.
* XeLaTeX compiled matplotlib examples - [Gallery](https://github.com/pwuertz/matplotlib-backend-pgf/wiki/Examples Gallery), [List](https://github.com/pwuertz/matplotlib-backend-pgf/wiki/Examples List)

![Example Image](https://github.com/pwuertz/matplotlib-backend-pgf/raw/master/demo/figure-pgf.png)

Although the pgf backend is very useful already and produces figures in publication quality (an overused expression ;) ), there are still some loose ends. Any input for making the pgf backend an option that is easy to use for matplotlib users is welcome. I wrote down all open questions I had in TODO comments within the code. To summarize them:

* It is recommended to install the [unicode variant of Computer Modern](http://sourceforge.net/projects/cm-unicode/) and to choose "CMU Serif", "CMU Sans Serif", etc. in the rc parameters (see test_pgf_backend.py). This provides the most consistent appearance for LaTeX documents.

* I'm not sure how certain draw methods of the renderer should behave due to the lack of documentation, but most of the matplotlib examples are looking good for now.

* Because matplotlib behaves weird in some situations, there are a few workarounds also marked as TODO. Maybe one can get rid of those one day or find a better explanation why this workaround is necessary.
