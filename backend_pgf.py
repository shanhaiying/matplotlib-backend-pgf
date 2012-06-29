from __future__ import division

import os
import re
import shutil
import tempfile
import codecs
import subprocess
import warnings
warnings.formatwarning = lambda *args: str(args[0])

import matplotlib
from matplotlib.backend_bases import RendererBase, GraphicsContextBase,\
     FigureManagerBase, FigureCanvasBase
from matplotlib.figure import Figure
from matplotlib.text import Text
from matplotlib.path import Path
from matplotlib import _png, rcParams

###############################################################################
# settings read from rc

# debug switch
debug = bool(rcParams.get("pgf.debug", False))

# use xelatex default font if pgf.font is not set and emit a warning
fontfamily = rcParams.get("pgf.font", "")
if not fontfamily:
    warnings.warn("""No font was specified in rc parameter 'pgf.font'.
Using the XeLaTeX default font might result in incomplete glyph coverage.""", stacklevel=1)

# latex preamble
latex_preamble = rcParams.get("pgf.preamble", "")
if type(latex_preamble) == list:
    latex_preamble = "\n".join(latex_preamble)

# is math text to be displaystyled? (large symbols)
displaymath = bool(rcParams.get("pgf.displaymath", True))

###############################################################################

# TODO: matplotlib uses \mathdefault sometimes. this is an unknown latex macro
mathdefault_search = re.compile(r"\\mathdefault")
mathdefault_replace = lambda s: mathdefault_search.sub(r"\mathnormal", s)

# method for reformatting inline math
math_search = re.compile(r"\$([^\$]+)\$")
math_replace = lambda match: r"\(\displaystyle %s\)" % match.group(1)
def math_to_displaystyle(text):
    """
    This function replaces any inline math with a inline math environment in
    displaystyle.
    """
    return math_search.sub(math_replace, text)

# every line of a file included with \input must be terminated with %
# if not, latex will create additional vertical spaces for some reason
def writeln(fh, line):
    fh.write(line)
    fh.write("%\n")

class XelatexError(Exception):
    def __init__(self, message, latex_output = ""):
        Exception.__init__(self, message)
        self.latex_output = latex_output

