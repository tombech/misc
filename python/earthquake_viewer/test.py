import requests
from PIL import Image, ImageEnhance, ImageFilter
from itertools import chain, product
flatten = chain.from_iterable
import os.path

dyn_url = "http://hraun.vedur.is/ja/drumplot/IDYN.png"

class QuakeCounter:

    def __init__(self):
        self.count = 0
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
            fn = self.getFreeFilename("outfile.png")
            
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

    def getFreeFilename(self, filename):
        if not os.path.isfile(filename):
            return filename

        fn, ext = os.path.splitext(filename)
        i = 0

        f = "%s-%s%s" % (fn, str(i), ext)        
        while os.path.isfile(f):
            i = i + 1
            f = "%s-%s%s" % (fn, str(i), ext)
        
        return f

    def saveImage(self, image, filename):
        fn = self.getFreeFilename(filename)
        image.save(fn)
        return fn
        
    def cleanupImage(self, image, label="debug", debug=False):
        image = self.removeLines(image)
        
        if debug:
            self.saveImage(image, "outputfile_lines1_%s" % label, overwrite=False)
            
        image = self.removeLines(image)
        
        if debug:
            self.saveImage(image, "outputfile_lines2_%s" % label, overwrite=False)

        image = image.filter(ImageFilter.GaussianBlur(radius=1))
        
        if debug:
            self.saveImage(image, "outputfile_blur_%s" % label, overwrite=False)

        image, numregions = self.removeSmallRegions(image, 200)   
       
        return image,numregions
        
    def countQuakes(self, url, debug=False):
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
        
        return self.count

if __name__ == '__main__':
    counter = QuakeCounter()
    print counter.countQuakes(dyn_url)
