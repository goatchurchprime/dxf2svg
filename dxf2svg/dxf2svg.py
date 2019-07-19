#!/usr/bin/env python3 

import dxfgrabber, math
VERSION = "2019-02-20"

def preamble(d, f):
    minX = d.header['$EXTMIN'][0]
    minY = d.header['$EXTMIN'][1]
    maxX = d.header['$EXTMAX'][0]
    maxY = d.header['$EXTMAX'][1]
    if minX>maxX or minY>maxY:
        print("Junk window size", (minX, minY), (maxX, maxY))
        minX, minY, maxX, maxY = -1000, -1000, 1000, 1000
    SVG_PREAMBLE = '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="{0} {1} {2} {3}">\n'
    f(SVG_PREAMBLE.format(minX, -maxY, maxX - minX, maxY - minY))
    if d.header['$INSUNITS'] != 4:
        print("Need to convert units from", {1:"Inches", 2:"Feet", 5:"Centimeters" }.get(d.header['$INSUNITS'], ("unknown", d.header['$INSUNITS'])))
    fac = 1.0
    f('<g transform="scale(%f %f)">\n' % (fac, fac))
    

layercol= {"PLOT-LINES":"green", "PLOTLINES":"green", "CUT-LINE":"blue"}

def splinepathtostring(e):
    import nurbs.Curve
    curve = nurbs.Curve.Curve()
    curve.ctrlpts = [p[:2]  for p in e.control_points]
    curve.degree = e.degree
    curve.knotvector = e.knots
    #curve.knotvector = nurbs.utilities.knotvector_autogen(curve.degree, len(curve.ctrlpts))
    curve.weights = e.weights
    curve.evaluate_rational()
    return "".join("%s%f %f" % ("M" if i==0 else "L", p[0], -p[1])  for i, p in enumerate(curve.curvepts))

# See also arbitrary axis algorithm in http://paulbourke.net/dataformats/dxf/dxf10.html
# Seems to flip rotation around Y-axis, so only invert the X
def arcextrusionfac(e):
    if max(abs(e.extrusion[0]), abs(e.extrusion[1]), abs(abs(e.extrusion[2]) - 1)) > 1e-5:
        print("Unknown arc extrusion", e.extrusion)
    return 1 if e.extrusion[2] >= 0 else -1

def arcpathstring(e):
    x1 = e.center[0] + e.radius * math.cos(math.radians(e.start_angle))
    y1 = e.center[1] + e.radius * math.sin(math.radians(e.start_angle))
    x2 = e.center[0] + e.radius * math.cos(math.radians(e.end_angle))
    y2 = e.center[1] + e.radius * math.sin(math.radians(e.end_angle))
    angdiff = e.end_angle - e.start_angle
    while angdiff >= 360: angdiff -= 360
    while angdiff < 0:  angdiff += 360
    exfac = arcextrusionfac(e)
    largearcflag = int(angdiff > 180)
    sweepflag = 1 if exfac < 0 else 0
    return 'M {0} {1} A {2} {3} {4} {5} {6} {7} {8} '.format(x1*exfac, -y1, 
            e.radius, e.radius, 0, largearcflag, sweepflag, x2*exfac, -y2)

# https://www.autodesk.com/techpubs/autocad/acad2000/dxf/entities_section.htm
SVG_LINE = '<line class="{layername}" x1="{0}" y1="{1}" x2="{2}" y2="{3}" stroke="{4}" stroke-width="{5:.2f}" />\n'
SVG_PATH = '<path class="{layername}" d="{0}{1}" fill="none" stroke="{2}" stroke-width="{3:.2f}" />\n'
SVG_CIRCLE = '<circle class="{layername}" cx="{0}" cy="{1}" r="{2}" stroke="{3}" stroke-width="{4}" fill="none" />\n'
unhandledentities = { }
def outent(e, fwrite, col, layername, th):
    if e.dxftype == "LINE":
        fwrite(SVG_LINE.format(e.start[0], -e.start[1], e.end[0], -e.end[1], col, th, layername=layername))
    elif e.dxftype == "ARC":
        fwrite(SVG_PATH.format(arcpathstring(e), "", col, th, layername=layername))
    elif e.dxftype == "LWPOLYLINE":
        pth = "".join("%s%f %f" % ("M" if i==0 else "L", p[0], -p[1])  for i, p in enumerate(e.points))
        fwrite(SVG_PATH.format(pth, ("Z" if e.is_closed else ""), col, th, layername=layername))
    elif e.dxftype == "POLYLINE":  # this can do 2D meshes (I think the is_closed only applies to this one, not the LWPOLYLINE)
        pth = "".join("%s%f %f" % ("M" if i==0 else "L", p[0], -p[1])  for i, p in enumerate(e.points))
        fwrite(SVG_PATH.format(pth,  ("Z" if e.is_closed else ""), col, th, layername=layername))
    elif e.dxftype == "SPLINE":
        fwrite(SVG_PATH.format(splinepathtostring(e), "", col, th, layername=layername))
    elif e.dxftype == "CIRCLE":
        exfac = arcextrusionfac(e)
        fwrite(SVG_CIRCLE.format(e.center[0]*exfac, -e.center[1], e.radius, col, 5+th, layername=layername))
    else:
        if e.dxftype not in unhandledentities:
            unhandledentities[e.dxftype] = 0
        unhandledentities[e.dxftype] += 1
        #print("unhandled entity", e.dxftype)