class XelatexManager:
    """
    The XelatexManager opens an instance of xelatex for determining the
    metrics of text elements. The Xelatex environment can be modified by
    changing the main font and by adding a custom latex preamble. These
    parameters are read from the rc settings "pgf.font" and "pgf.preamble".
    """

    def __init__(self):
        # create latex header with some content, else latex will load some
        # math fonts later when we don't expect the additional output on stdout
        # TODO: is this sufficient?
        setmainfont = r"\setmainfont{%s}" % fontfamily if fontfamily else ""
        latex_header = u"""\\documentclass{minimal}
%s
\\usepackage{fontspec}
%s
\\begin{document}
text $math \mu$ %% force latex to load fonts now
\\typeout{pgf_backend_query_start}
""" % (latex_preamble, setmainfont)

        latex_end = """
\\makeatletter
\\@@end
"""
        
        # test the xelatex setup to ensure a clean startup of the subprocess
        xelatex = subprocess.Popen(["xelatex", "-halt-on-error"],
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   universal_newlines=True)
        stdout, stderr = xelatex.communicate(latex_header + latex_end)       
        if xelatex.returncode != 0:
            raise XelatexError("Xelatex returned an error, probably missing font or error in preamble:\n%s" % stdout)
        
        # open xelatex process
        xelatex = subprocess.Popen(["xelatex", "-halt-on-error"],
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   universal_newlines=True)
        xelatex.stdin.write(latex_header)
        xelatex.stdin.flush()
        # read all lines until our 'pgf_backend_query_start' token appears
        while not xelatex.stdout.readline().startswith("*pgf_backend_query_start"):
            pass
        while xelatex.stdout.read(1) != '*':
            pass
        self.xelatex = xelatex
        self.xelatex_stdin = codecs.getwriter("utf-8")(xelatex.stdin)
        self.xelatex_stdout = codecs.getreader("utf-8")(xelatex.stdout)
        
        # cache for strings already processed
        self.str_cache = {}
    
    def __del__(self):
        self.xelatex.terminate()
        self.xelatex.wait()
        try:
            os.remove("texput.log")
            os.remove("texput.aux")
        except:
            pass
    
    def _wait_for_prompt(self):
        """
        Read all bytes from XeLaTeX stdout until a new line starts with a *.
        """
        buf = [""]
        while True:
            buf.append(self.xelatex_stdout.read(1))
            if buf[-1] == "*" and buf[-2] == "\n":
                break
            if buf[-1] == "":
                raise XelatexError("XeLaTeX halted", u"".join(buf))
        return "".join(buf)

    def get_width_height_descent(self, text, fontsize):
        """
        Get the width, total height and descent for a text typesetted by the
        current Xelatex environment.
        """        
        if debug: print "obtain metrics for: %s" % text
        
        # replace unknown \mathdefault command from matplotlib
        text = mathdefault_replace(text)
        
        # change fontsize and define textbox
        textbox = u"\\sbox0{\\fontsize{%f}{%f}\\selectfont{%s}}\n" % (fontsize, fontsize*1.2, text)
        # check cache
        if textbox in self.str_cache:
            return self.str_cache[textbox]
        
        # send textbox to xelatex and wait for prompt
        self.xelatex_stdin.write(unicode(textbox))
        self.xelatex_stdin.flush()
        try:
            self._wait_for_prompt()
        except XelatexError as e:
            msg = u"Error processing '%s'\nXelatex Output:\n%s" % (text, e.latex_output)
            raise ValueError(msg)

        # typeout width, height and text offset of the last textbox
        query = "\\typeout{\\the\\wd0,\\the\\ht0,\\the\\dp0}\n"
        self.xelatex_stdin.write(query)
        self.xelatex_stdin.flush()
        # read answer from latex and advance to the next prompt
        try:
            answer = self._wait_for_prompt()
        except XelatexError as e:
            msg = u"Error processing '%s'\nXelatex Output:\n%s" % (text, e.latex_output)
            raise ValueError(msg)
        
        # parse metrics from the answer string
        try:
            width, height, offset = answer.split("\n")[0].split(",")
        except:
            msg = "Error processing '%s'\nXelatex Output:\n%s" % (text, answer)
            raise ValueError(msg)
        w, h, o = float(width[:-2]), float(height[:-2]), float(offset[:-2])
        
        # the height returned from xelatex goes from base to top.
        # the height matplotlib expects goes from bottom to top.
        self.str_cache[textbox] = (w, h+o, o)
        return w, h+o, o

