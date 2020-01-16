"""
This module defines functions used used for loading and processing images.
The edge detection algorithms defines here are optimized for documents with
thin lines and a high degree of variability.

"""

import math
import random
import re

import cv2
import numpy as np
from pytesseract import image_to_string
from scipy import ndimage
from skimage.morphology import skeletonize
from skimage.util import img_as_float, img_as_ubyte

from .string_processing import clean_number, clean_single_character

morph_kernel = np.ones((3,3), np.uint8)

vertical_kernel = np.ones((3,1), np.uint8)
horizontal_kernel = np.ones((1,3), np.uint8)

vertical_structuringElement = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20))
horizontal_structuringElement = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 1))

def load_image(img):  
    """
    Load image and prepare for edge detection.
    
    Parameters
    ----------
    img : numpy.array
        Array of image to be processed
    
    Returns
    -------
    numpy.array
        Array representing processed image

    """

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)[1]
    inv = 255 - thresh

    dilated_vertical = cv2.dilate(inv, vertical_kernel)
    dilated = cv2.dilate(dilated_vertical, horizontal_kernel)
    processed_inv = cv2.erode(dilated, morph_kernel)
    processed_inv = cv2.GaussianBlur(processed_inv, (3,3), 0)

    return processed_inv

def calculate_angle(boxes):
    """
    Calculate skewness angle of image.

    Parameters
    ----------
    boxes : numpy.array
        Array containing photographic information about the boxes in a 
        document

    Returns
    -------
    float
        Angle of skewness of image

    """

    img_edges = img_as_ubyte(skeletonize(img_as_float(boxes)))
    lines = cv2.HoughLinesP(img_edges, 1, 1 / 180.0, 100, minLineLength=270, maxLineGap=20)

    angles = []

    try:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
            if angle != 0 and angle != -90:
                if angle > 30:
                    angle = 90 - angle
                if angle < -30:
                    angle = angle + 90
                angles.append(angle)

        if len(angles) != 0:
            skew_angle = np.mean(angles)
        else:
            skew_angle = 0
    except:
        skew_angle = 0

    return skew_angle

def rotate_image(img, angle):
    """
    Rotate image.

    Parameters
    ----------
    img : numpy.array
        Image to be rotated
    angle : float
        Degree by which the image is to be rotated

    """

    img_rotated = ndimage.rotate(img, angle)

    return img_rotated

def detect_boxes(
    processed_inv,
    align=True,
    thin_lines=False,
    thin_alignment='None',
    skel=True,canny=False,
    thresh_value=80,
    vertical_iterations=5,
    horizontal_iterations=3):
    """
    Detects boxes and calculate skew angle.

    Parameters
    ----------
    processed_inv : numpy.array
        Processed array containing photographic information of
        document page
    align : bool
        Automatically align document vertically based on median angle
        of skewness
    thin_lines : bool, optional
        Specify whether lines on the page are finer than usual for
        optimized kernel length
    thin_alignment : str
        Alignment of thin lines

        In some documents, the horizontal linses are thin. In others,
        the vertical lines are thin. Specifying `thin_alignment`
        optimizes the box detection algorithm accordingly.
    skel : bool, optional
        Specify whether to skeletonize the final image
    canny : bool, optional
        Specify whether to apply the Canny edge detection algorithm
        (set 'True' for inner contours of boxes; if set true, 
        pass 'skel = False')
    vertical_iterations : int, optional
        Number of iterations of morphological operations for vertical
        line detection (set '3' for thin lines)
    horizontal_iterations : int, optional
        Number of iterations of morphological operations for horizontal
        line detection (set '2' for thin lines)

    Returns
    -------
    numpy.array
        Array containing inverted photographic information of
        the lines detected in the image
    """

    if thin_lines:
        assert thin_alignment == 'vertical' or thin_alignment == 'horizontal', """
        Parameter thin_alignment must equal 'vertical' or 'horizontal'
        """
        if thin_alignment == 'vertical':
            vertical_dilate_kernel = np.ones((10,1))
            horizontal_dilate_kernel = np.ones((1,2))
        elif thin_alignment == 'horizontal':
            vertical_dilate_kernel = np.ones((2,1))
            horizontal_dilate_kernel = np.ones((1,10))
    else:
        horizontal_dilate_kernel = np.ones((1,10))
        vertical_dilate_kernel = np.ones((10,1))

    vertical_lines = cv2.erode(processed_inv, vertical_structuringElement, iterations = vertical_iterations)
    vertical_lines = cv2.dilate(vertical_lines, vertical_structuringElement, iterations = vertical_iterations)    
    vertical_lines = cv2.dilate(vertical_lines, horizontal_dilate_kernel, iterations = 2)

    horizontal_lines = cv2.erode(processed_inv, horizontal_structuringElement, iterations = horizontal_iterations)
    horizontal_lines = cv2.dilate(horizontal_lines, horizontal_structuringElement, iterations = horizontal_iterations)
    horizontal_lines = cv2.dilate(horizontal_lines, vertical_dilate_kernel, iterations = 2)

    boxes = cv2.bitwise_or(horizontal_lines, vertical_lines)

    if align:
        align = False
        skew_angle = calculate_angle(boxes)
        if skew_angle > 0.15 or skew_angle < -0.15:
            img_rotated = rotate_image(processed_inv, skew_angle)
            boxes_thinned = detect_boxes(img_rotated, thin_lines = thin_lines, thin_alignment = thin_alignment, align = align, skel = skel, canny = canny, vertical_iterations = vertical_iterations, horizontal_iterations = horizontal_iterations)
            skel = False
            canny = False
    
    if canny:
        skel = False
        boxes = cv2.threshold(boxes, thresh_value, 255, cv2.THRESH_BINARY)[1]
        boxes_thinned = cv2.Canny(boxes, thresh_value, 240, apertureSize = 3)

    if skel:
        boxes = cv2.threshold(boxes, thresh_value, 255, cv2.THRESH_BINARY)[1]
        boxes = img_as_float(boxes)
        boxes_thinned = skeletonize(boxes)
        boxes_thinned = img_as_ubyte(boxes_thinned)
    
    try:
        return skew_angle, boxes_thinned
    except:
        return boxes_thinned