# should also handle the color24 values too    
dxfcolors = ['#000000', '#FF0000', '#FFFF00', '#00FF00', '#00FFFF', '#0000FF', '#FF00FF', '#000000', '#808080', '#C0C0C0', '#FF0000', '#FF7F7F', '#CC0000', '#CC6666', '#990000', '#994C4C', '#7F0000', '#7F3F3F', '#4C0000', '#4C2626', '#FF3F00', '#FF9F7F', '#CC3300', '#CC7F66', '#992600', '#995F4C', '#7F1F00', '#7F4F3F', '#4C1300', '#4C2F26', '#FF7F00', '#FFBF7F', '#CC6600', '#CC9966', '#994C00', '#99724C', '#7F3F00', '#7F5F3F', '#4C2600', '#4C3926', '#FFBF00', '#FFDF7F', '#CC9900', '#CCB266', '#997200', '#99854C', '#7F5F00', '#7F6F3F', '#4C3900', '#4C4226', '#FFFF00', '#FFFF7F', '#CCCC00', '#CCCC66', '#999900', '#99994C', '#7F7F00', '#7F7F3F', '#4C4C00', '#4C4C26', '#BFFF00', '#DFFF7F', '#99CC00', '#B2CC66', '#729900', '#85994C', '#5F7F00', '#6F7F3F', '#394C00', '#424C26', '#7FFF00', '#BFFF7F', '#66CC00', '#99CC66', '#4C9900', '#72994C', '#3F7F00', '#5F7F3F', '#264C00', '#394C26', '#3FFF00', '#9FFF7F', '#33CC00', '#7FCC66', '#269900', '#5F994C', '#1F7F00', '#4F7F3F', '#134C00', '#2F4C26', '#00FF00', '#7FFF7F', '#00CC00', '#66CC66', '#009900', '#4C994C', '#007F00', '#3F7F3F', '#004C00', '#264C26', '#00FF3F', '#7FFF9F', '#00CC33', '#66CC7F', '#009926', '#4C995F', '#007F1F', '#3F7F4F', '#004C13', '#264C2F', '#00FF7F', '#7FFFBF', '#00CC66', '#66CC99', '#00994C', '#4C9972', '#007F3F', '#3F7F5F', '#004C26', '#264C39', '#00FFBF', '#7FFFDF', '#00CC99', '#66CCB2', '#009972', '#4C9985', '#007F5F', '#3F7F6F', '#004C39', '#264C42', '#00FFFF', '#7FFFFF', '#00CCCC', '#66CCCC', '#009999', '#4C9999', '#007F7F', '#3F7F7F', '#004C4C', '#264C4C', '#00BFFF', '#7FDFFF', '#0099CC', '#66B2CC', '#007299', '#4C8599', '#005F7F', '#3F6F7F', '#00394C', '#26424C', '#007FFF', '#7FBFFF', '#0066CC', '#6699CC', '#004C99', '#4C7299', '#003F7F', '#3F5F7F', '#00264C', '#26394C', '#0042FF', '#7F9FFF', '#0033CC', '#667FCC', '#002699', '#4C5F99', '#001F7F', '#3F4F7F', '#00134C', '#262F4C', '#0000FF', '#7F7FFF', '#0000CC', '#6666CC', '#000099', '#4C4C99', '#00007F', '#3F3F7F', '#00004C', '#26264C', '#3F00FF', '#9F7FFF', '#3200CC', '#7F66CC', '#260099', '#5F4C99', '#1F007F', '#4F3F7F', '#13004C', '#2F264C', '#7F00FF', '#BF7FFF', '#6600CC', '#9966CC', '#4C0099', '#724C99', '#3F007F', '#5F3F7F', '#26004C', '#39264C', '#BF00FF', '#DF7FFF', '#9900CC', '#B266CC', '#720099', '#854C99', '#5F007F', '#6F3F7F', '#39004C', '#42264C', '#FF00FF', '#FF7FFF', '#CC00CC', '#CC66CC', '#990099', '#994C99', '#7F007F', '#7F3F7F', '#4C004C', '#4C264C', '#FF00BF', '#FF7FDF', '#CC0099', '#CC66B2', '#990072', '#994C85', '#7F005F', '#7F3F0B', '#4C0039', '#4C2642', '#FF007F', '#FF7FBF', '#CC0066', '#CC6699', '#99004C', '#994C72', '#7F003F', '#7F3F5F', '#4C0026', '#4C2639', '#FF003F', '#FF7F9F', '#CC0033', '#CC667F', '#990026', '#994C5F', '#7F001F', '#7F3F4F', '#4C0013', '#4C262F', '#333333', '#5B5B5B', '#848484', '#ADADAD', '#D6D6D6', '#FFFFFF']
        