class RendererPgf(RendererBase):
    
    xelatexManager = None
    
    def __init__(self, figure, fh, draw_texts=True):
        """
        Creates a new Pgf renderer that translates any drawing instruction
        into commands to be interpreted in a latex pgfpicture environment.
        
        If `draw_texts` is False, the draw_text calls are ignored and the
        text elements must be rendered in a different way.
        """
        RendererBase.__init__(self)
        self.dpi = figure.dpi
        self.fh = fh
        self.figure = figure
        self.draw_texts = draw_texts
        self.image_counter = 0
        
        # create a shared xelatexmanager
        if self.xelatexManager is None:
            RendererPgf.xelatexManager = XelatexManager()

    def draw_markers(self, gc, marker_path, marker_trans, path, trans, rgbFace=None):
        writeln(self.fh, r"\begin{pgfscope}")

        # set style and clip
        self._pgf_clip(gc)
        self._pgf_path_styles(gc, rgbFace)
     
        # build marker definition
        bl, tr = marker_path.get_extents(marker_trans).get_points()
        writeln(self.fh, r"\pgfsys@defobject{currentmarker}{\pgfqpointxy{%f}{%f}}{\pgfqpointxy{%f}{%f}}{" % (bl[0],bl[1],tr[0],tr[1]))
        self._pgf_path(gc, marker_path, marker_trans, filled=bool(rgbFace))
        writeln(self.fh, r"}")
        
        # convert from display units to pt, transformshift needs real units
        f = 72.0/self.dpi
        # draw marker for each vertex
        for point, code in path.iter_segments(trans, simplify=False):
            x, y = tuple(point)
            writeln(self.fh, r"\begin{pgfscope}")
            writeln(self.fh, r"\pgfsys@transformshift{%fpt}{%fpt}" % (f*x,f*y))
            writeln(self.fh, r"\pgfsys@useobject{currentmarker}{}")
            writeln(self.fh, r"\end{pgfscope}")

        writeln(self.fh, r"\end{pgfscope}")
    
    def draw_path(self, gc, path, transform, rgbFace=None):
        writeln(self.fh, r"\begin{pgfscope}")
        self._pgf_clip(gc)
        self._pgf_path_styles(gc, rgbFace)
        self._pgf_path(gc, path, transform, filled=bool(rgbFace))
        writeln(self.fh, r"\end{pgfscope}")
    
    def _pgf_clip(self, gc):
        bbox = gc.get_clip_rectangle()
        if bbox:
            p1, p2 = bbox.get_points()
            w, h = p2-p1
            writeln(self.fh, r"\pgfpathrectangle{\pgfqpointxy{%f}{%f}}{\pgfqpointxy{%f}{%f}} " % (p1[0],p1[1],w,h))
            writeln(self.fh, r"\pgfusepath{clip}")
    
    def _pgf_path_styles(self, gc, rgbFace):
        # cap style
        capstyles = {"butt": r"\pgfsetbuttcap",
                     "round": r"\pgfsetroundcap",
                     "projecting": r"\pgfsetrectcap"}
        writeln(self.fh, capstyles[gc.get_capstyle()])

        # join style
        joinstyles = {"miter": r"\pgfsetmiterjoin",
                      "round": r"\pgfsetroundjoin",
                      "bevel": r"\pgfsetbeveljoin"}
        writeln(self.fh, joinstyles[gc.get_joinstyle()])
        
        # filling
        if rgbFace is not None:
            writeln(self.fh, r"\definecolor{currentfill}{rgb}{%f,%f,%f}" % tuple(rgbFace[:3]))
            writeln(self.fh, r"\pgfsetfillcolor{currentfill}")
            
        # linewidth and color
        lw = gc.get_linewidth()
        writeln(self.fh, r"\pgfsetlinewidth{%fpt}" % lw)
        writeln(self.fh, r"\definecolor{currentstroke}{rgb}{%f,%f,%f}" % gc.get_rgb()[:3])
        writeln(self.fh, r"\pgfsetstrokecolor{currentstroke}")
        
        # line style
        ls = gc.get_linestyle(None)
        if ls == "solid":
            writeln(self.fh, r"\pgfsetdash{}{0pt}")
        elif ls == "dashed":
            writeln(self.fh, r"\pgfsetdash{{%fpt}{%fpt}}{0cm}" % (2.5*lw, 2.5*lw))
        elif ls == "dashdot":
            writeln(self.fh, r"\pgfsetdash{{%fpt}{%fpt}{%fpt}{%fpt}}{0cm}" % (3*lw, 3*lw, 1*lw, 3*lw))
        elif "dotted":
            writeln(self.fh, r"\pgfsetdash{{%fpt}{%fpt}}{0cm}" % (lw, 3*lw))
    
    def _pgf_path(self, gc, path, transform, filled):        
        # build path
        for points, code in path.iter_segments(transform):
            if code == Path.MOVETO:
                x, y = tuple(points)
                writeln(self.fh, r"\pgfpathmoveto{\pgfqpointxy{%f}{%f}}" % (x,y))
            elif code == Path.CLOSEPOLY:
                writeln(self.fh, r"\pgfpathclose")
            elif code == Path.LINETO:
                x, y = tuple(points)
                writeln(self.fh, r"\pgfpathlineto{\pgfqpointxy{%f}{%f}}" % (x,y))
            elif code == Path.CURVE3:
                cx, cy, px, py = tuple(points)
                writeln(self.fh, r"\pgfpathquadraticcurveto{\pgfqpointxy{%f}{%f}}{\pgfqpointxy{%f}{%f}}" % tuple(points))
            elif code == Path.CURVE4:
                writeln(self.fh, r"\pgfpathcurveto{\pgfqpointxy{%f}{%f}}{\pgfqpointxy{%f}{%f}}{\pgfqpointxy{%f}{%f}}" % tuple(points))

        # draw path
        actions = "stroke,fill" if filled else "stroke"
        writeln(self.fh, r"\pgfusepath{%s}" % actions)

    def draw_image(self, gc, x, y, im):
        # TODO: there is probably a lot to do here like transforming and
        # clipping the image, but there is no documentation for the behavior
        # of this function. however, this simple implementation works for
        # basic needs.
        
        # filename for this image
        path = os.path.dirname(self.fh.name)
        fname = os.path.splitext(os.path.basename(self.fh.name))[0]
        fname_img = "%s-img%d.png" % (fname, self.image_counter)
        self.image_counter += 1
        # write image to a png file
        # for some reason, the image must be flipped upside down
        im.flipud_out()
        rows, cols, buf = im.as_rgba_str()
        _png.write_png(buf, cols, rows, os.path.join(path, fname_img))
        # include the png in the pgf picture
        h, w = im.get_size_out()
        h, w = h/self.dpi, w/self.dpi
        x, y = x/self.dpi, y/self.dpi
        writeln(self.fh, r"\pgftext[at=\pgfqpoint{%fin}{%fin},left,bottom]{\pgfimage[interpolate=true,width=%fin,height=%fin]{%s}}" % (x, y, w, h, fname_img))

    def draw_text(self, gc, x, y, s, prop, angle, ismath=False):
        if not self.draw_texts: return

        # replace unknown \mathdefault command from matplotlib
        s = mathdefault_replace(s)

        # check if the math is supposed to be displaystyled
        if displaymath: s = math_to_displaystyle(s)
        
        # TODO: the text coordinates are given in pt units, right?
        x = x*72.0/self.dpi
        y = y*72.0/self.dpi
        # include commands for changing the fontsize
        fontsize = prop.get_size_in_points()
        s = ur"{\fontsize{%f}{%f}\selectfont{%s}}" % (fontsize, fontsize*1.2, s)
        # draw text at given coordinates
        writeln(self.fh, r"\pgftext[left,bottom,x=%f,y=%f,rotate=%f]{%s}\n" % (x,y,angle,s))

    def get_text_width_height_descent(self, s, prop, ismath):
        # TODO: except from reading the fontsize, all text properties are
        # ignored for now.
        fontsize = prop.get_size_in_points()
        
        # check if the math is supposed to be displaystyled
        if displaymath: s = math_to_displaystyle(s)
        
        # get text metrics in units of pt, convert to display units
        w, h, d = self.xelatexManager.get_width_height_descent(s, fontsize)
        f = self.dpi/72.0
        return w*f, h*f, d*f

    def flipy(self):
        return False

    def get_canvas_width_height(self):
        return self.figure.get_figwidth(), self.figure.get_figheight()

    def new_gc(self):
        return GraphicsContextPgf()
 

