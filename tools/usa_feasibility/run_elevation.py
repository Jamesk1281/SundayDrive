"""elevation.main() with a bounding box other than New England's."""
import sys
sys.path.insert(0, sys.argv[1])
import elevation
elevation.BBOX = tuple(float(x) for x in sys.argv[3].split(","))
elevation.main(sys.argv[2], 11)