SVG_G = '<g class="{layername}" transform="translate({translate[0]} {translate[1]}) rotate({rotate}) scale({scale[0]}, {scale[1]})" stroke="{stroke}">\n'
def makesvgentitiesrecurse(d, entities, fwrite, block):
    for i, e in enumerate(entities):
        if e.color == 256:
            colnum = d.layers[e.layer].color
        elif e.color == 0:
            colnum = block.color
        else:
            colnum = e.color
        col = dxfcolors[colnum]
        layername = e.layer
        
        if e.dxftype == "INSERT":
            # need to flip the Y, and (not checked) I think the rotation is inverted as well
            col = layercol.get(e.layer, 'black')
            grec = SVG_G.format(layername=layername, translate=(e.insert[0], -e.insert[1]), rotate=-e.rotation, scale=e.scale, stroke=col)
            print("blockscale", grec)
            fwrite(grec)
            makesvgentitiesrecurse(d, list(d.blocks[e.name]), fwrite, e)
            fout.write("</g>\n")
        else:
            outent(e, fwrite, col, layername, 3)
    
def makesvg():
    fout = open("test1.svg", "w")
    preamble(d, fout.write)
    makesvgentitiesrecurse(d, d.entities, fout.write)
    fout.write("</g>\n")
    fout.write("</svg>\n")
    fout.close()

# main case with further libraries loaded and some command line help stuff
if __name__ == "__main__":
    from optparse import OptionParser
    import re
    parser = OptionParser()
    parser.add_option("-d", "--dxf",        dest="dxf",        metavar="FILE",                    help="Input dxf file")
    parser.add_option("-s", "--svg",        dest="svg",        metavar="FILE",                    help="Output dxf file")
    parser.add_option("-v", "--version",    action="store_true")
    parser.description = "Convert dxf to svg in a form that is going to be debuggable "
    
    # Code is here: https://bitbucket.org/goatchurch/survexprocessing
    options, args = parser.parse_args()
    
    # push command line args that look like files into file options 
    if len(args) >= 1 and re.search("(?i)\.dxf$", args[0]) and not options.dxf:
        options.dxf = args.pop(0)
    if len(args) >= 1 and re.search("(?i)\.svg$", args[0]) and not options.svg:
        options.svg = args.pop(0)
    if options.version:
        print("version:", VERSION)
    if not options.dxf:
        if not options.version:
            parser.print_help()
        exit(1)
    if not options.svg: 
        options.svg = re.sub("(?i)\.dxf$", "", options.dxf)+".svg"
    
    d = dxfgrabber.readfile(options.dxf)
    svgcols = ['mediumorchid', 'brown', 'magenta', 'green', 'grey', 'darkgoldenrod', 'lavender', 'honeydew', 'royalblue', 'maroon','palegoldenrod']
    layercol.update({k:v  for k, v in zip(d.layers.names(), svgcols)  if k not in layercol})

    fout = open(options.svg, "w")
    preamble(d, fout.write)
    makesvgentitiesrecurse(d, d.entities, fout.write, None)
    fout.write("</g>\n")
    fout.write("</svg>\n")
    fout.close()
    if unhandledentities:
        print("unhandledentities count", unhandledentities)

