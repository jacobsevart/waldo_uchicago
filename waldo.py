import numpy, Image, sys
import scipy.spatial
from scipy import ndimage
from scipy.ndimage import measurements
from skimage.color import rgb2lab
import scipy.misc

# Define some subroutines for later
def find_color(lab_image, color, delta):
	""" Flattens the image into a 1-dimensional array (list) are sets each pixel True 
	if it's close enough to the desired color, False otherwise. Output is 1-d."""
	distance_map = scipy.spatial.distance_matrix(lab_image.reshape(x_max * y_max, z_max), [color])
	return distance_map < delta

def length(x):
	""" Reads vertical length from SciPy's weird slice notation output."""
	return abs(x[0].start - x[0].stop)

def width(x):
	""" Reads horizontal length from SciPy's wierd slice notation output."""
	return abs(x[1].start - x[1].stop)
	
def merge_and_find_rectangles(rectangles, x_max, y_max):
	"""Plot the given rectangles on a map, label and find new rectangles.
	This merges rectangles which are touching/overlapping into one entity, which is necessary for
	proper stripe and hair detection."""
	
	intermed_map = numpy.zeros((x_max, y_max))
	for key, region in enumerate(rectangles):
		intermed_map[region] = key

	labelled_super_rectangles = scipy.ndimage.measurements.label(intermed_map)[0]
	super_rectangles = scipy.ndimage.measurements.find_objects(labelled_super_rectangles)

	return (intermed_map, super_rectangles)

if not len(sys.argv) == 2:
	print "Usage: ", sys.argv[0], " filename.jpg"
	sys.exit()

print "Preprocessing: loading image"
rgb_image = ndimage.io.imread(sys.argv[1])

print "Preprocessing: converting to L*ab color"
lab_image = rgb2lab(rgb_image)

x_max, y_max, z_max = lab_image.shape

print "Preprocessing: finding red"
red_map = find_color(lab_image, [59,66,38], 63)

print "Preprocessing: finding white"
white_map = find_color(lab_image, [98, 0, 0], 15)

print "Preprocessing: finding black"
black_map = find_color(lab_image, [8,2,2], 50)

# Initialize the mask_image we will compose to be black with 180/255 opacity.
# Doing it this way lets us easily debug color detection, though doing a numpy.where
# with the same True and False is admittedly inelegant.

black_mask = black_map.reshape(x_max, y_max)
mask_image = numpy.where(black_map, [0,0,0,180], [0,0,0,180]).reshape(x_max, y_max, 4)

print "Preprocessing: detecting red-white edges"

# So if white_map looks like [True, False, False, False, True, False, False]
# And if red_map looks like  [False, True, False, True, False, False, True]
# Then I want this:          [False, True, False, True, False, False, False]
# This is the purpose of the next 3 lines of code.

# Shift white_map up one
white_map_shifted_down = numpy.roll(white_map.reshape(x_max, y_max), 1, 0).reshape(x_max * y_max, 1)

# Shift white_map down one
white_map_shifted_up = numpy.roll(white_map.reshape(x_max, y_max), -1, 0).reshape(x_max * y_max, 1)

#Make a mask where each pixel is True it's red and vertically borders white.
red_white_edge_mask = numpy.where(numpy.logical_or(numpy.logical_and(red_map, white_map_shifted_up), numpy.logical_and(red_map, white_map_shifted_down)), True, False).reshape(x_max, y_max)

print "Preprocessing: finding rectangles in red-white edges"

# Get a list of rectangles representing contiguous regions of True in the red white edge mask
red_white_border_regions = scipy.ndimage.measurements.find_objects(scipy.ndimage.measurements.label(scipy.ndimage.morphology.binary_fill_holes(red_white_edge_mask))[0])

# Eliminate red_white_border_regions that aren't long enough to be part of a set of stripes
red_white_border_regions = [x for x in red_white_border_regions if width(x) >= 3]

# Plot and find larger rectangles in our filtered red-white border rectangles
red_white_intermed_map, red_white_intermed_rectangles = merge_and_find_rectangles(red_white_border_regions, x_max, y_max)

# Make a second pass of the same process on these larger rectangles
red_white_final_map, red_white_super_rectangles = merge_and_find_rectangles(red_white_intermed_rectangles, x_max, y_max)

# Now we will process black_mask to find hair rectangles

print "Preprocessing: finding rectangles in black"

