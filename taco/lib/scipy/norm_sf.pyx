'''
TACO: Multi-sample transcriptome assembly from RNA-Seq
'''
from taco.lib.scipy.ndtr cimport ndtr

def norm_sf(double a):
    return ndtr(-a)