def get_boxes_info(
    boxes_thinned,
    retr_mode,
    approx_method=cv2.CHAIN_APPROX_SIMPLE):
    """
    Retreive contours and return a list of lists, each area of the box,
    and coordinates of the box.

    Parameters
    ----------
    boxes_thinned : numpy.array
        Array containing photographic information of the lines detected
         in a document
    retr_mode : cv::RetrievalModes
        OpenCV contour retreival mode (see 'https://docs.opencv.org/3.4/d3/dc0/group__imgproc__shape.html#ga819779b9857cc2f8601e6526a3a5bc71')
    approx_method :
        Chain approximation method for contour detection
    
    Returns
    -------
    box_info : list
        List of tuples containing information about the areas and boung
        ing rectangles of each contour (used for sorting algorithms)
    """

    contours = cv2.findContours(boxes_thinned, retr_mode, cv2.CHAIN_APPROX_SIMPLE)[0]

    areas = []
    coordinates_list = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        areas.append(area)
        coordinates_list.append([x, y, w, h])

    box_info = [box for box in zip(areas, coordinates_list)]

    return box_info

def process_image(
    img,
    retr_mode,
    approx_method=cv2.CHAIN_APPROX_SIMPLE,
    align=True,
    thresh_value=80,
    thin_lines=False,
    thin_alignment='None',
    skel=True,
    canny=False,
    vertical_iterations=4,
    horizontal_iterations=3):
    """
    Convenience function to call functions 'load_image', 'detect_boxes', 'get_boxes_info' in order

    Parameters
    ----------
    img : str
        Relative path to image to be processed
    
    See the corresponding functions for other parameters.

    Returns
    -------
    boxes_info : list
        List of tuples containing information about the areas and boung
        ing rectangles of each contour (used for sorting algorithms)

    """

    processed_inv = load_image(img)
    skew_angle, boxes_thinned = detect_boxes(
        processed_inv,
        align=align,
        thresh_value=thresh_value,
        thin_lines=thin_lines,
        thin_alignment=thin_alignment,
        skel=skel,
        canny=canny,
        vertical_iterations=vertical_iterations,
        horizontal_iterations=horizontal_iterations)

    boxes_info = get_boxes_info(boxes_thinned, retr_mode, approx_method)
    return skew_angle, boxes_info

def save_box(img, coordinates, rank, title = 'box'):
    """Convenience function to save a part of the image defined by the box."""

    x, y, w, h = coordinates[0], coordinates[1], coordinates[2], coordinates[3]
    cropped = img[y:y+h, x:x+w]
    cv2.imwrite(f'images/cut_outs/{title}{rank}.jpg', cropped)

