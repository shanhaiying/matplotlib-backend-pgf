matplotlib-backend-pgf
======================

A backend for matplotlib drawing pgf pictures that can processed with XeLaTex/LuaLaTeX. This enables full unicode support and a consistent typesetting of the text elements within LaTeX documents. See [Demo document](https://github.com/pwuertz/matplotlib-backend-pgf/raw/master/demo/demo.pdf) for a comparison with existing backends.

![Example Image](https://github.com/pwuertz/matplotlib-backend-pgf/raw/master/demo/figure-pgf.png)

Although the pgf backend is very useful already and produces figures in publication quality (an overused expression ;) ), there are still some loose ends. Any input for making the pgf backend an option that is easy to use for matplotlib users is welcome. I wrote down all open questions I had in TODO comments within the code. To summarize them:

* The default font for the backend right now is the unicode variant of Computer Modern (CMU Serif), which might not be present on most users' systems. If you don't want to install/use it, you can just specify another by setting an extra rc parameter (see test script). I could as well check for the fonts specified in the default rc parameters but these look just weird when embedded in latex documents. An alternative is to fallback to the standard computer modern font, but it lacks alot of unicode characters.

* When printing pgf commands, the actual font depends on the LaTeX environment you are embedding the figure in. Matplotlib only needs the font for calculating the text positions or if the user decides to save the figure to PDF directly.

* I'm not sure how certain draw methods of the renderer should behave due to lack of documentation. Rotated text and image transformations are probably not handled correctly.

* Some text properties like selecting a different font family or making the text italic/bold are ignored since I did not need them yet.

* The method of obtaining the metrics of text elements is pretty cool I think, but also very fragile right now. The XelatexManager runs an instance of XeLaTeX in a subprocess and queries the width/height/descent of the texts we want to print. Unfortunately, python does not provide a timeout option when reading from a subprocess. If something unexpected happens the read operation just stalls forever. I'm not sure whats the best option to solve this. Running a nonstop mode xelatex process for each text element might slow things down. Running the subprocess in a thread and communicate through a Queue might work.
 
* Because matplotlib behaves weird in some situations, there are a few workarounds also marked as TODO. Maybe one can get rid of those one day or find a better explanation why this workaround is necessary.