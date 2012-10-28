This is a script I created in response to the University of Chicago admissions essay question,
"So where is Waldo, really?" It was inspired by a StackOverflow response[1] that implemented rudimentary Waldo detection in Mathematica. This solution follows a different algorithm implemented in Python, supported by NumPy, SciPy, Scikits-Image, and the Python Imaging Library. The accompanying admissions essay, which lays out a simplified version of the algorithm followed here, is forthcoming.

If you'd like to run this yourself, it works on Python 2.7.3 with the latest versions of the four aforementioned libraries. You may need to boost the contrast of the images you're working with so that red-white borders are clear, and replace my reference values and color distance thresholds for red, white, and black (in the L*ab colorspace) with your own.

[1] http://stackoverflow.com/questions/8479058/how-do-i-find-waldo-with-mathematica