from __future__ import division

import os
import re
import shutil
import tempfile
import codecs
import subprocess

import matplotlib
from matplotlib.backend_bases import RendererBase, GraphicsContextBase,\
     FigureManagerBase, FigureCanvasBase
from matplotlib.figure import Figure
from matplotlib.text import Text
from matplotlib.path import Path
from matplotlib import _png, rcParams

def writeln(fh, line):
    fh.write(line)
    fh.write("%\n")

# debug switch
debug = rcParams.get("pgf.debug", False)

# setting the default font and preamble
# TODO: Computer Modern Unicode is not included in current latex distributions
# the default font doesn't provide much of the symbols though :/
fontfamily = rcParams.get("pgf.font", "CMU Serif")
latex_preamble = rcParams.get("pgf.preamble", "")

# TODO: the mathdefault macro matplotlib adds to some texts is unknown to me
latex_preamble += "\\newcommand{\\mathdefault}[1]{#1}\n"

# replace every math environment with displaystyle math
math_search = re.compile(r"\$([^\$]+)\$")
math_replace = lambda match: r"\(\displaystyle %s\)" % match.group(1)
def math_to_displaystyle(text):
    return math_search.sub(math_replace, text)

class XelatexManager:
    """
    The XelatexManager is required for getting font metrics from Xelatex.
    """
    
    # create header with some content, else latex will load some math fonts
    # later when we don't expect the additional output on stdout
    # TODO: is this sufficient?
    latex_header = u"""\\documentclass{minimal}
%s
\\usepackage{fontspec}
\\setmainfont{%s}
\\begin{document}
text $math \mu$ %% force latex to load fonts now
\\typeout{pgf_backend_query_start}
""" % (latex_preamble, fontfamily)

    latex_end = """
\\makeatletter
\\@@end
"""

    def __init__(self):
        # test xelatex setup to ensure a clean startup of the subprocess
        xelatex = subprocess.Popen(["xelatex"],
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE)
        xelatex.stdin.write(self.latex_header)
        xelatex.stdin.write(self.latex_end)
        xelatex.stdin.close()
        if xelatex.wait() != 0:
            raise RuntimeError("Xelatex returned an error, probably missing font or error in preamble")
        
        # open xelatex process
        xelatex = subprocess.Popen(["xelatex"],
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE)
        xelatex.stdin.write(self.latex_header)
        xelatex.stdin.flush()
        # read all lines until our 'pgf_backend_query_start' token appears
        while not xelatex.stdout.readline().startswith("*pgf_backend_query_start"):
            pass
        while xelatex.stdout.read(1) != '*':
            pass
        self.xelatex = xelatex
        self.xelatex_stdin = codecs.getwriter("utf-8")(xelatex.stdin)
        
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

    def get_width_height_descent(self, text, fontsize):
        if debug: print "xelatex metrics for: %s" % text
        # TODO: no error handling here. I haven't found a reliable way to
        # set a timeout for the readline methods yet, so if something doesnt
        # match the expected result the whole process blocks or we end up with
        # returned lines we dont' understand correctly.
        
        # change fontsize and define textbox
        textbox = u"\\sbox0{\\fontsize{%f}{%f}\\selectfont{%s}}\n" % (fontsize, fontsize*1.2, text)
        # check cache
        if textbox in self.str_cache:
            return self.str_cache[textbox]
        
        # send textbox to xelatex
        self.xelatex_stdin.write(unicode(textbox))
        self.xelatex_stdin.flush()
        # wait for the next xelatex prompt
        while self.xelatex.stdout.read(1) != "*":
            pass

        # typeout width, height and text offset of the last textbox
        query = "\\typeout{\\the\\wd0,\\the\\ht0,\\the\\dp0}\n"
        self.xelatex_stdin.write(query)
        self.xelatex_stdin.flush()
        # read answer from latex and advance stdout to the next prompt (*)
        answer = self.xelatex.stdout.readline().rstrip()
        while self.xelatex.stdout.read(1) != "*":
            pass
        
        # parse metrics from the answer string
        try:
            width, height, offset = answer.split(",")
        except:
            raise ValueError("Error processing string: %s" % text)
        w, h, o = float(width[:-2]), float(height[:-2]), float(offset[:-2])
        
        # the hight returned from xelatex goes from base to top.
        # the hight matplotlib expects goes from bottom to top.
        self.str_cache[textbox] = (w, h+o, o)
        return w, h+o, o

