#!/usr/bin/env python3 

import dxfgrabber, math

def preamble(d, f):
    minX = d.header['$EXTMIN'][0]
    minY = d.header['$EXTMIN'][1]
    maxX = d.header['$EXTMAX'][0]
    maxY = d.header['$EXTMAX'][1]
    SVG_PREAMBLE = '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="{0} {1} {2} {3}">\n'
    f(SVG_PREAMBLE.format(minX, -maxY, maxX - minX, maxY - minY))

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

def arcpathstring(e):
    x1 = e.center[0] + e.radius * math.cos(math.radians(e.start_angle))
    y1 = e.center[1] + e.radius * math.sin(math.radians(e.start_angle))
    x2 = e.center[0] + e.radius * math.cos(math.radians(e.end_angle))
    y2 = e.center[1] + e.radius * math.sin(math.radians(e.end_angle))
    angdiff = e.end_angle - e.start_angle
    while angdiff >= 360: angdiff -= 360
    while angdiff < 0:  angdiff += 360
    return 'M {0} {1} A {2} {3} {4} {5} {6} {7} {8} '.format(x1, -y1, 
            e.radius, e.radius, 0, int(angdiff > 180), 0, x2, -y2)

#https://www.autodesk.com/techpubs/autocad/acad2000/dxf/entities_section.htm
SVG_LINE = '<line x1="{0}" y1="{1}" x2="{2}" y2="{3}" stroke="{4}" stroke-width="{5:.2f}" />\n'
SVG_PATH = '<path d="{0}{1}" fill="none" stroke="{2}" stroke-width="{3:.2f}" />\n'
SVG_CIRCLE = '<circle cx="{0}" cy="{1}" r="{2}" stroke="{3}" stroke-width="{4}" fill="none" />\n'
def outent(d, e, f, th):
    if e.dxftype == "LINE":      
        f(SVG_LINE.format(e.start[0], -e.start[1], e.end[0], -e.end[1], 
                          layercol.get(e.layer, 'black'), th))
    elif e.dxftype == "ARC":
        f(SVG_PATH.format(arcpathstring(e), layercol.get(e.layer, 'black'), th))
    elif e.dxftype == "LWPOLYLINE":
        pth = "".join("%s%f %f" % ("M" if i==0 else "L", p[0], -p[1])  for i, p in enumerate(e.points))
        f(SVG_PATH.format(pth, ("Z" if e.is_closed else ""), layercol.get(e.layer, 'black'), th))
    elif e.dxftype == "POLYLINE":  # this can do 2D meshes
        pth = "".join("%s%f %f" % ("M" if i==0 else "L", p[0], -p[1])  for i, p in enumerate(e.points))
        f(SVG_PATH.format(pth, "", layercol.get(e.layer, 'black'), th))
    elif e.dxftype == "SPLINE":
        f(SVG_PATH.format(splinepathtostring(e), "", layercol.get(e.layer, 'black'), th))
    elif e.dxftype == "CIRCLE":
        f(SVG_CIRCLE.format(e.center[0], -e.center[1], e.radius, layercol.get(e.layer, 'black'), 5+th))
    else:
        print([e.dxftype])
    
        
SVG_G = '<g transform="translate({0} {1})" stroke="{2}">\n'
def makesvgentitiesrecurse(entities, f):
    for i, e in enumerate(entities):
        if e.dxftype == "INSERT":
            print(i, e, e.__dict__, "\n")
            f(SVG_G.format(e.insert[0], e.insert[1], layercol.get(e.layer, 'black')))
            assert e.scale[0] == 1 and e.scale[1] == 1
            makesvgentitiesrecurse(list(d.blocks[e.name]), f)
            f("</g>\n")
        else:
            outent(d, e, f, (3 if i != 8 else 13))
    
def makesvg():
    fout = open("test1.svg", "w")
    preamble(d, fout.write)
    makesvgentitiesrecurse(d.entities, fout.write)
    fout.write("</svg>\n")
    fout.close()


# main case with further libraries loaded and some command line help stuff
if __name__ == "__main__":
    from optparse import OptionParser
    import re
    parser = OptionParser()
    parser.add_option("-d", "--dxf",        dest="dxf",        metavar="FILE",                    help="Input dxf file")
    parser.add_option("-s", "--svg",        dest="svg",        metavar="FILE",                    help="Output dxf file")
    parser.description = "Convert dxf to svg in a form that is going to be debuggable"
    parser.epilog = "Best way to execute: dump3d yourcave.3d | ./parse3ddmp.py -s -r \n"
    
    # Code is here: https://bitbucket.org/goatchurch/survexprocessing
    options, args = parser.parse_args()
    
    # push command line args that look like files into file options 
    if len(args) >= 1 and re.search("(?i)\.dxf$", args[0]) and not options.dxf:
        options.dxf = args.pop(0)
    if len(args) >= 1 and re.search("(?i)\.svg$", args[0]) and not options.svg:
        options.svg = args.pop(0)
    if not options.dxf:
        parser.print_help()
        exit(1)
    if not options.svg: 
        options.svg = re.sub("(?i)\.dxf$", "", options.dxf)+".svg"
    
    d = dxfgrabber.readfile(options.dxf)
    svgcols = ['mediumorchid', 'lightgoldenrodyellow', 'saddlebrown', 'brown', 'honeydew', 'royalblue', 'steelblue', 'grey', 'darkgoldenrod', 'lavender', 'turquoise', 'cadetblue', 'lightslategray', 'maroon','palegoldenrod']
    layercol.update({k:v  for k, v in zip(d.layers.names(), svgcols)  if k not in layercol})

    for e in d.entities:
        print(e.name)

    fout = open(options.svg, "w")
    preamble(d, fout.write)
    makesvgentitiesrecurse(d.entities, fout.write)
    fout.write("</svg>\n")
    fout.close()

