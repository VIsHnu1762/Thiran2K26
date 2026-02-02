import cv2
import numpy as np
from typing import List, Tuple

def detect_table_layout(preprocessed_image: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """
    Detects potential table rows or items using contour detection.
    Returns a list of bounding boxes (x, y, w, h) sorted by Y position.
    """
    # Invert image to get white text on black background for contour findings if needed, 
    # but adaptive threshold usually gives black text on white.
    # We might need to invert for finding contours of text blocks.
    inverted = cv2.bitwise_not(preprocessed_image)
    
    # Dilate to connect text characters into blocks
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.dilate(inverted, kernel, iterations=1)

    # Find Contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    bounding_boxes = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        # Filter small noise
        if w > 20 and h > 10: 
            bounding_boxes.append((x, y, w, h))
            
    # Sort by Y position (top to bottom)
    bounding_boxes.sort(key=lambda b: b[1])
    
    return bounding_boxes

def extract_regions(image: np.ndarray, boxes: List[Tuple[int, int, int, int]]) -> List[np.ndarray]:
    """
    Crops the image into regions based on bounding boxes.
    """
    regions = []
    for (x, y, w, h) in boxes:
        roi = image[y:y+h, x:x+w]
        regions.append(roi)
    return regions