class GraphicsContextPgf(GraphicsContextBase):
    pass

########################################################################

def draw_if_interactive():
    pass

def new_figure_manager(num, *args, **kwargs):
    """
    Create a new figure manager instance
    """
    # if a main-level app must be created, this is the usual place to
    # do it -- see backend_wx, backend_wxagg and backend_tkagg for
    # examples.  Not all GUIs require explicit instantiation of a
    # main-level app (egg backend_gtk, backend_gtkagg) for pylab
    FigureClass = kwargs.pop('FigureClass', Figure)
    thisFig = FigureClass(*args, **kwargs)
    canvas = FigureCanvasPgf(thisFig)
    manager = FigureManagerPgf(canvas, num)
    return manager


class FigureCanvasPgf(FigureCanvasBase):
    filetypes = {"pgf": "Latex PGF picture",
                 "pdf": "XeLaTeX compiled PGF picture"}

    def __init__(self, *args):
        FigureCanvasBase.__init__(self, *args)

    def get_default_filetype(self):
        return 'pgf'

    def print_pgf(self, filename, *args, **kwargs):
        """
        Output pgf commands for drawing the figure so it can be included and
        rendered in latex documents.        
        """
        
        header_text = r"""%% Pgf figure exported from matplotlib.
%%
%% To include the image in your LaTeX document, write
%%   \input{<filename>.pgf}
%%
%% Make sure to load the required packages in your main document
%%   \usepackage{pgf}
%%   \usepackage{pgfsys}
%"""
        
        w, h = self.figure.get_figwidth(), self.figure.get_figheight()
        dpi = self.figure.dpi
        
        # start a pgfpicture environment and set a bounding box
        fh = codecs.open(filename, "wt", encoding="utf-8")
        writeln(fh, header_text)
        writeln(fh, r"\begingroup")
        writeln(fh, r"\makeatletter")
        writeln(fh, r"\begin{pgfpicture}")
        writeln(fh, r"\pgfpathrectangle{\pgfpointorigin}{\pgfqpoint{%fin}{%fin}}" % (w,h))
        writeln(fh, r"\pgfusepath{use as bounding box}")
        writeln(fh, r"\pgfsetxvec{\pgfqpoint{%fin}{0in}}" % (1./dpi))
        writeln(fh, r"\pgfsetyvec{\pgfqpoint{0in}{%fin}}" % (1./dpi))
        
        # for pgf output, do not process text elements using the Renderer
        renderer = RendererPgf(self.figure, fh, draw_texts=False)
        self.figure.draw(renderer)
        # manually extract text elements from the figure and draw them
        # TODO: this wouldn't be neccessary if draw_text received Text instances as documented
        self._render_texts_pgf(fh)

        # end the pgfpicture environment
        writeln(fh, r"\end{pgfpicture}")
        writeln(fh, r"\makeatother")
        writeln(fh, r"\endgroup")
    
    def print_pdf(self, filename, *args, **kwargs):
        """
        Use Xelatex to compile a Pgf generated figure to PDF.
        """
        w, h = self.figure.get_figwidth(), self.figure.get_figheight()
        
        target = os.path.abspath(filename)
        tmpdir = tempfile.mkdtemp()
        cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            self.print_pgf("figure.pgf")

            setmainfont = r"\setmainfont{%s}" % fontfamily if fontfamily else ""
            latexcode = r"""
\documentclass[12pt]{minimal}
\usepackage[paperwidth=%fin, paperheight=%fin, margin=0in]{geometry}
%s
\usepackage{fontspec}
%s
\usepackage{pgf}

\begin{document}
\centering
\input{figure.pgf}
\end{document}""" % (w, h, latex_preamble, setmainfont)
            with codecs.open("figure.tex", "wt", "utf-8") as fh:
                fh.write(latexcode)
            
            cmd = 'xelatex -interaction=nonstopmode "%s" > figure.stdout' % ("figure.tex")
            exit_status = os.system(cmd)
            if exit_status:
                raise RuntimeError("XeLaTeX was not able to process your file")
            shutil.copyfile("figure.pdf", target)
        finally:
            shutil.rmtree(tmpdir)
            os.chdir(cwd)

    def _render_texts_pgf(self, fh):
        # alignment anchors
        valign = {"top": "top", "bottom": "bottom", "baseline": "base", "center": ""}
        halign = {"left": "left", "right": "right", "center": ""}
        # alignment anchors for 90deg. rotated labels        
        rvalign = {"top": "left", "bottom": "right", "baseline": "right", "center": ""}
        rhalign = {"left": "top", "right": "bottom", "center": ""}
        
        # TODO: matplotlib does not hide unused tick labels yet, workaround
        for tick in self.figure.findobj(matplotlib.axis.Tick):
            tick.label1.set_visible(tick.label1On)
            tick.label2.set_visible(tick.label2On)
        # TODO: strange, first legend label is always "None", workaround
        for legend in self.figure.findobj(matplotlib.legend.Legend):
            labels = legend.findobj(matplotlib.text.Text)
            labels[0].set_visible(False)
        # TODO: strange, legend child labels are duplicated,
        # find a list of unique text objects as workaround
        texts = self.figure.findobj(match=Text, include_self=False)
        texts = list(set(texts))
        
        # draw text elements
        for text in texts:
            s = text.get_text()
            if not s or not text.get_visible(): continue
        
            s = mathdefault_replace(s)
            if displaymath: s = math_to_displaystyle(s)
        
            fontsize = text.get_fontsize()
            angle = text.get_rotation()
            transform = text.get_transform()
            x, y = transform.transform_point(text.get_position())
            # TODO: why are the coordinate's units different from path units?
            x *= 72./self.figure.dpi
            y *= 72./self.figure.dpi
            # TODO: positioning behavior unknown for rotated elements, right
            # now only the case for 90deg rotation is supported
            if angle == 90.:
                align = rvalign[text.get_va()] + "," + rhalign[text.get_ha()]
            else:
                align = valign[text.get_va()] + "," + halign[text.get_ha()]
    
            s = ur"{\fontsize{%f}{%f}\selectfont %s}" % (fontsize, fontsize*1.2, s)
            writeln(fh, ur"\pgftext[%s,x=%f,y=%f,rotate=%f]{%s}" % (align,x,y,angle,s))
    
    def get_renderer(self):
        return RendererPgf(self.figure, None, draw_texts=False)

class FigureManagerPgf(FigureManagerBase):
    def __init__(self, *args):
        FigureManagerBase.__init__(self, *args)

########################################################################

FigureManager = FigureManagerPgf
