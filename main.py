import sys
import time
import cv2
import serial
import struct
import socket
import threading
import random
import math
from pymavlink import mavutil

gst_pipeline = "v4l2src device=/dev/video0 ! videoconvert ! autovideosink"
video = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