# Find rectangles representing contiguous regions of True in black_mask
black_rectangles = scipy.ndimage.measurements.find_objects(scipy.ndimage.measurements.label(black_mask)[0])

# Plot and find larger rectangles in our starting hair rectangles
hair_region_intermed_map, hair_region_intermed_rectangles = merge_and_find_rectangles(black_rectangles, x_max, y_max)

# Filter the hair for size here. Not sure why but it works best between passes.
hair_region_intermed_rectangles = [x for x in hair_region_intermed_rectangles if length(x) >= 3 and width(x) >= 4]

# Plot and find larger rectangles in our intermediate hair rectangles
hair_region_final_map, hair_region_super_rectangles = merge_and_find_rectangles(hair_region_intermed_rectangles, x_max, y_max)

# We now have now filtered to components that could be part of Waldos.
# Let's find which (if any) are in the correct spatial arrangement to be a Waldo.

print "Searching for Waldo"
# Iterate over the list of rectangles representing red-white borders
for outer_key, rectangle in enumerate(red_white_super_rectangles):
	# This section counts red-white border rectangles below and vertically in line with 
	# the rectangle we're starting from"""
	
	vertical = rectangle[0].stop
	last_hit = vertical
	vertical_prime = vertical
	potential_stripe = []	
	# Keep looking until you've moved down 8 pixels without hitting a red-white border.
	while vertical_prime - last_hit < 8:
		# Move the cursor down one
		vertical_prime += 1
		
		# The starting rectangle is part of the set of potential stripes.
		potential_stripe.append(outer_key)
		
		# Move the cursor from the left horizontal position to the right horizontal position of the starting rectangle
		for horizontal_prime in range(rectangle[1].start, rectangle[1].stop):
			try:
				# Try to read the key plotted at the cursor
				key = red_white_final_map[vertical_prime, horizontal_prime]
			except:
				# We tried to go outside the bounds of the image. Python doesn't like this, 
				# but we're suppressing the error message.
				key = 0
							
			# If the key is not 0, a red-white border region was plotted there,
			# meaning this is potentially part of an interesting set of stripes"""	
			if not key == 0:
				# Add the key at this location to the list of potential stripes
				potential_stripe.append(key)
				# Reset last_hit so we keep looking for more
				last_hit = vertical_prime

	# If the number of unique red-white border regions invovled in this potential set of stripes is at least 3
	if len(set(potential_stripe)) >= 3:
		# It's probably Waldo's shirt. Now look for black hair above it
		stripe_rectangle = rectangle
		horizontal_start, vertical_start = (stripe_rectangle[1].start, stripe_rectangle[0].start)
		
		# The horizontal start of our search area is 3 pixels to the right of the left edge.
		horizontal_start += 3
		
		# Start looking at the top of the stripe (the while loop subtrats 1, so technically we start looking 1 pixel above it)
		vertical_prime = vertical_start
		
		# Go up from the top of the stripe no more than 30 pixels, each time searching from left
		# to right for a black rectangle (the only ones plotted are big enough to be hair)
		while (vertical_start - vertical_prime) <= 30 and vertical_prime >= 1:
			vertical_prime -= 1
			
			for search_x in range(horizontal_start - 3, horizontal_start + 3):
				try:	
					if not hair_region_final_map[vertical_prime, search_x] == 0:
						# If they key at (vertical_prime, serach_x) is not 0, it's hair. 
						# As far as we're concerned, we found Waldo. Make the mask transparent
						# for a rectangle around the Waldo.
						for y in range(vertical_start - 35, vertical_start + 50):
							for x in range(horizontal_start - 15, horizontal_start + 25):
								try:
									mask_image[y,x] = [255,255,255,0]
								except:
									# We tried to illuminate somethign outside the bounds of the image.
									# We don't really care, so do nothing
									pass
						break
				except:
					# We tried to read a pixel outside the image. Again, we don't care.
					pass

print "Saving " + sys.argv[1].split(".")[0] + "_detected_waldos.png"

# Get the mask from an ndarray to PIL
mask_pil_image = Image.fromarray(mask_image.astype('uint8'), "RGBA")

# Separate the alpha channel
r, g, b, a = mask_pil_image.split()

# Load the original image from ndimage to PIL
original_pil_image = scipy.misc.toimage(rgb_image)

# Lay the alpha channel of mask on top of it
original_pil_image.paste(mask_pil_image, mask=a)

# Save the composite
original_pil_image.save(sys.argv[1].split(".")[0] + "_detected_waldos.png")
print "Done."