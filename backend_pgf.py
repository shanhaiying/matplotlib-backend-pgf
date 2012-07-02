from __future__ import division

import os
import re
import shutil
import tempfile
import codecs
import subprocess
import warnings
warnings.formatwarning = lambda *args: str(args[0])

import matplotlib as mpl
from matplotlib.backend_bases import RendererBase, GraphicsContextBase,\
     FigureManagerBase, FigureCanvasBase
from matplotlib.figure import Figure
from matplotlib.text import Text
from matplotlib.path import Path
from matplotlib import _png, rcParams
from matplotlib import font_manager
from matplotlib.ft2font import FT2Font

###############################################################################
# settings read from rc

# debug switch
debug = bool(rcParams.get("pgf.debug", False))

# create a list of system fonts, all of these should work with xelatex
system_fonts = [FT2Font(f).family_name for f in font_manager.findSystemFonts()]
# font configuration
rcfonts = rcParams.get("pgf.rcfonts", True)
latex_fontspec = []
if not rcfonts:
    # use standard LaTeX fonts and use default serif font
    rcParams["font.family"] = "serif"
else:
    # try to find fonts from rc parameters
    families = ["serif", "sans-serif", "monospace"]
    fontspecs = [r"\setmainfont{%s}", r"\setsansfont{%s}", r"\setmonofont{%s}"]
    for family, fontspec in zip(families, fontspecs):
        matches = [f for f in rcParams["font."+family] if f in system_fonts]
        if matches:
            latex_fontspec.append(fontspec % matches[0])
        else:
            warnings.warn("No fonts found in font.%s, using LaTeX default.\n" % family)    
    if debug:
        print "font specification:", latex_fontspec
latex_fontspec = "\n".join(latex_fontspec)

# LaTeX preamble
latex_preamble = rcParams.get("pgf.preamble", "")
if type(latex_preamble) == list:
    latex_preamble = "\n".join(latex_preamble)

###############################################################################

# This almost made me cry!!!
# In the end, it's better to use only one unit for all coordinates, since the
# arithmetic in latex seems to produce inaccurate conversions.
latex_pt_to_in = 1./72.27
latex_in_to_pt = 1./latex_pt_to_in
mpl_pt_to_in = 1./72.
mpl_in_to_pt = 1./mpl_pt_to_in

###############################################################################
# helper functions

NO_ESCAPE = r"(?<!\\)(?:\\\\)*"
re_mathsep = re.compile(NO_ESCAPE + r"\$")
re_escapetext = re.compile(NO_ESCAPE + "([_^$%])")
repl_escapetext = lambda m: "\\" + m.group(1)
re_mathdefault = re.compile(NO_ESCAPE + r"(\\mathdefault)")
repl_mathdefault = lambda m: m.group(0)[:-len(m.group(1))]

def common_texification(text):
    """
    Do some necessary and/or useful substitutions for texts to be included in
    LaTeX documents.
    """

    # Sometimes, matplotlib adds the unknown command \mathdefault.
    # Not using \mathnormal instead since this looks odd for the latex cm font.
    text = re_mathdefault.sub(repl_mathdefault, text)

    # split text into normaltext and inline math parts
    parts = re_mathsep.split(text)
    for i, s in enumerate(parts):
        if not i%2:
            # textmode replacements
            s = re_escapetext.sub(repl_escapetext, s)
        else:
            # mathmode replacements
            s = r"\(\displaystyle %s\)" % s
        parts[i] = s
    
    return "".join(parts)

def writeln(fh, line):
    # every line of a file included with \input must be terminated with %
    # if not, latex will create additional vertical spaces for some reason
    fh.write(line)
    fh.write("%\n")