def get_line_coordinates(gray_box, v_num, h_num):
    """
    Return x- and y- coordinates of vertical and horizontal lines 
    respectively in ascending order.

    Parameters
    ----------
    gray_box : numpy.array
        OpenCV converted gray, array-like representation of the required document
    v_num : int
        Number of vertical lines in 'gray_box'
    h_num : int
        Number of horizontal lines in 'gray_box'
    
    Returns
    -------
    x_list : list
        List containing the x-coordinates of each vertical line
    y_list : list
        List containing the y-coordinates of each horizontal line
    """

    thresh = cv2.threshold(gray_box, 150, 255, cv2.THRESH_BINARY)[1]
    inv = 255 - thresh

    vertical_dilating_kernel = np.ones((5,1))
    horizontal_eroding_kernel = np.ones((1,21))
    vertical_eroding_kernel = np.ones((21,1))
    horizontal_dilating_kernel = np.ones((1,5))

    gray_box = cv2.dilate(inv, vertical_dilating_kernel, iterations=3)
    gray_box = cv2.dilate(gray_box, horizontal_dilating_kernel, iterations=2)
    
    h_gray_box = cv2.erode(gray_box, horizontal_eroding_kernel, iterations=10)

    v_gray_box = cv2.erode(gray_box, vertical_eroding_kernel, iterations=10)

    h_contours = sorted(
        cv2.findContours(
        h_gray_box, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)[0],
        key=cv2.contourArea,
        reverse=True)[:h_num]
    v_contours = sorted(
        cv2.findContours(
        v_gray_box, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)[0],
        key=cv2.contourArea,
        reverse=True)[:v_num]

    y_list = sorted([h_contours[line][0][0][1] for line in range(len(h_contours))])
    x_list = sorted([v_contours[line][0][0][0] for line in range(len(v_contours))])

    return x_list, y_list

def ocr_box(
    img,
    coordinates,
    concentrate=False,
    halve=False,
    resize=False,
    blur=True,
    sharpen=False,
    erode=False,
    dilate=False,
    lang='eng',
    config=''):
    """
    Detect text in a rectangular part of the image and return the detected string.
 
    Parameters
    ----------
    img : numpy.array
        Array containing photographic information of the document to be scanned
    coordinates : iterable
        Iterable containing the x- and y-coordinates of the top left po
        int of the bounding rectangle and its width and height
    halve : bool, optional
        Scan half of the rectangle
    concentrate : bool, optional
        Scan a smaller part of the box for better results
    resize : bool, optional
        Resize the box before scanning
    blur : bool, optional
        Blur the box for better results
    sharpen : bool, optional
        Sharpen the image
    erode : bool, optional
        Make the text thinner
    dilate : bool, optional
        Make the text thicker
    lang : str, optional
        Language for the Tesseract engine
    config: str, optional
        Configuration string for the 'config' parameter of 'pytesseract'

    Returns
    -------
    ocr_string : str
        Detected text contained in the box
    """

    x, y, w, h = coordinates

    if isinstance(halve, str):
        halve, side = halve.split(' ')
        halve = eval(halve)
    else:
        side = 'left'
    
    if halve:
        if side == 'left':
            w = w // 2
        elif side == 'right':
            w = w // 2
            x = x + w
    
    if concentrate:
        x = x + 90
        y = y + 65
        w = w - 80
        h = h - 70 

    cropped_img = img[y:y+h, x:x+w]
    
    if resize:
        cropped_img = cv2.resize(cropped_img, (0,0) , fx=3, fy=3)

    if erode:
        cropped_img = cv2.erode(cropped_img, (3,3), iterations=2)

    if blur:
        cropped_img = cv2.GaussianBlur(cropped_img, (7,7), 0)
        
    if sharpen:
        kernel = np.array([
                    [-1, -1, -1], 
                    [-1, 9, -1], 
                    [-1, -1, -1]])
        cropped_img = cv2.filter2D(cropped_img, -1, kernel)
        cropped_img = cv2.filter2D(cropped_img, -1, kernel)

    if dilate:
        cropped_img = cv2.dilate(cropped_img, (3,3), iterations=2)
    

    ocr_string = image_to_string(cropped_img, lang=lang, config=config)
    
    return ocr_string.strip() if (ocr_string != '' and ocr_string != 'N/A') else 'None'

