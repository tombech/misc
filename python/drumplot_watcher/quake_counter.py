import requests
from PIL import Image, ImageEnhance, ImageFilter
from itertools import chain, product
flatten = chain.from_iterable
import utils
import os.path
from datetime import datetime

dyn_url = "http://hraun.vedur.is/ja/drumplot/dyn.png"

class QuakeCounter:

    def __init__(self):
        self.count = 0
        self.previous_count = 0
        self.detailed_count = ()
        self.count_history = []
        self.updates = 0

    def pixelTest(self, pixel):
        return pixel > 0

    def closed_regions(self, image, test):
        """
        Return all closed regions in image who's pixel satisfy test.
        """
        pixel = image.load()
        xs, ys = map(xrange, image.size)
        todo = set(xy for xy in product(xs, ys) if test(pixel[xy]))
        while todo:
            region = set()
            edge = set([todo.pop()])
            while edge:
                region |= edge
                todo -= edge
                edge = todo.intersection(
                    flatten(((x - 1, y), (x, y - 1), (x + 1, y), (x, y + 1)) for x, y in edge))
            yield region

    def removeSmallRegions(self, image, regionsize=100):
        new_image = Image.new("L", image.size)
        pix = new_image.load()
        numregions = 0
        for region in self.closed_regions(image, self.pixelTest):
            if len(region) > regionsize:
                numregions = numregions + 1
                for x,y in region:
                    pix[x,y] = 255
        
        return new_image, numregions

    def downloadImage(self, imageurl):
        print "Downloading image..."

        r = requests.get(imageurl, stream=True)
        if r.status_code == 200:
            fn = utils.getFreeFilename("outfile.png")
            
            with open(fn, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)

        self.image = Image.open(fn)
        return fn, self.image

    def removeLines(self, image):
        pix = image.load()
        w, h = image.size
        for y in xrange(2,h-2):
            for x in range(w):
                if pix[x,y-1] == 0 and pix[x,y+1] == 0:
                    pix[x,y] = 0
                if pix[x,y-2] == 0 and pix[x,y+2] == 0:
                    pix[x,y] = 0

        return image

    def saveImage(self, image, filename, overwrite=False):
        if not overwrite:
            filename = utils.getFreeFilename(filename)
        image.save(filename)
        return filename
        
    def cleanupImage(self, image, label="debug", debug=False):
        image = self.removeLines(image)
        
        if debug:
            self.saveImage(image, "outputfile_lines1_%s.png" % label, overwrite=False)
            
        image = self.removeLines(image)
        
        if debug:
            self.saveImage(image, "outputfile_lines2_%s.png" % label, overwrite=False)

        image = image.filter(ImageFilter.GaussianBlur(radius=1))
        
        if debug:
            self.saveImage(image, "outputfile_blur_%s.png" % label, overwrite=False)

        image, numregions = self.removeSmallRegions(image, 300)   
       
        return image,numregions


    def resetCount(self):
        self.count_history = []
        self.count = 0
        self.previous_count
        self.detailed_count = (0,0,0,0)

    def countQuakes(self, url, debug=False):
        self.previous_count = self.count
        current_dir = os.getcwd()
        datedir = "output_images/%s" % utils.getISODateAsString()

        utils.assertDir(datedir)
        os.chdir(datedir)
        
        filename, image = self.downloadImage(url)

        converter = ImageEnhance.Color(image)
        img2 = converter.enhance(6.0)
        #img2.save("outputfile_ehanced.png")
        pix = img2.load()

        r_image = Image.new("L", img2.size)
        r_pix = r_image.load()
        g_image = Image.new("L", img2.size)
        g_pix = g_image.load()
        b_image = Image.new("L", img2.size)
        b_pix = b_image.load()
        y_image = Image.new("L", img2.size)
        y_pix = y_image.load()
    
        w, h = image.size
        for y in range(h):
            for x in range(w):
                r,g,b,a = pix[x,y] 
                if (r == 255 and g < 10 and b <10):
                    r_pix[x,y] = 255
                elif (b == 255 and r < 10 and g < 10):
                    b_pix[x,y] = 255
                elif (g > 200 and b < 100 and r < 100):
                    g_pix[x,y] = 255
                elif (r == 255 and g > 100 and b == 0):
                    y_pix[x,y] = 255

        r_image, nr = self.cleanupImage(r_image, label="r", debug=debug)
        g_image, ng = self.cleanupImage(g_image, label="g", debug=debug)
        b_image, nb = self.cleanupImage(b_image, label="b", debug=debug)
        y_image, ny = self.cleanupImage(y_image, label="y", debug=debug)
        
        if debug:
            self.saveImage(r_image, "outputfile_r.png")
            self.saveImage(g_image, "outputfile_g.png")
            self.saveImage(b_image, "outputfile_b.png")
            self.saveImage(y_image, "outputfile_y.png")

        print "Quakes found:", nr, ng, nb, ny
        self.count = nr+ng+nb+ny
        self.detailed_count = (nr, ng, nb, ny)

        os.chdir(current_dir)
        
        new_count = False
        if not self.detailed_count in self.count_history:
            self.count_history.append(self.detailed_count)
            new_count = True
        
        return current_dir + os.sep + datedir + os.sep + filename, new_count

if __name__ == '__main__':
    counter = QuakeCounter()
    filename, count = counter.countQuakes(dyn_url)
    if count > 0:
        print "Found %s quakes" % count
        counter.sendNotice(filename)