def _font_properties_str(prop):
    # translate font properties to latex commands, return as string
    commands = []

    families = {"serif": r"\rmfamily", "sans": r"\sffamily",
                "sans-serif": r"\sffamily", "monospace": r"\ttfamily"}
    family = prop.get_family()[0]
    if family in families:
        commands.append(families[family])
    elif family in system_fonts:
        commands.append(r"\setmainfont{%s}\rmfamily" % family)
    else:
        pass # print warning?

    size = prop.get_size_in_points()
    commands.append(r"\fontsize{%f}{%f}" % (size, size*1.2))

    styles = {"normal": r"", "italic": r"\itshape", "oblique": r"\slshape"}
    commands.append(styles[prop.get_style()])
    
    boldstyles = ["semibold", "demibold", "demi", "bold", "heavy",
                  "extra bold", "black"]
    if prop.get_weight() in boldstyles: commands.append(r"\bfseries")

    commands.append(r"\selectfont")
    return "".join(commands)


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
        latex_header = u"""\\documentclass{minimal}
%s
\\usepackage{fontspec}
%s
\\begin{document}
text $math \mu$ %% force latex to load fonts now
\\typeout{pgf_backend_query_start}
""" % (latex_preamble, latex_fontspec)

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

    def get_width_height_descent(self, text, prop):
        """
        Get the width, total height and descent for a text typesetted by the
        current Xelatex environment.
        """        
        if debug: print "obtain metrics for: %s" % text

        # apply font properties and define textbox
        prop_cmds = _font_properties_str(prop)
        textbox = u"\\sbox0{%s %s}\n" % (prop_cmds, text)

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
        
        # convert from display units to in
        f = 1./self.dpi

        # set style and clip
        self._print_pgf_clip(gc)
        self._print_pgf_path_styles(gc, rgbFace)
     
        # build marker definition
        bl, tr = marker_path.get_extents(marker_trans).get_points()
        coords = bl[0]*f, bl[1]*f, tr[0]*f, tr[1]*f
        writeln(self.fh, r"\pgfsys@defobject{currentmarker}{\pgfqpoint{%fin}{%fin}}{\pgfqpoint{%fin}{%fin}}{" % coords)
        self._print_pgf_path(marker_path, marker_trans)
        self._pgf_path_draw(stroke=gc.get_linewidth() != 0.0,
                            fill=rgbFace is not None)
        writeln(self.fh, r"}")
        
        # draw marker for each vertex
        for point, code in path.iter_segments(trans, simplify=False):
            x, y = tuple(point)
            writeln(self.fh, r"\begin{pgfscope}")
            writeln(self.fh, r"\pgfsys@transformshift{%fin}{%fin}" % (x*f,y*f))
            writeln(self.fh, r"\pgfsys@useobject{currentmarker}{}")
            writeln(self.fh, r"\end{pgfscope}")

        writeln(self.fh, r"\end{pgfscope}")
    
    def draw_path(self, gc, path, transform, rgbFace=None):
        writeln(self.fh, r"\begin{pgfscope}")
        self._print_pgf_clip(gc)
        self._print_pgf_path_styles(gc, rgbFace)
        self._print_pgf_path(path, transform)
        self._pgf_path_draw(stroke=gc.get_linewidth() != 0.0,
                            fill=rgbFace is not None)
        writeln(self.fh, r"\end{pgfscope}")
    
    def _print_pgf_clip(self, gc):
        f = 1./self.dpi
        # check for clip box
        bbox = gc.get_clip_rectangle()
        if bbox:
            p1, p2 = bbox.get_points()
            w, h = p2-p1
            coords = p1[0]*f, p1[1]*f, w*f, h*f
            writeln(self.fh, r"\pgfpathrectangle{\pgfqpoint{%fin}{%fin}}{\pgfqpoint{%fin}{%fin}} " % coords)
            writeln(self.fh, r"\pgfusepath{clip}")

        # check for clip path
        clippath, clippath_trans = gc.get_clip_path()
        if clippath is not None:
            self._print_pgf_path(clippath, clippath_trans)
            writeln(self.fh, r"\pgfusepath{clip}")
    
    def _print_pgf_path_styles(self, gc, rgbFace):
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
        has_fill = rgbFace is not None
        path_is_transparent = gc.get_alpha() != 1.0
        fill_is_transparent = has_fill and (len(rgbFace) > 3) and (rgbFace[3] != 1.0)
        if has_fill:
            writeln(self.fh, r"\definecolor{currentfill}{rgb}{%f,%f,%f}" % tuple(rgbFace[:3]))
            writeln(self.fh, r"\pgfsetfillcolor{currentfill}")
        if has_fill and (path_is_transparent or fill_is_transparent):
            opacity = gc.get_alpha() * 1.0 if not fill_is_transparent else rgbFace[3]
            writeln(self.fh, r"\pgfsetfillopacity{%f}" % opacity)
        
        # linewidth and color
        lw = gc.get_linewidth() * mpl_pt_to_in * latex_in_to_pt
        stroke_rgba = gc.get_rgb()
        writeln(self.fh, r"\pgfsetlinewidth{%fpt}" % lw)
        writeln(self.fh, r"\definecolor{currentstroke}{rgb}{%f,%f,%f}" % stroke_rgba[:3])
        writeln(self.fh, r"\pgfsetstrokecolor{currentstroke}")
        if gc.get_alpha() != 1.0:
            writeln(self.fh, r"\pgfsetstrokeopacity{%f}" % gc.get_alpha())
        
        # line style
        ls = gc.get_linestyle(None)
        if ls == "solid":
            writeln(self.fh, r"\pgfsetdash{}{0pt}")
        elif ls == "dashed":
            writeln(self.fh, r"\pgfsetdash{{%fpt}{%fpt}}{0pt}" % (2.5*lw, 2.5*lw))
        elif ls == "dashdot":
            writeln(self.fh, r"\pgfsetdash{{%fpt}{%fpt}{%fpt}{%fpt}}{0pt}" % (3*lw, 3*lw, 1*lw, 3*lw))
        elif "dotted":
            writeln(self.fh, r"\pgfsetdash{{%fpt}{%fpt}}{0pt}" % (lw, 3*lw))
    
    def _print_pgf_path(self, path, transform):
        f = 1./self.dpi
        # build path
        for points, code in path.iter_segments(transform):
            if code == Path.MOVETO:
                x, y = tuple(points)
                writeln(self.fh, r"\pgfpathmoveto{\pgfqpoint{%fin}{%fin}}" % (f*x,f*y))
            elif code == Path.CLOSEPOLY:
                writeln(self.fh, r"\pgfpathclose")
            elif code == Path.LINETO:
                x, y = tuple(points)
                writeln(self.fh, r"\pgfpathlineto{\pgfqpoint{%fin}{%fin}}" % (f*x,f*y))
            elif code == Path.CURVE3:
                cx, cy, px, py = tuple(points)
                coords = cx*f, cy*f, px*f, py*f
                writeln(self.fh, r"\pgfpathquadraticcurveto{\pgfqpoint{%fin}{%fin}}{\pgfqpoint{%fin}{%fin}}" % coords)
            elif code == Path.CURVE4:
                c1x, c1y, c2x, c2y, px, py = tuple(points)
                coords = c1x*f, c1y*f, c2x*f, c2y*f, px*f, py*f
                writeln(self.fh, r"\pgfpathcurveto{\pgfqpoint{%fin}{%fin}}{\pgfqpoint{%fin}{%fin}}{\pgfqpoint{%fin}{%fin}}" % coords)

    def _pgf_path_draw(self, stroke=True, fill=False):
        actions = []
        if stroke: actions.append("stroke")
        if fill: actions.append("fill")
        writeln(self.fh, r"\pgfusepath{%s}" % ",".join(actions))

    def draw_image(self, gc, x, y, im):
        # TODO: Almost no documentation for the behavior of this function.
        #       Something missing?
        
        # save the images to png files
        path = os.path.dirname(self.fh.name)
        fname = os.path.splitext(os.path.basename(self.fh.name))[0]
        fname_img = "%s-img%d.png" % (fname, self.image_counter)
        self.image_counter += 1
        im.flipud_out()
        rows, cols, buf = im.as_rgba_str()
        _png.write_png(buf, cols, rows, os.path.join(path, fname_img))

        # reference the image in the pgf picture
        writeln(self.fh, r"\begin{pgfscope}")
        self._print_pgf_clip(gc)
        h, w = im.get_size_out()
        f = 1./self.dpi # from display coords to inch
        writeln(self.fh, r"\pgftext[at=\pgfqpoint{%fin}{%fin},left,bottom]{\pgfimage[interpolate=true,width=%fin,height=%fin]{%s}}" % (x*f, y*f, w*f, h*f, fname_img))
        writeln(self.fh, r"\end{pgfscope}")

    def draw_text(self, gc, x, y, s, prop, angle, ismath=False):
        if not self.draw_texts: return

        s = common_texification(s)

        # apply font properties
        prop_cmds = _font_properties_str(prop)
        s = ur"{%s %s}" % (prop_cmds, s)

        # draw text at given coordinates
        x = x * 1./self.dpi
        y = y * 1./self.dpi
        writeln(self.fh, r"\begin{pgfscope}")
        alpha = gc.get_alpha()
        if alpha != 1.0:
            writeln(self.fh, r"\pgfsetfillopacity{%f}" % alpha)
            writeln(self.fh, r"\pgfsetstrokeopacity{%f}" % alpha)
        stroke_rgb = tuple(gc.get_rgb())[:3]
        if stroke_rgb != (0, 0, 0):
            writeln(self.fh, r"\definecolor{textcolor}{rgb}{%f,%f,%f}" % stroke_rgb)
            writeln(self.fh, r"\pgfsetstrokecolor{textcolor}")
            writeln(self.fh, r"\pgfsetfillcolor{textcolor}")
        writeln(self.fh, "\\pgftext[left,bottom,x=%fin,y=%fin,rotate=%f]{%s}\n" % (x,y,angle,s))
        writeln(self.fh, r"\end{pgfscope}")

    def get_text_width_height_descent(self, s, prop, ismath):       
        # check if the math is supposed to be displaystyled
        s = common_texification(s)

        # get text metrics in units of latex pt, convert to display units
        w, h, d = self.xelatexManager.get_width_height_descent(s, prop)
        # TODO: this should be latex_pt_to_in instead of mpl_pt_to_in
        # but having a little bit morespace around the text looks better,
        # plus the bounding box reported by xelatex is VERY narrow
        f = mpl_pt_to_in * self.dpi
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
        # figure size in units of in
        w, h = self.figure.get_figwidth(), self.figure.get_figheight()
        
        # start a pgfpicture environment and set a bounding box
        fh = codecs.open(filename, "wt", encoding="utf-8")
        writeln(fh, header_text)
        writeln(fh, r"\begingroup")
        writeln(fh, r"\makeatletter")
        writeln(fh, r"\begin{pgfpicture}")
        writeln(fh, r"\pgfpathrectangle{\pgfpointorigin}{\pgfqpoint{%fin}{%fin}}" % (w,h))
        writeln(fh, r"\pgfusepath{use as bounding box}")
        
        # TODO: Matplotlib does not send Text instances to the renderer as documented.
        # This means that we cannot anchor the text elements correctly so that
        # they stay aligned when changing the font size later.
        # Manually iterating through all text instances of a figure has proven
        # to be too much work since matplotlib behaves really weird sometimes.
        # -> _render_texts_pgf
        renderer = RendererPgf(self.figure, fh, draw_texts=True)
        self.figure.draw(renderer)

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
\end{document}""" % (w, h, latex_preamble, latex_fontspec)
            with codecs.open("figure.tex", "wt", "utf-8") as fh:
                fh.write(latexcode)
            
            cmd = 'xelatex -interaction=nonstopmode "%s" > figure.stdout' % ("figure.tex")
            exit_status = os.system(cmd)
            if exit_status:
                shutil.copyfile("figure.stdout", target+".err")
                raise RuntimeError("XeLaTeX was not able to process your file.\nXeLaTeX stdout saved to %s" % (target+".err"))
            shutil.copyfile("figure.pdf", target)
        finally:
            shutil.rmtree(tmpdir)
            os.chdir(cwd)

    def _render_texts_pgf(self, fh):
        # TODO: currently unused code path
        
        # alignment anchors
        valign = {"top": "top", "bottom": "bottom", "baseline": "base", "center": ""}
        halign = {"left": "left", "right": "right", "center": ""}
        # alignment anchors for 90deg. rotated labels        
        rvalign = {"top": "left", "bottom": "right", "baseline": "right", "center": ""}
        rhalign = {"left": "top", "right": "bottom", "center": ""}
        
        # TODO: matplotlib does not hide unused tick labels yet, workaround
        for tick in self.figure.findobj(mpl.axis.Tick):
            tick.label1.set_visible(tick.label1On)
            tick.label2.set_visible(tick.label2On)
        # TODO: strange, first legend label is always "None", workaround
        for legend in self.figure.findobj(mpl.legend.Legend):
            labels = legend.findobj(mpl.text.Text)
            labels[0].set_visible(False)
        # TODO: strange, legend child labels are duplicated,
        # find a list of unique text objects as workaround
        texts = self.figure.findobj(match=Text, include_self=False)
        texts = list(set(texts))
        
        # draw text elements
        for text in texts:
            s = text.get_text()
            if not s or not text.get_visible(): continue
        
            s = common_texification(s)
        
            fontsize = text.get_fontsize()
            angle = text.get_rotation()
            transform = text.get_transform()
            x, y = transform.transform_point(text.get_position())
            x = x * 1.0 / self.figure.dpi
            y = y * 1.0 / self.figure.dpi
            # TODO: positioning behavior unknown for rotated elements
            # right now only the alignment for 90deg rotations is correct
            if angle == 90.:
                align = rvalign[text.get_va()] + "," + rhalign[text.get_ha()]
            else:
                align = valign[text.get_va()] + "," + halign[text.get_ha()]
    
            s = ur"{\fontsize{%f}{%f}\selectfont %s}" % (fontsize, fontsize*1.2, s)
            writeln(fh, ur"\pgftext[%s,x=%fin,y=%fin,rotate=%f]{%s}" % (align,x,y,angle,s))
    
    def get_renderer(self):
        return RendererPgf(self.figure, None, draw_texts=False)

class FigureManagerPgf(FigureManagerBase):
    def __init__(self, *args):
        FigureManagerBase.__init__(self, *args)

########################################################################

FigureManager = FigureManagerPgf