class RendererPgf(RendererBase):
    
    xelatexManager = None
    
    def __init__(self, figure, fh, draw_texts=True, use_xelatex_manager=False):
        RendererBase.__init__(self)
        self.dpi = figure.dpi
        self.fh = fh
        self.figure = figure
        self.draw_texts = draw_texts
        self.image_counter = 0
        
        # if we use the xelatex manager, create a shared one
        self.use_xelatex_manager = use_xelatex_manager
        if use_xelatex_manager and self.xelatexManager is None:
            RendererPgf.xelatexManager = XelatexManager()

    def draw_path(self, gc, path, transform, rgbFace=None):
        writeln(self.fh, r"\begin{pgfscope}")
        
        # clip
        bbox = gc.get_clip_rectangle()
        if bbox:
            p1, p2 = bbox.get_points()
            w, h = p2-p1
            writeln(self.fh, r"\pgfpathrectangle{\pgfqpointxy{%f}{%f}}{\pgfqpointxy{%f}{%f}} " % (p1[0],p1[1],w,h))
            writeln(self.fh, r"\pgfsetstrokecolor{red}")     
            writeln(self.fh, r"\pgfusepath{clip}")
        
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

        # set filling
        if rgbFace is not None:
            writeln(self.fh, r"\definecolor{currentfill}{rgb}{%f,%f,%f}" % tuple(rgbFace[:3]))
            writeln(self.fh, r"\pgfsetfillcolor{currentfill}")
            action_fill = "fill"
        else:
            action_fill = ""
            
        # set stroke style
        lw = gc.get_linewidth()
        writeln(self.fh, r"\pgfsetlinewidth{%fpt}" % lw)
        writeln(self.fh, r"\definecolor{currentstroke}{rgb}{%f,%f,%f}" % gc.get_rgb()[:3])
        writeln(self.fh, r"\pgfsetstrokecolor{currentstroke}")
        
        # TODO: have to find the exact dash-distances the other backends are using
        ls = gc.get_linestyle(None)
        if ls == "solid":
            writeln(self.fh, r"\pgfsetdash{}{0pt}")
        elif ls == "dashed":
            writeln(self.fh, r"\pgfsetdash{{%fpt}{%fpt}}{0cm}" % (2.5*lw, 2.5*lw))
        elif ls == "dashdot":
            writeln(self.fh, r"\pgfsetdash{{%fpt}{%fpt}{%fpt}{%fpt}}{0cm}" % (3*lw, 3*lw, 1*lw, 3*lw))
        elif "dotted":
            writeln(self.fh, r"\pgfsetdash{{%fpt}{%fpt}}{0cm}" % (lw, 3*lw))
                
        # draw
        writeln(self.fh, r"\pgfusepath{stroke,%s}" % action_fill)
        writeln(self.fh, r"\end{pgfscope}")

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
        rows, cols, buffer = im.as_rgba_str()
        _png.write_png(buffer, cols, rows, os.path.join(path, fname_img))
        # include the png in the pgf picture
        h, w = im.get_size_out()
        h, w = h/self.dpi, w/self.dpi
        x, y = x/self.dpi, y/self.dpi
        writeln(self.fh, r"\pgftext[at=\pgfqpoint{%fin}{%fin},left,bottom]{\pgfimage[interpolate=true,width=%fin,height=%fin]{%s}}" % (x, y, w, h, fname_img))

    def draw_text(self, gc, x, y, s, prop, angle, ismath=False):
        if not self.draw_texts: return
        # check if the math is supposed to be displaystyled
        if rcParams.get("pgf.displaymath", True):
            s = math_to_displaystyle(s)
        
        # TODO: the text coordinates are given in pt units, right?
        x = x*72.0/self.dpi
        y = y*72.0/self.dpi
        # include commands for changing the fontsize
        fontsize = prop.get_size_in_points()
        s = ur"{\fontsize{%f}{%f}\selectfont{%s}}" % (fontsize, fontsize*1.2, s)
        # draw text at given coordinates
        writeln(self.fh, r"\pgftext[left,bottom,x=%f,y=%f,rotate=%f]{%s}\n" % (x,y,angle,s))

    def get_text_width_height_descent(self, s, prop, ismath):
        fontsize = prop.get_size_in_points()
        
        # check if the math is supposed to be displaystyled
        if rcParams.get("pgf.displaymath", True):
            s = math_to_displaystyle(s)
        
        # get text size parameters in units of pt
        if self.use_xelatex_manager:
            texmanager = self.get_texmanager()
            w, h, d = self.xelatexManager.get_width_height_descent(s, fontsize)
        else:
            texmanager = self.get_texmanager()
            w, h, d = texmanager.get_text_width_height_descent(s, fontsize, renderer=self)

        # convert sizes in displayunits
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
        w, h = self.figure.get_figwidth(), self.figure.get_figheight()
        dpi = self.figure.dpi

        fh = codecs.open(filename, "wt", encoding="utf-8")
        writeln(fh, r"\begingroup")
        writeln(fh, r"\begin{pgfpicture}")
        writeln(fh, r"\pgfpathrectangle{\pgfpointorigin}{\pgfqpoint{%fin}{%fin}}" % (w,h))
        writeln(fh, r"\pgfusepath{use as bounding box}")
        writeln(fh, r"\pgfsetxvec{\pgfqpoint{%fin}{0in}}" % (1./dpi))
        writeln(fh, r"\pgfsetyvec{\pgfqpoint{0in}{%fin}}" % (1./dpi))
        
        use_xelatex_manager = rcParams.get("pgf.xelatexmanager", True)
        # for pgf output, do not process text elements using the Renderer
        renderer = RendererPgf(self.figure, fh, draw_texts=False,
                               use_xelatex_manager=use_xelatex_manager)
        self.figure.draw(renderer)
        # add text elements manually so we can place them according to their
        # alignment properties
        self._render_texts_pgf(fh)
        
        writeln(fh, r"\end{pgfpicture}")
        writeln(fh, r"\endgroup")
    
    def print_pdf(self, filename, *args, **kwargs):
        w, h = self.figure.get_figwidth(), self.figure.get_figheight()
        
        target = os.path.abspath(filename)
        tmpdir = tempfile.mkdtemp()
        cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            self.print_pgf("figure.pgf")

            latexcode = r"""
\documentclass[12pt]{minimal}
\usepackage[paperwidth=%fin, paperheight=%fin, margin=0in]{geometry}
%s
\usepackage{fontspec}
\setmainfont{%s}
\usepackage{tikz}

\begin{document}
\centering
\input{figure.pgf}
\end{document}""" % (w, h, latex_preamble, fontfamily)
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
        
        # TODO: matplotlib weirdness, hide invalid tick labels
        for tick in self.figure.findobj(matplotlib.axis.Tick):
            tick.label1.set_visible(tick.label1On)
            tick.label2.set_visible(tick.label2On)
        # TODO: matplotlib weirdness, first legend label is "None"
        for legend in self.figure.findobj(matplotlib.legend.Legend):
            labels = legend.findobj(matplotlib.text.Text)
            labels[0].set_visible(False)
        # TODO: matplotlib weirdness, legend child labels are duplicated,
        # find a list of unique text objects as workaround
        texts = self.figure.findobj(match=Text, include_self=False)
        texts = list(set(texts))

        displaymath = bool(rcParams.get("pgf.displaymath", True))
        
        # draw text elements
        for text in texts:
            s = text.get_text()
            if not s or not text.get_visible(): continue
        
            if displaymath:
                s = math_to_displaystyle(s)
        
            fontsize = text.get_fontsize()
            angle = text.get_rotation()
            transform = text.get_transform()
            x, y = transform.transform_point(text.get_position())
            # TODO: why are the text units different from path units?
            x *= 72./self.figure.dpi
            y *= 72./self.figure.dpi
            if angle == 90.:
                align = rvalign[text.get_va()] + "," + rhalign[text.get_ha()]
            else:
                # TODO: matplotlibs positioning behavior unknown for rotation
                align = valign[text.get_va()] + "," + halign[text.get_ha()]
    
            s = ur"{\fontsize{%f}{%f}\selectfont %s}" % (fontsize, fontsize*1.2, s)
            writeln(fh, ur"\pgftext[%s,x=%f,y=%f,rotate=%f]{%s}" % (align,x,y,angle,s))
    
    def get_renderer(self):
        use_xelatex_manager = rcParams.get("pgf.xelatexmanager", True)
        return RendererPgf(self.figure, None, draw_texts=False,
                           use_xelatex_manager=use_xelatex_manager)

class FigureManagerPgf(FigureManagerBase):
    def __init__(self, *args):
        FigureManagerBase.__init__(self, *args)

########################################################################

FigureManager = FigureManagerPgf