def ocr_boxes(
    img,
    boxes,
    halve=False,
    resize=False,
    blur=True,
    sharpen=False,
    erode=False,
    dilate=False,
    lang='eng',
    config=None):
    """
    Detect strings in multiple related boxes and concatenate the results.
    
    Parameters
    ----------
    halve : bool, optional
        Scan half of the rectangle
    resize : bool, optional
        Resize the box before scanning
    blur : bool, optional
        Blur the box for better results
    sharpen : bool, optional
        Sharpen the image
    erode : bool, optional
        Make the text thinner
    dilate : bool, optional
        Make the text thicker
    lang : str, optional
        Language for the Tesseract engine
    config: str, optional
        Configuration string for the 'config' parameter of 'pytesseract'
    
    Returns
    -------
    str 
        Concatenated string of strings detected in each box

    See Also
    --------
    ocr_box
    """

    string_list = []

    for order, box in enumerate(boxes):
        coordinates = box[1]

        box_string = ocr_box(
                            img,
                            coordinates,
                            halve=halve,
                            resize=resize,
                            blur=blur,
                            sharpen=sharpen,
                            erode=erode,
                            dilate=dilate,
                            lang=lang,
                            config=config)

        if box_string != 'None' and box_string != 'N/A':
            string_list.append(box_string)
    
    try:
        string_list[0] #Check if list is empty
        ocr_string = ' '.join(string_list)
    except:
        ocr_string = 'None'

    return ocr_string

def ocr_segmented_box(img, coordinates, lang='eng', data_type='number', single=False):
    """
    Detect text in each box of a larger segmented box and concatenate
    all strings.

    Parameters
    ----------
    img : numpy.array
        Array containing photographic information of the source document
    coordinates : iterable
        Iterable of x- and y-coodinates of the top-left point of the 
        desired rectangle and the corresponding width and height
    lang : str
        Language configuration of the Tesseract engine
    data_type : str
        Type of data contained in box, options:
        `number`, `letter`
    
    Returns
    -------
    str
        Detected text as a contatenated string
    """

    x, y, w, h = coordinates
    
    cropped_img = img[y:y + h, x:x + w]
    
    height = cropped_img.shape[0]
    length = cropped_img.shape[1]
    
    vertical_thickening_kernel = np.ones((3,1), np.uint8)
    vertical_thinning_kernel = np.ones((int(cropped_img.shape[0] * 0.4), 1), np.uint8)
    horizontal_kernel = np.ones((1,7), np.uint8)
    
    gray = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)[1]
    inv = 255 - thresh

    processed_img = cv2.dilate(inv, horizontal_kernel, iterations = 3)
    processed_img = cv2.dilate(processed_img, vertical_thickening_kernel, iterations = 7)
    processed_img = cv2.erode(processed_img, vertical_thinning_kernel, iterations = 10)

    processed_img = img_as_float(processed_img)
    processed_img = skeletonize(processed_img)
    processed_img = img_as_ubyte(processed_img)

    contours = cv2.findContours(processed_img, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)[0]
    contours.sort(key = lambda x: x[0][0][0])

    """If contours are found, return the text contained in each box
    segmented by those contours"""
    if len(contours) >= 2:
        if contours[0][0][0][0] < 50:
            n_boxes = len(contours) - 1
        else:
            n_boxes = len(contours)
        
        step_length = int(length // n_boxes)

        img_string_list = []

        box_generator = (
            thresh[:, step_length * step:min(
                step_length * (step + 1), length)] 
                for step in range(n_boxes))

        for order, box in enumerate(box_generator):
            height, width = box.shape
            box = box[(height//7) : (height - height//7), (width//7) : (width - width//7)]
            box = cv2.GaussianBlur(box, (9, 9), 1)
            box_string = image_to_string(box, lang=lang, config='--psm 10')

            if order != 6: # Prevent treating the the seventh digit of 
                           # the second part of the HKID as a letter
                if not single:
                    box_string = clean_number(box_string, data_type=data_type)
                elif single:
                    box_string = clean_single_character(box_string, data_type=data_type)
            else:
                box_string = re.sub('[^a-zA-Z0-9]', '', box_string)
                if not any(letter.isupper() for letter in box_string):
                    box_string = clean_single_character(box_string, data_type='number')
            
            img_string_list.append(box_string)

        return ' '.join(img_string_list)
    else:
        return 'None'
